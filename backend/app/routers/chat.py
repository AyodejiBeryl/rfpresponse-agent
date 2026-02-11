from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_org, get_current_user, get_db, get_llm_client
from app.models.conversation import Conversation
from app.models.draft_section import DraftSection
from app.models.message import Message
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from app.schemas.chat import (
    ConversationCreateRequest,
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.services.knowledge_service import get_relevant_context
from app.services.llm_client import LLMClient

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["chat"])

SECTION_UPDATE_RE = re.compile(
    r'<section_update\s+key="([^"]+)">(.*?)</section_update>',
    re.DOTALL,
)

SYSTEM_PROMPT = """\
You are an expert federal proposal writer helping refine RFP response sections.
Rules:
- Only use facts from the provided context (company profile, past performance, requirements).
- Do not invent certifications, contracts, or legal claims.
- When the user asks you to revise a section, output the full revised section wrapped in:
  <section_update key="SECTION_KEY">
  ...revised content...
  </section_update>
- Outside the tags, provide your explanation of what changed and why.
- Be concise and compliance-focused.
"""


def _build_context(project: Project, section_key: str | None, current_section: str | None) -> str:
    parts = [f"Solicitation metadata: {project.metadata_json}"]
    if project.company_profile_snapshot:
        parts.append(f"Company profile:\n{project.company_profile_snapshot[:3000]}")
    if project.past_performance_snapshot:
        pp = "\n".join(f"- {p}" for p in project.past_performance_snapshot[:5])
        parts.append(f"Past performance:\n{pp}")

    req_preview = "\n".join(
        f"- {r.get('id', '')}: {r.get('requirement_text', '')}"
        for r in (project.requirements or [])[:20]
    )
    parts.append(f"Key requirements:\n{req_preview}")

    matrix_preview = "\n".join(
        f"- {m.get('requirement_id', '')}: {m.get('status', '')} — {m.get('evidence', '')}"
        for m in (project.compliance_matrix or [])[:20]
    )
    parts.append(f"Compliance snapshot:\n{matrix_preview}")

    if section_key and current_section:
        parts.append(f"Current '{section_key}' section content:\n{current_section}")

    return "\n\n".join(parts)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    project_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(db, project_id, org.id)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project.id)
        .order_by(Conversation.created_at.desc())
    )
    return result.scalars().all()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    project_id: uuid.UUID,
    payload: ConversationCreateRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(db, project_id, org.id)
    conv = Conversation(
        project_id=project.id,
        title=payload.title or f"Chat about {payload.section_key or 'proposal'}",
        section_key=payload.section_key,
        created_by=user.id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    project_id: uuid.UUID,
    conv_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(db, project_id, org.id)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/conversations/{conv_id}/messages")
async def send_message(
    project_id: uuid.UUID,
    conv_id: uuid.UUID,
    payload: SendMessageRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    project = await _get_project(db, project_id, org.id)

    # Get conversation
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv or conv.project_id != project.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get current section content if section-scoped
    current_section = None
    if conv.section_key:
        sec_result = await db.execute(
            select(DraftSection).where(
                DraftSection.project_id == project.id,
                DraftSection.section_key == conv.section_key,
                DraftSection.is_current == True,
            )
        )
        sec = sec_result.scalar_one_or_none()
        if sec:
            current_section = sec.content

    # Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=payload.content)
    db.add(user_msg)
    await db.commit()

    # Retrieve relevant knowledge base context via RAG
    rag_queries = [payload.content]
    if conv.section_key and current_section:
        rag_queries.append(current_section[:500])
    rag_context = ""
    try:
        rag_context = await get_relevant_context(
            db=db, org_id=org.id, queries=rag_queries, llm_client=llm, top_k=5
        )
    except Exception:
        pass  # RAG is best-effort; don't block chat if it fails

    # Build messages for LLM
    context = _build_context(project, conv.section_key, current_section)
    if rag_context:
        context += "\n\n" + rag_context

    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    llm_messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nProject context:\n" + context},
    ]
    for msg in history:
        llm_messages.append({"role": msg.role, "content": msg.content})

    # Stream response via SSE
    async def event_stream():
        full_response = []
        try:
            for token in llm.stream_complete(llm_messages):
                full_response.append(token)
                yield f"data: {token}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
            return

        assistant_text = "".join(full_response)

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conv.id, role="assistant", content=assistant_text
        )
        db.add(assistant_msg)

        # Check for section updates
        updates = SECTION_UPDATE_RE.findall(assistant_text)
        for section_key, new_content in updates:
            # Mark old version as not current
            old_result = await db.execute(
                select(DraftSection).where(
                    DraftSection.project_id == project.id,
                    DraftSection.section_key == section_key,
                    DraftSection.is_current == True,
                )
            )
            old_section = old_result.scalar_one_or_none()
            new_version = 1
            if old_section:
                old_section.is_current = False
                new_version = old_section.version + 1

            new_section = DraftSection(
                project_id=project.id,
                section_key=section_key,
                content=new_content.strip(),
                version=new_version,
                is_current=True,
                created_by=user.id,
            )
            db.add(new_section)
            assistant_msg.draft_section_id = new_section.id

        await db.commit()
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _get_project(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
