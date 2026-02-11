"use client";

import { useState } from "react";
import Link from "next/link";
import {
  useKnowledgeDocs,
  useUploadKnowledge,
  useDeleteKnowledge,
  useKnowledgeSearch,
  type SearchResult,
} from "@/hooks/useKnowledge";
import { formatDate } from "@/lib/utils";

const DOC_TYPES = [
  { value: "company_profile", label: "Company Profile" },
  { value: "past_proposal", label: "Past Proposal" },
  { value: "capability_statement", label: "Capability Statement" },
  { value: "past_performance", label: "Past Performance" },
  { value: "other", label: "Other" },
];

export default function KnowledgeBasePage() {
  const { data: docs, isLoading } = useKnowledgeDocs();
  const uploadMutation = useUploadKnowledge();
  const deleteMutation = useDeleteKnowledge();
  const searchMutation = useKnowledgeSearch();

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("other");
  const [uploadError, setUploadError] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploadError("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    formData.append("doc_type", docType);

    try {
      await uploadMutation.mutateAsync(formData);
      setFile(null);
      setTitle("");
      setDocType("other");
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      const results = await searchMutation.mutateAsync({
        query: searchQuery,
        top_k: 5,
      });
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and all its indexed data?")) return;
    await deleteMutation.mutateAsync(id);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload company documents to improve RFP analysis accuracy. The AI uses these
          to find better evidence for compliance matching and proposal drafting.
        </p>
      </div>

      {/* Upload form */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Upload Document</h2>
        <form onSubmit={handleUpload} className="space-y-4">
          {uploadError && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {uploadError}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document Title
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="input-field"
                placeholder="e.g. Cloud Migration Case Study"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document Type
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="input-field"
              >
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              File (PDF, DOCX, or TXT)
            </label>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
            />
          </div>

          <button
            type="submit"
            disabled={!file || !title || uploadMutation.isPending}
            className="btn-primary"
          >
            {uploadMutation.isPending ? "Uploading & Indexing..." : "Upload & Index"}
          </button>
        </form>
      </div>

      {/* Search */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Search Knowledge Base</h2>
        <form onSubmit={handleSearch} className="flex gap-2 mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field flex-1"
            placeholder="Search for relevant capabilities, experience, etc."
          />
          <button
            type="submit"
            disabled={searchMutation.isPending}
            className="btn-primary"
          >
            {searchMutation.isPending ? "Searching..." : "Search"}
          </button>
        </form>

        {searchResults.length > 0 && (
          <div className="space-y-3">
            {searchResults.map((result) => (
              <div
                key={result.chunk_id}
                className="rounded-lg border border-gray-200 p-3"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-primary-700">
                    {result.doc_title}
                  </span>
                  <span className="text-xs text-gray-400">
                    {(result.similarity * 100).toFixed(0)}% match
                  </span>
                </div>
                <p className="text-sm text-gray-600 line-clamp-3">
                  {result.chunk_text}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document list */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">
          Indexed Documents{docs ? ` (${docs.length})` : ""}
        </h2>

        {isLoading && (
          <p className="text-gray-400 text-sm">Loading documents...</p>
        )}

        {docs && docs.length === 0 && (
          <p className="text-gray-500 text-sm">
            No documents uploaded yet. Upload your company profiles, past proposals,
            and capability statements to enhance AI analysis.
          </p>
        )}

        {docs && docs.length > 0 && (
          <div className="divide-y divide-gray-100">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between py-3">
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/knowledge/${doc.id}`}
                    className="text-sm font-medium text-gray-900 hover:text-primary-600"
                  >
                    {doc.title}
                  </Link>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {DOC_TYPES.find((t) => t.value === doc.doc_type)?.label ||
                        doc.doc_type}
                    </span>
                    {doc.original_filename && (
                      <span className="text-xs text-gray-400 truncate max-w-[200px]">
                        {doc.original_filename}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {formatDate(doc.created_at)}
                    </span>
                    {doc.is_indexed ? (
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                        Indexed
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                        Processing
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  disabled={deleteMutation.isPending}
                  className="ml-4 text-sm text-red-500 hover:text-red-700"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
