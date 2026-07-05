import { useLeads, type LeadResponse } from "@/hooks/useLeads";
import AppLayout from "@/components/AppLayout";

const TIER_CONFIG = {
  hot: {
    label: "Panas",
    desc: "Sinyal niat beli kuat — prioritaskan follow-up",
    badge: "bg-red-100 text-red-700 border border-red-200",
    bar: "bg-red-500",
    dot: "bg-red-500",
    glow: "border-red-200",
    avatar: "bg-red-100 text-red-700",
  },
  warm: {
    label: "Hangat",
    desc: "Tertarik tapi belum memutuskan — pantau terus",
    badge: "bg-amber-100 text-amber-700 border border-amber-200",
    bar: "bg-amber-400",
    dot: "bg-amber-500",
    glow: "border-amber-200",
    avatar: "bg-amber-100 text-amber-700",
  },
  cold: {
    label: "Dingin",
    desc: "Belum ada sinyal minat — biarkan AI tangani",
    badge: "bg-slate-100 text-slate-600 border border-slate-200",
    bar: "bg-slate-300",
    dot: "bg-slate-400",
    glow: "border-slate-200",
    avatar: "bg-slate-100 text-slate-600",
  },
} as const;

const REASON_LABEL: Record<string, string> = {
  "niat_beli:positive": "Menyatakan niat beli dengan positif",
  "niat_beli:neutral": "Menyatakan niat beli",
  "niat_beli:negative": "Menyatakan niat beli, tapi ragu",
  "niat_beli:unknown": "Menyatakan niat beli",
  spam_only: "Hanya mengirim spam",
  no_interactions: "Belum ada interaksi",
  single_interaction: "Baru 1 kali interaksi",
  "decayed:hot_to_warm": "Tidak aktif lebih dari 1 hari",
  "decayed:warm_to_cold": "Tidak aktif lebih dari 2 hari",
};

const PLATFORM_LABEL: Record<string, string> = {
  facebook: "Facebook",
  messenger: "Messenger",
  instagram: "Instagram",
  whatsapp: "WhatsApp",
};

function formatReason(raw: string | null) {
  if (!raw) return "—";
  if (raw.startsWith("tanya_info:")) {
    const count = raw.split(":")[1];
    return `Bertanya ${count}x tentang produk`;
  }
  return REASON_LABEL[raw] ?? raw;
}

function relativeTime(iso: string | null) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}d lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  return `${Math.floor(diff / 86400)} hari lalu`;
}

function TierBar({ tier }: { tier: "hot" | "warm" | "cold" }) {
  const fill = tier === "hot" ? 100 : tier === "warm" ? 55 : 20;
  const cfg = TIER_CONFIG[tier];
  return (
    <div className="h-1 w-full rounded-full bg-slate-100 overflow-hidden" role="presentation">
      <div
        className={`h-full rounded-full ${cfg.bar} transition-all`}
        style={{ width: `${fill}%` }}
      />
    </div>
  );
}

