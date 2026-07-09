import { useEffect } from "react";
import api from "@/lib/api";
import { useInboxStore, type ThreadMessage, type ThreadResponse } from "@/store/inbox";

const USE_DEMO_DATA = import.meta.env.VITE_USE_DEMO_DATA === "true";

function minutesAgo(m: number): string {
  return new Date(Date.now() - m * 60_000).toISOString();
}

const DUMMY_THREADS: ThreadResponse[] = [
  {
    session_id: "sess-001",
    customer_id: "cust-001",
    customer_name: "Rina Wijaya",
    platform: "facebook",
    channel_type: "comment",
    status: "open",
    is_continuation: false,
    prior_session_id: null,
    prior_session_date: null,
    message_count: 3,
    has_human_takeover: false,
    last_message_at: minutesAgo(5),
    messages: [
      {
        id: "msg-001",
        message_in: "Hi, I'd like to ask about the price",
        message_out: "Hello! This product is priced at Rp 250,000. Anything else I can help with?",
        intent: "tanya_info",
        sentiment: "neutral",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(30),
      },
      {
        id: "msg-002",
        message_in: "Does it come with a warranty?",
        message_out: "Yes, all our products come with a full 1-year warranty 😊",
        intent: "tanya_info",
        sentiment: "neutral",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(15),
      },
      {
        id: "msg-003",
        message_in: "Alright, I want to buy it",
        message_out: null,
        intent: "niat_beli",
        sentiment: "positive",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(5),
      },
    ],
  },
  {
    session_id: "sess-002",
    customer_id: "cust-002",
    customer_name: "Budi Santoso",
    platform: "instagram",
    channel_type: "dm",
    status: "open",
    is_continuation: true,
    prior_session_id: "sess-000",
    prior_session_date: minutesAgo(1440),
    message_count: 2,
    has_human_takeover: true,
    last_message_at: minutesAgo(2),
    messages: [
      {
        id: "msg-004",
        message_in: "This is the second time I'm asking, where is my order?!",
        message_out: "I apologize for the inconvenience. Let me check your order status right away.",
        intent: "komplain",
        sentiment: "negative",
        is_human_takeover: true,
        escalation_reason: "customer_escalated",
        created_at: minutesAgo(10),
      },
      {
        id: "msg-005",
        message_in: "I want a refund now!",
        message_out: null,
        intent: "komplain",
        sentiment: "negative",
        is_human_takeover: true,
        escalation_reason: null,
        created_at: minutesAgo(2),
      },
    ],
  },
  {
    session_id: "sess-003",
    customer_id: "cust-003",
    customer_name: "Sari Dewi",
    platform: "whatsapp",
    channel_type: "dm",
    status: "open",
    is_continuation: false,
    prior_session_id: null,
    prior_session_date: null,
    message_count: 1,
    has_human_takeover: false,
    last_message_at: minutesAgo(60),
    messages: [
      {
        id: "msg-006",
        message_in: "Good evening, is this product still available?",
        message_out: "Good evening! Yes, it's still in stock. Would you like to place an order?",
        intent: "tanya_info",
        sentiment: "neutral",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(60),
      },
    ],
  },
  {
    session_id: "sess-004",
    customer_id: "cust-004",
    customer_name: "Ahmad Fauzi",
    platform: "facebook",
    channel_type: "comment",
    status: "closed",
    is_continuation: false,
    prior_session_id: null,
    prior_session_date: null,
    message_count: 4,
    has_human_takeover: false,
    last_message_at: minutesAgo(180),
    messages: [
      {
        id: "msg-007",
        message_in: "How much is shipping?",
        message_out: "Free shipping for orders above Rp 500,000!",
        intent: "tanya_info",
        sentiment: "neutral",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(240),
      },
      {
        id: "msg-008",
        message_in: "Great, I'll take two",
        message_out: "Noted! Your order total is Rp 600,000 with free shipping.",
        intent: "niat_beli",
        sentiment: "positive",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(210),
      },
      {
        id: "msg-009",
        message_in: "Payment confirmed",
        message_out: "Thank you! Your order will be shipped within 1x24 hours 🚚",
        intent: "niat_beli",
        sentiment: "positive",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(200),
      },
      {
        id: "msg-010",
        message_in: "Thank you!",
        message_out: "You're welcome! Happy shopping 😊",
        intent: "tanya_info",
        sentiment: "positive",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(180),
      },
    ],
  },
  {
    session_id: "sess-005",
    customer_id: "cust-005",
    customer_name: "Maya Putri",
    platform: "messenger",
    channel_type: "dm",
    status: "open",
    is_continuation: false,
    prior_session_id: null,
    prior_session_date: null,
    message_count: 1,
    has_human_takeover: false,
    last_message_at: minutesAgo(20),
    messages: [
      {
        id: "msg-011",
        message_in: "Promo code not working",
        message_out: "I'm sorry about that. Let me help you with a new promo code.",
        intent: "komplain",
        sentiment: "negative",
        is_human_takeover: false,
        escalation_reason: null,
        created_at: minutesAgo(20),
      },
    ],
  },
];

export function useConversations() {
  const { filter, setThreads, toggleTakeoverInThread } = useInboxStore();

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter === "ai") params.is_human_takeover = "false";
    if (filter === "human") params.is_human_takeover = "true";

    function fetchThreads() {
      if (USE_DEMO_DATA) {
        setThreads(DUMMY_THREADS);
        return;
      }

      api
        .get<{ data: ThreadResponse[] }>("/conversations/threads", { params })
        .then((res) => {
          if (res.data.data && res.data.data.length > 0) {
            setThreads(res.data.data);
          } else {
            setThreads([]);
          }
        })
        .catch(() => {
          setThreads([]);
        });
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
