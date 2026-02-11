"use client";

import Link from "next/link";
import { useProjects } from "@/hooks/useProjects";
import { formatDate, statusColor } from "@/lib/utils";

export default function ProjectsPage() {
  const { data: projects, isLoading, error } = useProjects();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-sm text-gray-500 mt-1">Your RFP analyses and proposal drafts</p>
        </div>
        <Link href="/projects/new" className="btn-primary">
          New Project
        </Link>
      </div>

      {isLoading && (
        <div className="text-center py-12 text-gray-400">Loading projects...</div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
          Failed to load projects
        </div>
      )}

      {projects && projects.length === 0 && (
        <div className="text-center py-16 card">
          <h3 className="text-lg font-medium text-gray-900">No projects yet</h3>
          <p className="mt-2 text-sm text-gray-500">
            Upload an RFP to get started with your first proposal analysis.
          </p>
          <Link href="/projects/new" className="btn-primary mt-4 inline-flex">
            Create your first project
          </Link>
        </div>
      )}

      {projects && projects.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="card hover:ring-primary-300 hover:ring-2 transition-all"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-gray-900 line-clamp-2">
                  {project.title}
                </h3>
                <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${statusColor(project.status)}`}>
                  {project.status}
                </span>
              </div>
              <div className="mt-3 space-y-1 text-sm text-gray-500">
                {project.metadata_json?.solicitation_number && project.metadata_json.solicitation_number !== "Not found" && (
                  <p>Sol #: {project.metadata_json.solicitation_number}</p>
                )}
                <p>Created {formatDate(project.created_at)}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
