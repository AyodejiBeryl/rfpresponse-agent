"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { useProject } from "@/hooks/useProjects";
import { useConversations, useCreateConversation, useMessages } from "@/hooks/useChat";
import { api } from "@/lib/api";
import type { Message } from "@/types";

export default function ChatPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project } = useProject(projectId);
  const { data: conversations, refetch: refetchConversations } = useConversations(projectId);
  const createConversation = useCreateConversation(projectId);

  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: loadedMessages } = useMessages(
    projectId,
    activeConvId || ""
  );

  useEffect(() => {
    if (loadedMessages) setMessages(loadedMessages);
  }, [loadedMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  const sectionKeys = project ? Object.keys(project.draft_sections) : [];

  const handleNewConversation = async () => {
    const conv = await createConversation.mutateAsync({
      section_key: selectedSection || undefined,
      title: selectedSection
        ? `Refine ${selectedSection.replace(/_/g, " ")}`
        : "General proposal chat",
    });
    setActiveConvId(conv.id);
    setMessages([]);
    refetchConversations();
  };

  const handleSend = useCallback(async () => {
    if (!input.trim() || !activeConvId || streaming) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      conversation_id: activeConvId,
      role: "user",
      content: input.trim(),
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setStreaming(true);
    setStreamText("");

    try {
      const stream = api.streamPost(
        `/api/v1/projects/${projectId}/conversations/${activeConvId}/messages`,
        { content: userMessage.content }
      );

      let fullText = "";
      for await (const chunk of stream) {
        fullText += chunk;
        setStreamText(fullText);
      }

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        conversation_id: activeConvId,
        role: "assistant",
        content: fullText,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setStreamText("");
    } catch {
      setStreamText("Error: Failed to get response. Please try again.");
    } finally {
      setStreaming(false);
    }
  }, [input, activeConvId, streaming, projectId]);

  const currentSection = selectedSection && project?.draft_sections[selectedSection];

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] lg:h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}`} className="text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
          </Link>
          <h1 className="text-lg font-bold text-gray-900">AI Chat Refinement</h1>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedSection}
            onChange={(e) => setSelectedSection(e.target.value)}
            className="input-field w-auto text-sm"
          >
            <option value="">General</option>
            {sectionKeys.map((key) => (
              <option key={key} value={key}>
                {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>
          <button onClick={handleNewConversation} className="btn-secondary text-sm">
            New Chat
          </button>
        </div>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden flex-col lg:flex-row">
        {/* Section preview (desktop) */}
        {currentSection && (
          <div className="hidden lg:block lg:w-1/2 overflow-y-auto card">
            <h3 className="font-semibold text-gray-900 mb-3">
              {selectedSection.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </h3>
            <div className="prose prose-sm max-w-none text-gray-700">
              <ReactMarkdown>{currentSection}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Chat panel */}
        <div className={`flex flex-1 flex-col card p-0 overflow-hidden ${currentSection ? "lg:w-1/2" : ""}`}>
          {!activeConvId ? (
            <div className="flex flex-1 items-center justify-center p-6">
              <div className="text-center">
                <p className="text-gray-500 mb-4">
                  Select a section and start a new chat to refine your proposal.
                </p>
                <button onClick={handleNewConversation} className="btn-primary">
                  Start Chat
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                        msg.role === "user"
                          ? "bg-primary-600 text-white"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {msg.role === "assistant" ? (
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}
                {streaming && streamText && (
                  <div className="flex justify-start">
                    <div className="max-w-[80%] rounded-xl px-4 py-2.5 text-sm bg-gray-100 text-gray-800">
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown>{streamText}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="border-t border-gray-200 p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                    placeholder="Ask to refine this section..."
                    className="input-field flex-1"
                    disabled={streaming}
                  />
                  <button
                    onClick={handleSend}
                    disabled={streaming || !input.trim()}
                    className="btn-primary"
                  >
                    Send
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
