"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useKnowledgeDoc } from "@/hooks/useKnowledge";
import { formatDate } from "@/lib/utils";

export default function KnowledgeDocDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data: doc, isLoading, error } = useKnowledgeDoc(id);

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400">Loading document...</div>;
  }

  if (error || !doc) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
        Document not found
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/knowledge" className="text-gray-400 hover:text-gray-600">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">{doc.title}</h1>
      </div>

      <div className="card mb-6">
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div>
            <p className="text-gray-500">Type</p>
            <p className="font-medium text-gray-900 capitalize">
              {doc.doc_type.replace(/_/g, " ")}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Original File</p>
            <p className="font-medium text-gray-900">
              {doc.original_filename || "N/A"}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Uploaded</p>
            <p className="font-medium text-gray-900">{formatDate(doc.created_at)}</p>
          </div>
        </div>
        <div className="mt-4">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
              doc.is_indexed
                ? "bg-green-100 text-green-700"
                : "bg-yellow-100 text-yellow-700"
            }`}
          >
            {doc.is_indexed ? "Indexed & searchable" : "Processing..."}
          </span>
        </div>
      </div>

      {doc.extracted_text && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-3">Extracted Content</h2>
          <div className="max-h-[600px] overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
              {doc.extracted_text}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
