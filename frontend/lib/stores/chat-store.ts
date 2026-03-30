import { create } from "zustand";
import type { QueryResponse } from "@/lib/api/client";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  metadata?: QueryResponse;
  isLoading?: boolean;
  error?: string;
}

interface ChatStore {
  messages: ChatMessage[];
  sidebarOpen: boolean;

  addMessage: (message: Omit<ChatMessage, "id" | "timestamp">) => string;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

let messageCounter = 0;

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  sidebarOpen: true,

  addMessage: (message) => {
    const id = `msg-${++messageCounter}-${Date.now()}`;
    set((state) => ({
      messages: [...state.messages, { ...message, id, timestamp: Date.now() }],
    }));
    return id;
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    }));
  },

  clearMessages: () => set({ messages: [] }),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
