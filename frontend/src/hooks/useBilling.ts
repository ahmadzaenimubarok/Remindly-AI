import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface BillingStatus {
  plan: string;
  plan_expires_at: string | null;
  stripe_customer_id: string | null;
  pending_plan: string | null;
  pending_plan_date: string | null;
}

const PLAN_LABELS: Record<string, string> = {
  free: "Gratis",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",
};

export function useBilling() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: BillingStatus }>("/billing/status");
      setStatus(res.data.data);
    } catch {
      setError("Gagal memuat info billing.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  async function startCheckout(plan: string): Promise<void> {
    setRedirecting(true);
    try {
      const origin = window.location.origin;
      const res = await api.post<{ data: { checkout_url: string; modified: boolean } }>("/billing/checkout", {
        plan,
        success_url: `${origin}/billing?success=1`,
        cancel_url: `${origin}/billing?cancel=1`,
      });
      if (res.data.data.modified) {
        // Plan langsung diubah tanpa redirect Stripe
        await fetchStatus();
        setRedirecting(false);
      } else {
        window.location.href = res.data.data.checkout_url;
      }
    } catch {
      setError("Gagal mengubah plan. Coba lagi.");
      setRedirecting(false);
    }
  }

  return { status, isLoading, error, redirecting, startCheckout, planLabel: PLAN_LABELS };
}