function LeadCard({
  lead,
  onResolve,
  onArchive,
  showActions,
}: {
  lead: LeadResponse;
  onResolve: (id: string) => void;
  onArchive: (id: string) => void;
  showActions: boolean;
}) {
  const tier = TIER_CONFIG[lead.tier];
  const name = lead.customer_name ?? "Tanpa nama";
  const platform =
    PLATFORM_LABEL[lead.customer_platform ?? ""] ?? lead.customer_platform ?? "—";

  return (
    <article
      className={`rounded-lg border bg-white p-4 sm:p-5 shadow-sm flex flex-col gap-3.5 ${tier.glow}`}
      aria-label={`${name} — ${tier.label}`}
    >
      {/* Header: avatar + name + tier badge */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${tier.avatar}`}
            aria-hidden="true"
          >
            {name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
            <p className="text-xs text-slate-400">{platform}</p>
          </div>
        </div>
        <span
          className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-semibold border ${tier.badge}`}
        >
          {tier.label}
        </span>
      </div>

      {/* Heat bar */}
      <TierBar tier={lead.tier} />

      {/* Signal */}
      <div className="rounded-md bg-slate-50 px-3 py-2.5">
        <p className="text-[11px] font-medium text-slate-400 mb-0.5">Sinyal</p>
        <p className="text-sm text-slate-700">{formatReason(lead.tier_reason)}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md bg-slate-50 px-3 py-2">
          <p className="text-[11px] text-slate-400 mb-0.5">Interaksi</p>
          <p className="text-base font-bold text-slate-900">{lead.interaction_count}</p>
          <p className="text-[11px] text-slate-400">total pesan</p>
        </div>
        <div className="rounded-md bg-slate-50 px-3 py-2">
          <p className="text-[11px] text-slate-400 mb-0.5">Terakhir aktif</p>
          <p className="text-sm font-semibold text-slate-900 leading-snug">
            {relativeTime(lead.last_interaction)}
          </p>
          <p className="text-[11px] text-slate-400">
            masuk {relativeTime(lead.created_at)}
          </p>
        </div>
      </div>

      {/* Actions — min 44px touch target */}
      {showActions && (
        <div className="flex gap-2 pt-1 border-t border-slate-100">
          <button
            onClick={() => onResolve(lead.id)}
            className="flex-1 min-h-[44px] rounded-md px-3 py-2.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 active:bg-emerald-200 transition-colors"
            aria-label={`Tandai ${name} selesai`}
          >
            Tandai Selesai
          </button>
          <button
            onClick={() => onArchive(lead.id)}
            className="min-h-[44px] rounded-md px-3 py-2.5 text-xs font-semibold bg-white text-slate-500 border border-slate-200 hover:bg-slate-50 active:bg-slate-100 transition-colors"
            aria-label={`Arsipkan ${name}`}
          >
            Arsip
          </button>
        </div>
      )}
    </article>
  );
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

  const hotCount = leads.filter((l) => l.tier === "hot" && l.status === "active").length;
  const warmCount = leads.filter((l) => l.tier === "warm" && l.status === "active").length;

  return (
    <AppLayout>
      <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6">
        {/* Summary bar — stacks on mobile */}
        {statusFilter === "active" && (hotCount > 0 || warmCount > 0) && (
          <div className="mb-6 flex flex-col sm:flex-row gap-3">
            {hotCount > 0 && (
              <div className="flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                <span
                  aria-hidden="true"
                  className="h-2 w-2 shrink-0 rounded-full bg-red-500 [animation:pulse_2s_cubic-bezier(0.4,0,0.6,1)_infinite] motion-reduce:animate-none"
                />
                <div>
                  <p className="text-sm font-semibold text-red-700">{hotCount} prospek panas</p>
                  <p className="text-xs text-red-500">Perlu follow-up segera</p>
                </div>
              </div>
            )}
            {warmCount > 0 && (
              <div className="flex items-center gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                <span
                  aria-hidden="true"
                  className="h-2 w-2 shrink-0 rounded-full bg-amber-500"
                />
                <div>
                  <p className="text-sm font-semibold text-amber-700">{warmCount} prospek hangat</p>
                  <p className="text-xs text-amber-600">Sedang tertarik, pantau terus</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Filters — stacks on mobile, side-by-side on sm+ */}
        <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
            {/* Tier filter */}
            <div
              className="flex gap-1.5 flex-wrap"
              role="group"
              aria-label="Filter tier lead"
            >
              {TIER_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTierFilter(t.key)}
                  aria-pressed={tierFilter === t.key}
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

            {/* Status filter — separator adapts between horizontal line (mobile) and vertical divider (desktop) */}
            <div
              className="flex gap-1.5 flex-wrap pt-1.5 border-t border-slate-200 sm:pt-0 sm:border-t-0 sm:border-l sm:border-slate-200 sm:pl-4"
              role="group"
              aria-label="Filter status lead"
            >
              {STATUS_TABS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setStatusFilter(s.key)}
                  aria-pressed={statusFilter === s.key}
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

          <span className="text-xs text-slate-400" aria-live="polite">
            {loading ? "Memuat…" : `${leads.length} leads`}
          </span>
        </div>

        {/* Tier description */}
        {tierFilter !== "all" && (
          <p className="mb-4 text-xs text-slate-400">
            {TIER_CONFIG[tierFilter as keyof typeof TIER_CONFIG]?.desc}
          </p>
        )}

        {/* Grid */}
        {loading ? (
          <div
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
            aria-busy="true"
            aria-label="Memuat leads…"
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 h-56 animate-pulse"
                aria-hidden="true"
              />
            ))}
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-20 text-sm text-slate-400">
            <span aria-hidden="true" className="text-3xl">📋</span>
            <span>Belum ada lead di kategori ini.</span>
          </div>
        ) : (
          <div
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
            role="list"
            aria-label="Daftar leads"
          >
            {leads.map((lead) => (
              <LeadCard
                key={lead.id}
                lead={lead}
                onResolve={handleResolve}
                onArchive={handleArchive}
                showActions={statusFilter === "active"}
              />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
