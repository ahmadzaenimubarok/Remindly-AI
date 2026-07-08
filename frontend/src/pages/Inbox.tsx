import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConversations } from "@/hooks/useConversations";
import { useInboxStore, type ThreadMessage } from "@/store/inbox";
import AppLayout from "@/components/AppLayout";

const FILTER_LABELS = { all: "All", ai: "AI", human: "Human" } as const;

const PLATFORM_ICON: Record<string, string> = {
  facebook: "🌐",
  messenger: "💬",
  instagram: "📸",
  whatsapp: "📱",
};

const INTENT_LABEL: Record<string, string> = {
  niat_beli: "Purchase intent",
  tanya_info: "Info inquiry",
  komplain: "Complaint",
  spam: "Spam",
};

const SENTIMENT_LABEL: Record<string, string> = {
  positive: "Positive",
  negative: "Negative",
  neutral: "Neutral",
};

const SENTIMENT_CLASS: Record<string, string> = {
  positive: "bg-emerald-100 text-emerald-700 border-emerald-200",
  negative: "bg-red-100 text-red-700 border-red-200",
  neutral: "bg-slate-100 text-slate-600 border-slate-200",
};

function truncate(text: string | null, max: number) {
  if (!text) return "—";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function relativeTime(iso: string) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Toast notification — shows for 3 seconds then disappears
function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 shadow-md"
    >
      {message}
    </div>
  );
}

// TakeoverButton — hold 600ms to confirm, or quick click shows hint
function TakeoverButton({
  active,
  onConfirm,
  disabled,
}: {
  active: boolean;
  onConfirm: () => void;
  disabled: boolean;
}) {
  const holdTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [holding, setHolding] = useState(false);
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);
  const HOLD_MS = 600;

  function startHold(e: React.MouseEvent | React.TouchEvent) {
    e.stopPropagation();
    if (disabled) return;
    startRef.current = Date.now();
    setHolding(true);
    setProgress(0);

    function tick() {
      const elapsed = Date.now() - startRef.current;
      const p = Math.min(elapsed / HOLD_MS, 1);
      setProgress(p);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setHolding(false);
        setProgress(0);
        onConfirm();
      }
    }
    rafRef.current = requestAnimationFrame(tick);
  }

  function cancelHold() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (holdTimer.current) clearTimeout(holdTimer.current);
    setHolding(false);
    setProgress(0);
  }

  useEffect(() => () => cancelHold(), []);

  const label = active ? "⚠ Human" : "AI";
  const ariaLabel = active ? "Hold to switch back to AI mode" : "Hold to switch to Human mode";

  return (
    <button
      onMouseDown={startHold}
      onMouseUp={cancelHold}
      onMouseLeave={cancelHold}
      onTouchStart={startHold}
      onTouchEnd={cancelHold}
      aria-label={ariaLabel}
      title={ariaLabel}
      disabled={disabled}
      className={[
        "relative overflow-hidden rounded-md px-2.5 py-1 text-xs font-semibold border transition-colors select-none",
        active
          ? "bg-red-500 text-white border-red-500 hover:bg-red-600"
          : "bg-white text-slate-500 border-slate-300 hover:border-slate-400 hover:text-slate-700",
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
      ].join(" ")}
    >
      {holding && (
        <span
          aria-hidden="true"
          className={[
            "absolute inset-0 origin-left transition-none",
            active ? "bg-red-700/30" : "bg-slate-900/10",
          ].join(" ")}
          style={{ transform: `scaleX(${progress})` }}
        />
      )}
      <span className="relative">{label}</span>
    </button>
  );
}

