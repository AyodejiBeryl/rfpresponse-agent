"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useProject } from "@/hooks/useProjects";
import { statusColor } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";

type Tab = "overview" | "requirements" | "matrix" | "drafts" | "export";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { data: project, isLoading, error } = useProject(id);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400">Loading project...</div>;
  }
  if (error || !project) {
    return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">Failed to load project</div>;
  }

  const metCount = project.compliance_matrix.filter((r) => r.status === "met").length;
  const partialCount = project.compliance_matrix.filter((r) => r.status === "partial").length;
  const missingCount = project.compliance_matrix.filter((r) => r.status === "missing").length;

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "requirements", label: `Requirements (${project.requirements.length})` },
    { key: "matrix", label: "Compliance Matrix" },
    { key: "drafts", label: "Draft Sections" },
    { key: "export", label: "Export" },
  ];

  const handleExport = async (format: string) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/projects/${id}/export/${format}`,
      { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify(project) }
    );
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = format === "csv" ? "compliance_matrix.csv" : format === "markdown" ? "proposal_draft.md" : "proposal_draft.docx";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.title}</h1>
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(project.status)}`}>
              {project.status}
            </span>
            {project.metadata_json?.solicitation_number && project.metadata_json.solicitation_number !== "Not found" && (
              <span>Sol #: {project.metadata_json.solicitation_number}</span>
            )}
          </div>
        </div>
        <Link href={`/projects/${id}/chat`} className="btn-primary">
          Refine with AI Chat
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6 overflow-x-auto">
        <nav className="flex gap-6 min-w-max">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <div className="grid gap-4 sm:grid-cols-3 mb-6">
          <div className="card text-center">
            <p className="text-3xl font-bold text-green-600">{metCount}</p>
            <p className="text-sm text-gray-500 mt-1">Requirements Met</p>
          </div>
          <div className="card text-center">
            <p className="text-3xl font-bold text-yellow-600">{partialCount}</p>
            <p className="text-sm text-gray-500 mt-1">Partially Met</p>
          </div>
          <div className="card text-center">
            <p className="text-3xl font-bold text-red-600">{missingCount}</p>
            <p className="text-sm text-gray-500 mt-1">Missing</p>
          </div>
        </div>
      )}

      {activeTab === "overview" && project.gaps.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-3">Gaps & Action Items</h3>
          <ul className="space-y-2">
            {project.gaps.map((gap, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-red-400 shrink-0" />
                {gap}
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeTab === "requirements" && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="pb-3 pr-4 font-medium">ID</th>
                <th className="pb-3 pr-4 font-medium">Requirement</th>
                <th className="pb-3 pr-4 font-medium">Priority</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {project.requirements.map((req) => (
                <tr key={req.id}>
                  <td className="py-3 pr-4 font-mono text-xs text-gray-500">{req.id}</td>
                  <td className="py-3 pr-4 text-gray-700">{req.requirement_text}</td>
                  <td className="py-3 pr-4">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      req.priority === "must" ? "bg-red-100 text-red-700" :
                      req.priority === "should" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-700"
                    }`}>
                      {req.priority}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "matrix" && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="pb-3 pr-4 font-medium">Req ID</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 font-medium">Evidence</th>
                <th className="pb-3 pr-4 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {project.compliance_matrix.map((row) => (
                <tr key={row.requirement_id}>
                  <td className="py-3 pr-4 font-mono text-xs text-gray-500">{row.requirement_id}</td>
                  <td className="py-3 pr-4">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-gray-700">{row.evidence}</td>
                  <td className="py-3 pr-4 text-gray-500">{row.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "drafts" && (
        <div className="space-y-4">
          {Object.entries(project.draft_sections).map(([key, content]) => (
            <div key={key} className="card">
              <button
                onClick={() => setExpandedSection(expandedSection === key ? null : key)}
                className="flex w-full items-center justify-between"
              >
                <h3 className="font-semibold text-gray-900">
                  {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </h3>
                <svg
                  className={`h-5 w-5 text-gray-400 transition-transform ${expandedSection === key ? "rotate-180" : ""}`}
                  fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                </svg>
              </button>
              {expandedSection === key && (
                <div className="mt-4 prose prose-sm max-w-none text-gray-700">
                  <ReactMarkdown>{content}</ReactMarkdown>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === "export" && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Export Options</h3>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => handleExport("csv")} className="btn-secondary">
              Export Compliance Matrix (CSV)
            </button>
            <button onClick={() => handleExport("markdown")} className="btn-secondary">
              Export Proposal (Markdown)
            </button>
            <button onClick={() => handleExport("docx")} className="btn-secondary">
              Export Proposal (DOCX)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
