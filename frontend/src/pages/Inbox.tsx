import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { useConversations } from "@/hooks/useConversations";
import { useInboxStore, type ThreadMessage } from "@/store/inbox";

const FILTER_LABELS = { all: "Semua", ai: "AI", human: "Human" } as const;

const PLATFORM_ICON: Record<string, string> = {
  facebook: "🌐",
  messenger: "💬",
  instagram: "📸",
  whatsapp: "📱",
};

const INTENT_LABEL: Record<string, string> = {
  niat_beli: "Niat beli",
  tanya_info: "Tanya info",
  komplain: "Komplain",
  spam: "Spam",
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
  if (diff < 60) return `${diff}d lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
  return `${Math.floor(diff / 86400)}h lalu`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
  });
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
  return (
    <div
      className={[
        "flex flex-col gap-1.5 px-4 py-3 border-b border-slate-100 last:border-0",
        msg.is_human_takeover ? "bg-red-50" : "bg-white",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          {/* Pesan masuk */}
          {msg.message_in && (
            <div className="flex items-start gap-2">
              <span className="mt-0.5 text-[10px] text-slate-400 w-8 shrink-0 text-right">
                {formatTime(msg.created_at)}
              </span>
              <p className="text-sm text-slate-800">{msg.message_in}</p>
            </div>
          )}
          {/* Balasan AI */}
          {msg.message_out && (
            <div className="flex items-start gap-2">
              <span className="mt-0.5 text-[10px] text-slate-400 w-8 shrink-0 text-right">
                ↳
              </span>
              <p className="text-sm text-slate-500 italic">{msg.message_out}</p>
            </div>
          )}
        </div>

        {/* Tags + toggle */}
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
              {msg.sentiment}
            </Badge>
          )}
          <button
            onClick={() => onToggle(sessionId, msg.id, msg.is_human_takeover)}
            aria-label="Toggle human takeover"
            className={[
              "rounded-md px-2.5 py-1 text-xs font-semibold border transition-colors",
              msg.is_human_takeover
                ? "bg-red-500 text-white border-red-500 hover:bg-red-600"
                : "bg-white text-slate-500 border-slate-300 hover:border-slate-400 hover:text-slate-700",
            ].join(" ")}
          >
            {msg.is_human_takeover ? "⚠ Human" : "AI"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Inbox() {
  const { logout } = useAuth();
  const { threads, filter, setFilter, expanded, setExpanded } = useInboxStore();
  const { handleToggle } = useConversations();

  const escalatedCount = threads.filter((t) => t.has_human_takeover).length;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <img src="/logo.jpeg" alt="Reseller AI" className="h-7 w-7 rounded-full object-cover" />
          <span className="text-sm font-semibold text-slate-900">
            Reseller AI — Inbox
          </span>
          {escalatedCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse inline-block" />
              {escalatedCount} perlu ditangani
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <a href="/leads" className="text-xs text-slate-500 hover:text-slate-900 transition-colors">
            Leads
          </a>
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="text-slate-500 hover:text-slate-900"
          >
            Keluar
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-6">
        {/* Filter bar */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-2">
            {(["all", "ai", "human"] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
                className={
                  filter === f
                    ? "bg-slate-900 text-white hover:bg-slate-800"
                    : "border-slate-300 text-slate-600 hover:bg-slate-50"
                }
              >
                {FILTER_LABELS[f]}
                {f === "human" && escalatedCount > 0 && (
                  <span className="ml-1.5 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white leading-none">
                    {escalatedCount}
                  </span>
                )}
              </Button>
            ))}
          </div>
          <span className="text-xs text-slate-400">{threads.length} sesi</span>
        </div>

        {/* Thread list */}
        <div className="flex flex-col gap-2">
          {threads.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-sm text-slate-400">
              <span className="text-2xl">📭</span>
              <span>Belum ada percakapan.</span>
            </div>
          )}

          {threads.map((thread) => {
            const isOpen = expanded === thread.session_id;
            const displayName = thread.customer_name ?? "Pengguna tanpa nama";

            return (
              <div
                key={thread.session_id}
                className={[
                  "rounded-lg border bg-white shadow-sm overflow-hidden",
                  thread.has_human_takeover
                    ? "border-red-300"
                    : "border-slate-200",
                ].join(" ")}
              >
                {/* Thread header — klik untuk expand */}
                <button
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                  onClick={() => setExpanded(thread.session_id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm">
                      {PLATFORM_ICON[thread.platform] ?? "💬"}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-900">
                          {displayName}
                        </span>
                        {thread.is_continuation && thread.prior_session_date && (
                          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200">
                            Lanjutan dari sesi{" "}
                            {new Date(thread.prior_session_date).toLocaleDateString("id-ID", {
                              day: "numeric",
                              month: "short",
                            })}
                          </span>
                        )}
                        {thread.status === "closed" && (
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500 border border-slate-200">
                            Selesai
                          </span>
                        )}
                        {thread.has_human_takeover && (
                          <span className="rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-semibold text-white">
                            ⚠ Human
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400">
                        {thread.message_count} pesan ·{" "}
                        {relativeTime(thread.last_message_at)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {/* Preview pesan terakhir */}
                    {!isOpen && (
                      <span className="text-xs text-slate-400 max-w-48 truncate hidden sm:block">
                        {truncate(
                          thread.messages[thread.messages.length - 1]?.message_in,
                          60
                        )}
                      </span>
                    )}
                    <span className="text-slate-400 text-sm select-none">
                      {isOpen ? "↑" : "↓"}
                    </span>
                  </div>
                </button>

                {/* Messages */}
                {isOpen && (
                  <div className="border-t border-slate-100">
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
      </main>
    </div>
  );
}
