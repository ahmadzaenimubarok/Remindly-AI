import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/useAuth";
import { useLeads } from "@/hooks/useLeads";

const TIER_CONFIG = {
  hot: {
    label: "Panas",
    className: "bg-red-100 text-red-700 border border-red-200",
    dot: "bg-red-500",
  },
  warm: {
    label: "Hangat",
    className: "bg-amber-100 text-amber-700 border border-amber-200",
    dot: "bg-amber-500",
  },
  cold: {
    label: "Dingin",
    className: "bg-slate-100 text-slate-600 border border-slate-200",
    dot: "bg-slate-400",
  },
} as const;

const REASON_LABEL: Record<string, string> = {
  "niat_beli:positive": "Niat beli — positif",
  "niat_beli:neutral": "Niat beli — netral",
  "niat_beli:negative": "Niat beli — negatif",
  "niat_beli:unknown": "Niat beli",
  "spam_only": "Spam",
  "no_interactions": "Belum ada interaksi",
  "single_interaction": "Interaksi tunggal",
  "decayed:hot_to_warm": "Tidak aktif",
  "decayed:warm_to_cold": "Tidak aktif",
};

function formatReason(raw: string | null) {
  if (!raw) return "—";
  if (raw.startsWith("tanya_info:")) {
    const count = raw.split(":")[1];
    return `Tanya info ${count}`;
  }
  return REASON_LABEL[raw] ?? raw;
}

function relativeTime(iso: string | null) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}d lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
  return `${Math.floor(diff / 86400)}h lalu`;
}

const TIER_TABS = [
  { key: "all", label: "Semua" },
  { key: "hot", label: "Panas" },
  { key: "warm", label: "Hangat" },
  { key: "cold", label: "Dingin" },
] as const;

const STATUS_TABS = [
  { key: "active", label: "Aktif" },
  { key: "archived", label: "Diarsip" },
  { key: "resolved", label: "Selesai" },
] as const;

export default function Leads() {
  const { logout } = useAuth();
  const {
    leads,
    loading,
    tierFilter,
    setTierFilter,
    statusFilter,
    setStatusFilter,
    handleArchive,
    handleResolve,
  } = useLeads();

  const hotCount = leads.filter((l) => l.tier === "hot").length;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-900">
            Reseller AI — Leads
          </span>
          {hotCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse inline-block" />
              {hotCount} prospek panas
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <a
            href="/inbox"
            className="text-xs text-slate-500 hover:text-slate-900 transition-colors"
          >
            Inbox
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
        {/* Filters */}
        <div className="mb-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            {/* Tier filter */}
            <div className="flex gap-1.5">
              {TIER_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTierFilter(t.key)}
                  className={[
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    tierFilter === t.key
                      ? "bg-slate-900 text-white shadow-sm"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
                  ].join(" ")}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Status filter */}
            <div className="flex gap-1.5 border-l border-slate-200 pl-4">
              {STATUS_TABS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStatusFilter(s.key)}
                  className={[
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    statusFilter === s.key
                      ? "bg-slate-100 text-slate-900 border border-slate-300"
                      : "text-slate-500 hover:text-slate-900",
                  ].join(" ")}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <span className="text-xs text-slate-400">
            {loading ? "Memuat..." : `${leads.length} leads`}
          </span>
        </div>

        {/* Table */}
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 border-slate-200">
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Tier
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Alasan
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide text-center">
                  Interaksi
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Terakhir aktif
                </TableHead>
                <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Masuk
                </TableHead>
                {statusFilter === "active" && (
                  <TableHead className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                    Aksi
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {!loading && leads.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="py-16 text-center text-sm text-slate-400"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <span className="text-2xl">📋</span>
                      <span>Belum ada lead di kategori ini.</span>
                    </div>
                  </TableCell>
                </TableRow>
              )}
              {leads.map((lead) => {
                const tier = TIER_CONFIG[lead.tier];
                return (
                  <TableRow
                    key={lead.id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                  >
                    <TableCell>
                      <span className="flex items-center gap-2">
                        <span
                          className={`h-2 w-2 rounded-full flex-shrink-0 ${tier.dot}`}
                        />
                        <Badge className={`text-xs font-medium ${tier.className}`}>
                          {tier.label}
                        </Badge>
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-slate-600">
                      {formatReason(lead.tier_reason)}
                    </TableCell>
                    <TableCell className="text-center">
                      <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-slate-100 px-2 text-xs font-semibold text-slate-700">
                        {lead.interaction_count}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                      {relativeTime(lead.last_interaction)}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 whitespace-nowrap">
                      {relativeTime(lead.created_at)}
                    </TableCell>
                    {statusFilter === "active" && (
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleResolve(lead.id)}
                            className="rounded-md px-2.5 py-1 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors"
                          >
                            Selesai
                          </button>
                          <button
                            onClick={() => handleArchive(lead.id)}
                            className="rounded-md px-2.5 py-1 text-xs font-medium bg-slate-50 text-slate-500 border border-slate-200 hover:bg-slate-100 transition-colors"
                          >
                            Arsip
                          </button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </main>
    </div>
  );
}
