"use client";

import { useCallback, useRef, useState, useEffect } from "react";
import { ChatMessage, type ChatMsg } from "@/components/ChatMessage";
import * as api from "@/lib/api";

interface ChatSidebarProps {
  /** Called when the AI mutates the board so the parent can refresh. */
  onBoardUpdated?: () => void;
}

let nextId = 1;
function genId() {
  return `msg-${nextId++}`;
}

/** Reset ID counter (for tests). */
export function resetIdCounter() {
  nextId = 1;
}

export const ChatSidebar = ({ onBoardUpdated }: ChatSidebarProps) => {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      if (listRef.current) {
        listRef.current.scrollTop = listRef.current.scrollHeight;
      }
    });
  }, []);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  const sendToAI = useCallback(
    async (userMessage: string, history: ChatMsg[]) => {
      setSending(true);
      try {
        const apiHistory = history.map((m) => ({
          role: m.role,
          content: m.content,
        }));
        const result = await api.sendChatMessage(userMessage, apiHistory);

        const assistantMsg: ChatMsg = {
          id: genId(),
          role: "assistant",
          content: result.message,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        if (result.board_update) {
          onBoardUpdated?.();
        }
      } catch {
        const errorMsg: ChatMsg = {
          id: genId(),
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setSending(false);
      }
    },
    [onBoardUpdated]
  );

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: ChatMsg = { id: genId(), role: "user", content: text };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInput("");

    sendToAI(text, messages);
  }, [input, sending, messages, sendToAI]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleEdit = useCallback(
    (id: string, content: string) => {
      if (sending) return;
      const idx = messages.findIndex((m) => m.id === id);
      if (idx === -1) return;

      // Replace the message and remove all subsequent ones
      const edited: ChatMsg = { ...messages[idx], content };
      const truncated = [...messages.slice(0, idx), edited];
      setMessages(truncated);

      // Re-send to AI with the edited history
      const historyForAI = truncated.slice(0, -1);
      sendToAI(content, historyForAI);
    },
    [messages, sending, sendToAI]
  );

  const handleDelete = useCallback(
    (id: string) => {
      if (sending) return;
      const idx = messages.findIndex((m) => m.id === id);
      if (idx === -1) return;
      setMessages(messages.slice(0, idx));
    },
    [messages, sending]
  );

  return (
    <aside className="flex h-full w-[350px] shrink-0 flex-col rounded-[32px] border border-[var(--stroke)] bg-white/80 shadow-[var(--shadow)] backdrop-blur">
      {/* Header */}
      <div className="border-b border-[var(--stroke)] px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
          AI Assistant
        </p>
        <p className="mt-1 text-sm font-semibold text-[var(--navy-dark)]">
          Chat
        </p>
        <div className="mt-2 h-0.5 w-8 rounded-full bg-[var(--accent-yellow)]" />
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="py-8 text-center text-xs text-[var(--gray-text)]">
            Ask the AI to create, move, edit, or delete cards on your board.
          </p>
        )}
        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        ))}
        {sending && (
          <div className="flex items-center gap-2 text-xs text-[var(--gray-text)]">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--primary-blue)]" />
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-[var(--stroke)] px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the AI..."
            disabled={sending}
            className="flex-1 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none placeholder:text-[var(--gray-text)] focus:border-[var(--primary-blue)]"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </aside>
  );
};
