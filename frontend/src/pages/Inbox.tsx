import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { useConversations } from "@/hooks/useConversations";
import { useInboxStore } from "@/store/inbox";

const FILTER_LABELS = { all: "Semua", ai: "AI", human: "Human" } as const;

const PLATFORM_ICON: Record<string, string> = {
  facebook: "🌐",
  messenger: "💬",
  instagram: "📸",
  whatsapp: "📱",
};

function truncate(text: string | null, max: number) {
  if (!text) return "—";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function relativeTime(iso: string) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}d yang lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m yang lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j yang lalu`;
  return `${Math.floor(diff / 86400)}h yang lalu`;
}

export default function Inbox() {
  const { logout } = useAuth();
  const { conversations, filter, setFilter } = useInboxStore();
  const { handleToggle } = useConversations();

  const escalatedCount = conversations.filter((c) => c.is_human_takeover).length;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex items-center gap-3">
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
          <a
            href="/leads"
            className="text-xs text-slate-500 hover:text-slate-900 transition-colors"
          >
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

      <main className="mx-auto max-w-6xl px-6 py-6">
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
          <span className="text-xs text-slate-400">
            {conversations.length} percakapan
          </span>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 border-slate-200">
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Platform
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Pesan masuk
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Intent
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Sentiment
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Status
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Waktu
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Takeover
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {conversations.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="py-16 text-center text-sm text-slate-400"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <span className="text-2xl">📭</span>
                      <span>Belum ada percakapan.</span>
                    </div>
                  </TableCell>
                </TableRow>
              )}
              {conversations.map((conv) => (
                <TableRow
                  key={conv.id}
                  className={
                    conv.is_human_takeover
                      ? "border-l-4 border-l-red-400 bg-red-50 hover:bg-red-100 border-b border-red-100"
                      : "border-b border-slate-100 hover:bg-slate-50"
                  }
                >
                  <TableCell className="text-sm text-slate-700">
                    <span className="flex items-center gap-1.5 capitalize">
                      <span>{PLATFORM_ICON[conv.platform] ?? "💬"}</span>
                      {conv.platform}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm text-slate-800 font-medium">
                        {truncate(conv.message_in, 70)}
                      </span>
                      {conv.message_out && (
                        <span className="text-xs text-slate-400 italic">
                          ↳ {truncate(conv.message_out, 50)}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {conv.intent ? (
                      <Badge
                        variant="secondary"
                        className="text-xs bg-slate-100 text-slate-700 border border-slate-200"
                      >
                        {conv.intent}
                      </Badge>
                    ) : (
                      <span className="text-slate-300 text-sm">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {conv.sentiment ? (
                      <Badge
                        className={
                          conv.sentiment === "positive"
                            ? "text-xs bg-green-100 text-green-700 border border-green-200"
                            : conv.sentiment === "negative"
                              ? "text-xs bg-red-100 text-red-700 border border-red-200"
                              : "text-xs bg-slate-100 text-slate-600 border border-slate-200"
                        }
                      >
                        {conv.sentiment}
                      </Badge>
                    ) : (
                      <span className="text-slate-300 text-sm">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={
                        conv.is_human_takeover
                          ? "text-xs bg-red-500 text-white font-semibold shadow-sm"
                          : "text-xs bg-emerald-100 text-emerald-700 border border-emerald-200"
                      }
                    >
                      {conv.is_human_takeover ? "⚠ Human" : "✓ AI"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-slate-400 whitespace-nowrap">
                    {relativeTime(conv.created_at)}
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={conv.is_human_takeover}
                      onCheckedChange={() =>
                        handleToggle(conv.id, conv.is_human_takeover)
                      }
                      aria-label="Toggle human takeover"
                      className={conv.is_human_takeover ? "data-[state=checked]:bg-red-500" : ""}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </main>
    </div>
  );
}
