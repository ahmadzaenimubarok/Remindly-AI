import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface LeadResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  tier: "hot" | "warm" | "cold";
  tier_reason: string | null;
  interaction_count: number;
  last_interaction: string | null;
  status: "active" | "archived" | "resolved";
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

type TierFilter = "all" | "hot" | "warm" | "cold";
type StatusFilter = "active" | "archived" | "resolved";

export function useLeads() {
  const [leads, setLeads] = useState<LeadResponse[]>([]);
  const [tierFilter, setTierFilter] = useState<TierFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [loading, setLoading] = useState(true);

  const fetchLeads = useCallback(() => {
    const params: Record<string, string> = {};
    if (tierFilter !== "all") params.tier = tierFilter;
    params.status = statusFilter;

    api
      .get<{ data: LeadResponse[] }>("/leads", { params })
      .then((res) => setLeads(res.data.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tierFilter, statusFilter]);

  useEffect(() => {
    setLoading(true);
    fetchLeads();
    const timer = setInterval(fetchLeads, 15_000);
    return () => clearInterval(timer);
  }, [fetchLeads]);

  async function handleArchive(id: string) {
    try {
      await api.patch(`/leads/${id}/archive`);
      setLeads((prev) => prev.filter((l) => l.id !== id));
    } catch {}
  }

  async function handleResolve(id: string) {
    try {
      await api.patch(`/leads/${id}/resolve`);
      setLeads((prev) => prev.filter((l) => l.id !== id));
    } catch {}
  }

  return {
    leads,
    loading,
    tierFilter,
    setTierFilter,
    statusFilter,
    setStatusFilter,
    handleArchive,
    handleResolve,
  };
}
