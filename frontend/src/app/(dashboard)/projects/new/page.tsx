"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCreateProject, useUploadProject } from "@/hooks/useProjects";

// RFP type options for the dropdown
const RFP_TYPES = [
  { value: "", label: "Auto-detect (recommended)" },
  { value: "government_rfp", label: "Government RFP" },
  { value: "government_rfi", label: "Government RFI" },
  { value: "government_rfq", label: "Government RFQ" },
  { value: "sources_sought", label: "Sources Sought" },
  { value: "commercial_rfp", label: "Commercial RFP" },
  { value: "commercial_rfq", label: "Commercial RFQ" },
  { value: "vendor_application", label: "Vendor Application" },
  { value: "grant", label: "Grant Application" },
  { value: "custom", label: "Custom / Other" },
];

export default function NewProjectPage() {
  const router = useRouter();
  const createProject = useCreateProject();
  const uploadProject = useUploadProject();

  const [mode, setMode] = useState<"text" | "file">("file");
  const [title, setTitle] = useState("");
  const [rfpType, setRfpType] = useState("");
  const [solicitationText, setSolicitationText] = useState("");
  const [companyProfile, setCompanyProfile] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const loading = createProject.isPending || uploadProject.isPending;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      if (mode === "file" && file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", title);
        formData.append("company_profile", companyProfile);
        if (companyName) formData.append("company_name", companyName);
        if (rfpType) formData.append("rfp_type", rfpType);

        const project = await uploadProject.mutateAsync(formData);
        router.push(`/projects/${project.id}`);
      } else if (mode === "text") {
        const project = await createProject.mutateAsync({
          title,
          solicitation_text: solicitationText,
          company_profile: companyProfile,
          company_name: companyName || undefined,
          rfp_type: rfpType || undefined,
        });
        router.push(`/projects/${project.id}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">New Project</h1>

      <form onSubmit={handleSubmit} className="card space-y-6">
        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Project Title</label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="input-field"
            placeholder="e.g. IT Support Services Response"
          />
        </div>

        {/* RFP Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            RFP Type
          </label>
          <select
            value={rfpType}
            onChange={(e) => setRfpType(e.target.value)}
            className="input-field"
          >
            {RFP_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">
            Select the type of document for better extraction accuracy, or let the system auto-detect.
          </p>
        </div>

        {/* Input mode toggle */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">RFP Source</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode("file")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === "file"
                  ? "bg-primary-100 text-primary-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Upload File
            </button>
            <button
              type="button"
              onClick={() => setMode("text")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === "text"
                  ? "bg-primary-100 text-primary-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Paste Text
            </button>
          </div>
        </div>

        {mode === "file" ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Upload RFP (PDF, DOCX, or TXT)
            </label>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
            />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Solicitation Text
            </label>
            <textarea
              required={mode === "text"}
              value={solicitationText}
              onChange={(e) => setSolicitationText(e.target.value)}
              rows={10}
              className="input-field"
              placeholder="Paste the full RFP text here..."
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="input-field"
            placeholder="Optional"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Company Profile / Capability Statement
          </label>
          <textarea
            required
            value={companyProfile}
            onChange={(e) => setCompanyProfile(e.target.value)}
            rows={5}
            className="input-field"
            placeholder="Describe your company's capabilities, experience, and relevant qualifications..."
          />
        </div>

        <button
          type="submit"
          disabled={loading || (mode === "file" && !file)}
          className="btn-primary w-full"
        >
          {loading ? "Analyzing RFP..." : "Analyze & Create Project"}
        </button>
      </form>
    </div>
  );
}
