import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Conversation, Message } from "@/types";

export function useConversations(projectId: string) {
  return useQuery<Conversation[]>({
    queryKey: ["conversations", projectId],
    queryFn: () =>
      api.get(`/api/v1/projects/${projectId}/conversations`),
    enabled: !!projectId,
  });
}

export function useMessages(projectId: string, conversationId: string) {
  return useQuery<Message[]>({
    queryKey: ["messages", conversationId],
    queryFn: () =>
      api.get(
        `/api/v1/projects/${projectId}/conversations/${conversationId}/messages`
      ),
    enabled: !!projectId && !!conversationId,
  });
}

export function useCreateConversation(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { title?: string; section_key?: string }) =>
      api.post<Conversation>(
        `/api/v1/projects/${projectId}/conversations`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["conversations", projectId],
      });
    },
  });
}
