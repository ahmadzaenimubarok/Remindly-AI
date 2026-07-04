import { create } from "zustand";

export interface ThreadMessage {
  id: string;
  message_in: string | null;
  message_out: string | null;
  intent: string | null;
  sentiment: string | null;
  is_human_takeover: boolean;
  escalation_reason: string | null;
  created_at: string;
}

export interface ThreadResponse {
  session_id: string;
  customer_id: string;
  customer_name: string | null;
  platform: string;
  channel_type: string;
  status: "open" | "closed";
  is_continuation: boolean;
  prior_session_id: string | null;
  prior_session_date: string | null;
  message_count: number;
  has_human_takeover: boolean;
  last_message_at: string;
  messages: ThreadMessage[];
}

// Legacy — masih dipakai oleh takeover PATCH
export interface ConversationResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  session_id: string | null;
  platform: string;
  channel_type: string;
  message_in: string | null;
  message_out: string | null;
  intent: string | null;
  sentiment: string | null;
  is_human_takeover: boolean;
  escalation_reason: string | null;
  created_at: string;
}

type Filter = "all" | "ai" | "human";

interface InboxStore {
  threads: ThreadResponse[];
  filter: Filter;
  expanded: string | null; // session_id yang sedang dibuka
  setThreads: (t: ThreadResponse[]) => void;
  setFilter: (f: Filter) => void;
  setExpanded: (id: string | null) => void;
  toggleTakeoverInThread: (sessionId: string, msgId: string, value: boolean) => void;
  // legacy compat
  conversations: ConversationResponse[];
  setConversations: (c: ConversationResponse[]) => void;
  toggleTakeover: (id: string, value: boolean) => void;
}

export const useInboxStore = create<InboxStore>((set) => ({
  threads: [],
  filter: "all",
  expanded: null,
  setThreads: (threads) => set({ threads }),
  setFilter: (filter) => set({ filter }),
  setExpanded: (id) =>
    set((state) => ({ expanded: state.expanded === id ? null : id })),
  toggleTakeoverInThread: (sessionId, msgId, value) =>
    set((state) => ({
      threads: state.threads.map((t) =>
        t.session_id === sessionId
          ? {
              ...t,
              has_human_takeover: value || t.messages.some((m) => m.id !== msgId && m.is_human_takeover),
              messages: t.messages.map((m) =>
                m.id === msgId ? { ...m, is_human_takeover: value } : m
              ),
            }
          : t
      ),
    })),
  // legacy
  conversations: [],
  setConversations: (conversations) => set({ conversations }),
  toggleTakeover: (id, value) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, is_human_takeover: value } : c
      ),
    })),
}));
