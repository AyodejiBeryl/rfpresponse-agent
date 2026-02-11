import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Project, ProjectListItem } from "@/types";

export function useProjects() {
  return useQuery<ProjectListItem[]>({
    queryKey: ["projects"],
    queryFn: () => api.get("/api/v1/projects"),
  });
}

export function useProject(id: string) {
  return useQuery<Project>({
    queryKey: ["project", id],
    queryFn: () => api.get(`/api/v1/projects/${id}`),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      title: string;
      solicitation_text: string;
      company_profile: string;
      company_name?: string;
      past_performance?: string[];
      capability_statement?: string;
    }) => api.post<Project>("/api/v1/projects", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useUploadProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.post<Project>("/api/v1/projects/upload", formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
