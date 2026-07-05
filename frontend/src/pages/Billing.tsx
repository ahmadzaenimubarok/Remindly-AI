import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useBilling } from "@/hooks/useBilling";
import AppLayout from "@/components/AppLayout";

const PLANS = [
  {
    key: "free",
    label: "Gratis",
    price: "Rp 0 / bulan",
    features: ["Instagram reply", "Manajemen produk", "Inbox & leads"],
  },
  {
    key: "starter",
    label: "Starter",
    price: "Rp 99.000 / bulan",
    features: ["Instagram & TikTok reply", "Content publish", "Product discovery"],
  },
  {
    key: "pro",
    label: "Pro",
    price: "Rp 299.000 / bulan",
    features: [
      "Semua fitur Starter",
      "Facebook & WhatsApp reply",
      "Lead classification",
      "Analytics",
    ],
  },
  {
    key: "enterprise",
    label: "Enterprise",
    price: "Hubungi kami",
    features: ["Semua fitur Pro", "Unlimited channels", "Dedicated support", "Custom SLA"],
  },
] as const;

function formatExpiry(iso: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function Billing() {
  const { status, isLoading, error, redirecting, startCheckout, planLabel } = useBilling();
  const [searchParams] = useSearchParams();
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get("success") === "1") {
      setNotice("Pembayaran berhasil! Plan akan aktif dalam beberapa menit.");
    } else if (searchParams.get("cancel") === "1") {
      setNotice("Checkout dibatalkan. Plan tidak berubah.");
    }
  }, [searchParams]);

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl p-6">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">Billing & Plan</h1>
        <p className="mb-6 text-sm text-slate-500">Pilih plan yang sesuai kebutuhan bisnis kamu.</p>

        {notice && (
          <div className="mb-6 rounded-lg border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800">
            {notice}
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Current plan */}
        {!isLoading && status && (
          <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-400 mb-1">Plan aktif</p>
            <div className="flex items-center gap-3">
              <span className="text-lg font-semibold text-slate-900">
                {planLabel[status.plan] ?? status.plan}
              </span>
              {status.plan !== "free" && status.plan_expires_at && (
                <span className="text-xs text-slate-500">
                  aktif hingga {formatExpiry(status.plan_expires_at)}
                </span>
              )}
              {status.plan === "free" && (
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                  Gratis
                </span>
              )}
            </div>
          </div>
        )}

        {isLoading && (
          <div className="mb-6 h-16 rounded-lg border border-slate-200 bg-white animate-pulse" />
        )}

        {/* Plan cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => {
            const isCurrent = status?.plan === plan.key;
            const isFree = plan.key === "free";
            const isEnterprise = plan.key === "enterprise";
            const canCheckout = !isCurrent && !isFree && !isEnterprise;
            return (
              <div
                key={plan.key}
                className={[
                  "flex flex-col rounded-lg border bg-white p-5 shadow-sm",
                  isCurrent ? "border-[#0d7a8a] ring-1 ring-[#0d7a8a]/30" : "border-slate-200",
                ].join(" ")}
              >
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="font-semibold text-slate-900">{plan.label}</h2>
                  {isCurrent && (
                    <span className="rounded-md bg-[#0d7a8a]/10 px-2 py-0.5 text-xs font-medium text-[#0d7a8a]">
                      Aktif
                    </span>
                  )}
                </div>
                <p className="mb-4 text-sm font-medium text-slate-700">{plan.price}</p>
                <ul className="mb-6 flex-1 space-y-1.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                      <span className="mt-0.5 text-[#0d7a8a]" aria-hidden="true">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  disabled={isCurrent || redirecting || isFree || isEnterprise}
                  onClick={() => canCheckout && startCheckout(plan.key)}
                  className={
                    isCurrent || isFree
                      ? "bg-slate-100 text-slate-400 cursor-default"
                      : "bg-[#0d7a8a] hover:bg-[#0b6b7a] text-white"
                  }
                >
                  {isEnterprise
                    ? "Hubungi Kami"
                    : isCurrent
                    ? "Plan Aktif"
                    : isFree
                    ? "Plan Saat Ini"
                    : redirecting
                    ? "Mengalihkan..."
                    : "Pilih Plan"}
                </Button>
              </div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}
