import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface KnowledgeDoc {
  id: string;
  title: string;
  doc_type: string;
  original_filename: string | null;
  is_indexed: boolean;
  created_at: string;
}

export interface KnowledgeDocDetail extends KnowledgeDoc {
  extracted_text: string | null;
  updated_at: string;
}

export interface SearchResult {
  chunk_id: string;
  chunk_text: string;
  document_id: string;
  doc_title: string;
  similarity: number;
}

export function useKnowledgeDocs() {
  return useQuery<KnowledgeDoc[]>({
    queryKey: ["knowledge"],
    queryFn: () => api.get("/api/v1/knowledge"),
  });
}

export function useKnowledgeDoc(id: string) {
  return useQuery<KnowledgeDocDetail>({
    queryKey: ["knowledge", id],
    queryFn: () => api.get(`/api/v1/knowledge/${id}`),
    enabled: !!id,
  });
}

export function useUploadKnowledge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.post<KnowledgeDoc>("/api/v1/knowledge", formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
  });
}

export function useDeleteKnowledge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/knowledge/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
  });
}

export function useKnowledgeSearch() {
  return useMutation({
    mutationFn: (data: { query: string; top_k?: number }) =>
      api.post<SearchResult[]>("/api/v1/knowledge/search", data),
  });
}