function MessageRow({
  msg,
  sessionId,
  onToggle,
}: {
  msg: ThreadMessage;
  sessionId: string;
  onToggle: (sessionId: string, msgId: string, current: boolean) => void;
}) {
  const [pending, setPending] = useState(false);

  async function handleConfirm() {
    setPending(true);
    await onToggle(sessionId, msg.id, msg.is_human_takeover);
    setPending(false);
  }

  return (
    <div
      className={[
        "flex flex-col gap-1.5 px-4 py-3 border-b border-slate-100 last:border-0",
        msg.is_human_takeover ? "bg-red-50" : "bg-white",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          {msg.message_in && (
            <div className="flex items-start gap-2">
              <span
                className="mt-0.5 text-[10px] text-slate-400 w-8 shrink-0 text-right"
                aria-hidden="true"
              >
                {formatTime(msg.created_at)}
              </span>
              <p className="text-sm text-slate-800">{msg.message_in}</p>
            </div>
          )}
          {msg.message_out && (
            <div className="flex items-start gap-2">
              <span
                className="mt-0.5 text-[10px] text-slate-400 w-8 shrink-0 text-right"
                aria-hidden="true"
              >
                ↳
              </span>
              <p className="text-sm text-slate-500 italic">{msg.message_out}</p>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {msg.intent && (
            <Badge className="text-xs bg-slate-100 text-slate-600 border border-slate-200">
              {INTENT_LABEL[msg.intent] ?? msg.intent}
            </Badge>
          )}
          {msg.sentiment && (
            <Badge
              className={`text-xs border ${SENTIMENT_CLASS[msg.sentiment] ?? "bg-slate-100 text-slate-600 border-slate-200"}`}
            >
              {SENTIMENT_LABEL[msg.sentiment] ?? msg.sentiment}
            </Badge>
          )}
          <TakeoverButton
            active={msg.is_human_takeover}
            onConfirm={handleConfirm}
            disabled={pending}
          />
        </div>
      </div>
    </div>
  );
}

export default function Inbox() {
  const { threads, filter, setFilter, expanded, setExpanded } = useInboxStore();
  const { handleToggle, handleSessionToggle } = useConversations();
  const [toast, setToast] = useState<string | null>(null);

  const escalatedCount = threads.filter((t) => t.has_human_takeover).length;

  function showToast(msg: string) {
    setToast(msg);
  }

  return (
    <AppLayout escalatedCount={escalatedCount}>
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      <div className="mx-auto max-w-4xl px-4 sm:px-6 py-6">
        {/* Filter bar */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-2" role="group" aria-label="Filter conversations">
            {(["all", "ai", "human"] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
                className={
                  filter === f
                    ? "bg-slate-900 text-white hover:bg-slate-800"
                    : "border-slate-300 text-slate-600 hover:bg-slate-50"
                }
              >
                {FILTER_LABELS[f]}
                {f === "human" && escalatedCount > 0 && (
                  <span
                    className="ml-1.5 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white leading-none"
                    aria-label={`${escalatedCount} escalated`}
                  >
                    {escalatedCount}
                  </span>
                )}
              </Button>
            ))}
          </div>
          <span className="text-xs text-slate-400" aria-live="polite">
            {threads.length} conversations
          </span>
        </div>

        {/* Thread list */}
        <div className="flex flex-col gap-2" role="list" aria-label="Conversations">
          {threads.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-sm text-slate-400">
              <span aria-hidden="true" className="text-2xl">📭</span>
              <span>No conversations yet.</span>
            </div>
          )}

          {threads.map((thread) => {
            const isOpen = expanded === thread.session_id;
            const displayName = thread.customer_name ?? "Unknown user";
            const lastMsg =
              thread.messages[thread.messages.length - 1];
            const preview =
              lastMsg?.message_out ?? lastMsg?.message_in ?? null;

            return (
              <div
                key={thread.session_id}
                role="listitem"
                className={[
                  "rounded-lg border bg-white shadow-sm overflow-hidden",
                  thread.has_human_takeover ? "border-red-300" : "border-slate-200",
                ].join(" ")}
              >
                {/* Thread header */}
                <div className="flex items-start justify-between px-4 py-3 hover:bg-slate-50 transition-colors">
                  {/* Expand trigger — kiri */}
                  <button
                    className="flex items-center gap-3 flex-1 min-w-0 text-left"
                    onClick={() => setExpanded(thread.session_id)}
                    aria-expanded={isOpen}
                    aria-label={`${displayName} — ${thread.message_count} messages, ${relativeTime(thread.last_message_at)}`}
                  >
                    <div
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm"
                      aria-hidden="true"
                    >
                      {PLATFORM_ICON[thread.platform] ?? "💬"}
                    </div>
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-900">
                          {displayName}
                        </span>
                        {thread.is_continuation && thread.prior_session_date && (
                          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200">
                            Continuation from{" "}
                            {new Date(thread.prior_session_date).toLocaleDateString("en-US", {
                              day: "numeric",
                              month: "short",
                            })}
                          </span>
                        )}
                        {thread.status === "closed" && (
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500 border border-slate-200">
                            Closed
                          </span>
                        )}
                        {thread.has_human_takeover && (
                          <span
                            className="rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-semibold text-white"
                            aria-label="Handled by human"
                          >
                            ⚠ Human
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400">
                        {thread.message_count} messages · {relativeTime(thread.last_message_at)}
                      </span>
                      {/* Preview always visible — not hidden on mobile */}
                      {!isOpen && preview && (
                        <span className="text-xs text-slate-400 truncate max-w-xs mt-0.5">
                          {truncate(preview, 55)}
                        </span>
                      )}
                    </div>
                  </button>

                  {/* Session-level takeover + chevron — kanan */}
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    <TakeoverButton
                      active={thread.has_human_takeover}
                      disabled={false}
                      onConfirm={() =>
                        handleSessionToggle(
                          thread.session_id,
                          thread.messages,
                          !thread.has_human_takeover,
                          () =>
                            showToast(
                              thread.has_human_takeover
                                ? "AI is active again"
                                : "Human mode — AI paused",
                            ),
                          () => showToast("Failed to change mode. Try again."),
                        )
                      }
                    />
                    <span
                      className="text-slate-400 text-sm select-none"
                      aria-hidden="true"
                    >
                      {isOpen ? "↑" : "↓"}
                    </span>
                  </div>
                </div>

                {/* Messages (expanded) */}
                {isOpen && (
                  <div className="border-t border-slate-100" role="region" aria-label="Messages">
                    {thread.messages.map((msg) => (
                      <MessageRow
                        key={msg.id}
                        msg={msg}
                        sessionId={thread.session_id}
                        onToggle={handleToggle}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}
