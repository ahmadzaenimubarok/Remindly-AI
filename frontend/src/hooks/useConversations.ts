import { useEffect } from "react";
import api from "@/lib/api";
import { useInboxStore, type ThreadMessage, type ThreadResponse } from "@/store/inbox";

export function useConversations() {
  const { filter, setThreads, toggleTakeoverInThread } = useInboxStore();

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter === "ai") params.is_human_takeover = "false";
    if (filter === "human") params.is_human_takeover = "true";

    function fetchThreads() {
      api
        .get<{ data: ThreadResponse[] }>("/conversations/threads", { params })
        .then((res) => setThreads(res.data.data))
        .catch(() => {});
    }

    fetchThreads();
    const timer = setInterval(fetchThreads, 10_000);
    return () => clearInterval(timer);
  }, [filter, setThreads]);

  async function handleToggle(sessionId: string, msgId: string, currentValue: boolean) {
    const newValue = !currentValue;
    toggleTakeoverInThread(sessionId, msgId, newValue);
    try {
      await api.patch(`/conversations/${msgId}/takeover`, {
        is_human_takeover: newValue,
      });
    } catch {
      toggleTakeoverInThread(sessionId, msgId, currentValue);
    }
  }

  async function handleSessionToggle(
    sessionId: string,
    messages: ThreadMessage[],
    newValue: boolean,
    onSuccess?: () => void,
    onError?: () => void,
  ) {
    messages.forEach((m) => toggleTakeoverInThread(sessionId, m.id, newValue));
    try {
      await Promise.all(
        messages.map((m) =>
          api.patch(`/conversations/${m.id}/takeover`, { is_human_takeover: newValue }),
        ),
      );
      onSuccess?.();
    } catch {
      messages.forEach((m) => toggleTakeoverInThread(sessionId, m.id, !newValue));
      onError?.();
    }
  }

  return { handleToggle, handleSessionToggle };
}
