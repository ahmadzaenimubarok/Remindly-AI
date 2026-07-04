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

function sentimentVariant(
  s: string | null
): "default" | "secondary" | "destructive" {
  if (s === "positive") return "default";
  if (s === "negative") return "destructive";
  return "secondary";
}

export default function Inbox() {
  const { logout } = useAuth();
  const { conversations, filter, setFilter } = useInboxStore();
  const { handleToggle } = useConversations();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <span className="text-sm font-semibold text-slate-900">
          Reseller AI — Inbox
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          className="text-slate-500 hover:text-slate-900"
        >
          Keluar
        </Button>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-6">
          <div className="mb-4 flex gap-2">
            {(["all", "ai", "human"] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? "default" : "outline"}
                onClick={() => setFilter(f)}
                className={
                  filter === f
                    ? "bg-slate-900 text-white"
                    : "border-slate-300 text-slate-600"
                }
              >
                {FILTER_LABELS[f]}
              </Button>
            ))}
          </div>

          <div className="rounded-md border border-slate-200 bg-white shadow-sm">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-200">
                  <TableHead className="text-xs font-medium text-slate-500">
                    Platform
                  </TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">
                    Pesan masuk
                  </TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">
                    Intent
                  </TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">
                    Sentiment
                  </TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">
                    Status
                  </TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">
                    Waktu
                  </TableHead>
                  <TableHead className="text-xs font-medium text-slate-500">
                    Human takeover
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={7}
                      className="py-10 text-center text-sm text-slate-400"
                    >
                      Belum ada percakapan.
                    </TableCell>
                  </TableRow>
                )}
                {conversations.map((conv) => (
                  <TableRow key={conv.id} className="border-slate-100">
                    <TableCell className="text-sm capitalize text-slate-700">
                      {conv.platform}
                    </TableCell>
                    <TableCell className="max-w-xs text-sm text-slate-600">
                      {truncate(conv.message_in, 80)}
                    </TableCell>
                    <TableCell>
                      {conv.intent ? (
                        <Badge variant="secondary" className="text-xs">
                          {conv.intent}
                        </Badge>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {conv.sentiment ? (
                        <Badge
                          variant={sentimentVariant(conv.sentiment)}
                          className="text-xs"
                        >
                          {conv.sentiment}
                        </Badge>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          conv.is_human_takeover ? "destructive" : "secondary"
                        }
                        className="text-xs"
                      >
                        {conv.is_human_takeover ? "Human" : "AI"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {relativeTime(conv.created_at)}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={conv.is_human_takeover}
                        onCheckedChange={() =>
                          handleToggle(conv.id, conv.is_human_takeover)
                        }
                        aria-label="Toggle human takeover"
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
