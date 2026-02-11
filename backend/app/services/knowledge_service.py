from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_doc import KnowledgeDocument
from app.services.llm_client import LLMClient
from app.services.parser import (
    extract_text_from_docx_bytes,
    extract_text_from_pdf_bytes,
)
from app.services.storage import storage_service


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------


def _chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> list[str]:
    """Split text into chunks on paragraph boundaries, with token-level overlap."""
    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        words = para.split()
        para_len = len(words)

        if current_len + para_len > max_tokens and current:
            chunk_text = " ".join(current)
            chunks.append(chunk_text)
            # Keep overlap from end of current chunk
            overlap_words = " ".join(current).split()[-overlap:]
            current = overlap_words
            current_len = len(overlap_words)

        current.append(para)
        current_len += para_len

    if current:
        chunks.append(" ".join(current))

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def _embed_texts(texts: list[str], llm_client: LLMClient) -> list[list[float]]:
    """Generate embeddings using the OpenAI-compatible embeddings endpoint.

    Works with OpenAI directly. For Groq (which doesn't support embeddings),
    falls back to a simple TF-based vector for keyword matching.
    """
    try:
        response = llm_client.client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception:
        # Fallback: generate simple keyword frequency vectors
        # This ensures the system works even without embedding API access
        return _fallback_embeddings(texts)


def _fallback_embeddings(texts: list[str], dim: int = 1536) -> list[list[float]]:
    """Simple hash-based embeddings when no embedding API is available.

    Not as good as real embeddings but allows the system to function
    with basic keyword-level similarity.
    """
    embeddings = []
    for t in texts:
        words = re.findall(r"[a-z0-9]+", t.lower())
        vec = [0.0] * dim
        for w in words:
            idx = hash(w) % dim
            vec[idx] += 1.0
        # Normalize
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        embeddings.append(vec)
    return embeddings


# ---------------------------------------------------------------------------
# Document lifecycle
# ---------------------------------------------------------------------------


async def upload_and_index(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    doc_type: str,
    filename: str,
    file_data: bytes,
    llm_client: LLMClient,
) -> KnowledgeDocument:
    """Upload a document, extract text, chunk, embed, and store."""

    # 1. Extract text
    lower = filename.lower()
    if lower.endswith(".pdf"):
        extracted = extract_text_from_pdf_bytes(file_data)
    elif lower.endswith(".docx"):
        extracted = extract_text_from_docx_bytes(file_data)
    elif lower.endswith(".txt"):
        extracted = file_data.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type. Use PDF, DOCX, or TXT.")

    # 2. Store file
    s3_key = storage_service.generate_key(str(org_id), filename)
    storage_service.upload(file_data, s3_key)

    # 3. Create document record
    doc = KnowledgeDocument(
        org_id=org_id,
        uploaded_by=user_id,
        title=title,
        doc_type=doc_type,
        original_filename=filename,
        file_s3_key=s3_key,
        extracted_text=extracted,
        is_indexed=False,
    )
    db.add(doc)
    await db.flush()

    # 4. Chunk and embed
    chunks_text = _chunk_text(extracted)
    if chunks_text:
        embeddings = _embed_texts(chunks_text, llm_client)
        for i, (chunk_text, embedding) in enumerate(zip(chunks_text, embeddings)):
            chunk = KnowledgeChunk(
                document_id=doc.id,
                org_id=org_id,
                chunk_index=i,
                chunk_text=chunk_text,
            )
            db.add(chunk)
            await db.flush()

            # Store embedding via raw SQL (pgvector)
            await db.execute(
                text("UPDATE knowledge_chunks SET embedding = :emb WHERE id = :id"),
                {"emb": str(embedding), "id": str(chunk.id)},
            )

        doc.is_indexed = True

    await db.commit()
    await db.refresh(doc)
    return doc


async def search_knowledge(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    llm_client: LLMClient,
    top_k: int = 5,
) -> list[dict]:
    """Semantic search across an org's knowledge chunks."""
    query_embedding = _embed_texts([query], llm_client)[0]

    result = await db.execute(
        text("""
            SELECT kc.id, kc.chunk_text, kc.document_id,
                   kd.title as doc_title,
                   1 - (kc.embedding <=> :embedding::vector) as similarity
            FROM knowledge_chunks kc
            JOIN knowledge_documents kd ON kd.id = kc.document_id
            WHERE kc.org_id = :org_id
              AND kc.embedding IS NOT NULL
            ORDER BY kc.embedding <=> :embedding::vector
            LIMIT :top_k
        """),
        {
            "embedding": str(query_embedding),
            "org_id": str(org_id),
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    return [
        {
            "chunk_id": str(row[0]),
            "chunk_text": row[1],
            "document_id": str(row[2]),
            "doc_title": row[3],
            "similarity": float(row[4]) if row[4] else 0.0,
        }
        for row in rows
    ]


async def get_relevant_context(
    db: AsyncSession,
    org_id: uuid.UUID,
    queries: list[str],
    llm_client: LLMClient,
    top_k: int = 5,
) -> str:
    """Retrieve relevant knowledge chunks for multiple queries and format as context."""
    all_chunks: dict[str, dict] = {}

    for query in queries:
        results = await search_knowledge(db, org_id, query, llm_client, top_k=top_k)
        for r in results:
            if r["chunk_id"] not in all_chunks:
                all_chunks[r["chunk_id"]] = r

    if not all_chunks:
        return ""

    # Sort by similarity and take top results
    sorted_chunks = sorted(
        all_chunks.values(), key=lambda x: x["similarity"], reverse=True
    )[:top_k]

    parts = ["Relevant knowledge from your organization's documents:"]
    for chunk in sorted_chunks:
        parts.append(f"\n[From: {chunk['doc_title']}]\n{chunk['chunk_text']}")

    return "\n".join(parts)


async def delete_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """Delete a knowledge document and its chunks."""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.org_id == org_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return False

    # Delete file from storage
    if doc.file_s3_key:
        storage_service.delete(doc.file_s3_key)

    # Delete chunks
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id))

    # Delete document
    await db.delete(doc)
    await db.commit()
    return True


async def list_documents(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[KnowledgeDocument]:
    """List all knowledge documents for an org."""
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.org_id == org_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Optional[KnowledgeDocument]:
    """Get a single knowledge document."""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()
