import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

const USE_DEMO_DATA = import.meta.env.VITE_USE_DEMO_DATA === "true";

export interface LeadResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string | null;
  customer_platform: string | null;
  tier: "hot" | "warm" | "cold";
  tier_reason: string | null;
  interaction_count: number;
  last_interaction: string | null;
  status: "active" | "archived" | "resolved";
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

function minutesAgo(m: number): string {
  return new Date(Date.now() - m * 60_000).toISOString();
}

const DUMMY_LEADS: LeadResponse[] = [
  {
    id: "lead-001",
    tenant_id: "tenant-1",
    customer_id: "cust-001",
    customer_name: "Rina Wijaya",
    customer_platform: "facebook",
    tier: "hot",
    tier_reason: "niat_beli:positive",
    interaction_count: 8,
    last_interaction: minutesAgo(5),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(1440),
    updated_at: minutesAgo(5),
  },
  {
    id: "lead-002",
    tenant_id: "tenant-1",
    customer_id: "cust-004",
    customer_name: "Ahmad Fauzi",
    customer_platform: "facebook",
    tier: "hot",
    tier_reason: "niat_beli:neutral",
    interaction_count: 4,
    last_interaction: minutesAgo(180),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(2880),
    updated_at: minutesAgo(180),
  },
  {
    id: "lead-003",
    tenant_id: "tenant-1",
    customer_id: "cust-002",
    customer_name: "Budi Santoso",
    customer_platform: "instagram",
    tier: "hot",
    tier_reason: "komplain:negative",
    interaction_count: 6,
    last_interaction: minutesAgo(2),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(720),
    updated_at: minutesAgo(2),
  },
  {
    id: "lead-004",
    tenant_id: "tenant-1",
    customer_id: "cust-003",
    customer_name: "Sari Dewi",
    customer_platform: "whatsapp",
    tier: "warm",
    tier_reason: "tanya_info:2",
    interaction_count: 3,
    last_interaction: minutesAgo(60),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(4320),
    updated_at: minutesAgo(60),
  },
  {
    id: "lead-005",
    tenant_id: "tenant-1",
    customer_id: "cust-005",
    customer_name: "Maya Putri",
    customer_platform: "messenger",
    tier: "warm",
    tier_reason: "komplain:neutral",
    interaction_count: 2,
    last_interaction: minutesAgo(20),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(180),
    updated_at: minutesAgo(20),
  },
  {
    id: "lead-006",
    tenant_id: "tenant-1",
    customer_id: "cust-006",
    customer_name: "Dimas Prakoso",
    customer_platform: "facebook",
    tier: "cold",
    tier_reason: "single_interaction",
    interaction_count: 1,
    last_interaction: minutesAgo(600),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(600),
    updated_at: minutesAgo(600),
  },
  {
    id: "lead-007",
    tenant_id: "tenant-1",
    customer_id: "cust-007",
    customer_name: "Lestari Nugroho",
    customer_platform: "instagram",
    tier: "cold",
    tier_reason: "decayed:warm_to_cold",
    interaction_count: 3,
    last_interaction: minutesAgo(3000),
    status: "active",
    resolved_at: null,
    created_at: minutesAgo(7200),
    updated_at: minutesAgo(3000),
  },
  {
    id: "lead-008",
    tenant_id: "tenant-1",
    customer_id: "cust-004",
    customer_name: "Ahmad Fauzi",
    customer_platform: "facebook",
    tier: "warm",
    tier_reason: "niat_beli:neutral",
    interaction_count: 4,
    last_interaction: minutesAgo(4320),
    status: "resolved",
    resolved_at: minutesAgo(4320),
    created_at: minutesAgo(10080),
    updated_at: minutesAgo(4320),
  },
];

type TierFilter = "all" | "hot" | "warm" | "cold";
type StatusFilter = "active" | "archived" | "resolved";

export function useLeads() {
  const [leads, setLeads] = useState<LeadResponse[]>([]);
  const [tierFilter, setTierFilter] = useState<TierFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [loading, setLoading] = useState(true);

  const fetchLeads = useCallback(() => {
    if (USE_DEMO_DATA) {
      setLeads(DUMMY_LEADS.filter((l) => {
        if (tierFilter !== "all" && l.tier !== tierFilter) return false;
        if (l.status !== statusFilter) return false;
        return true;
      }));
      setLoading(false);
      return;
    }

    const params: Record<string, string> = {};
    if (tierFilter !== "all") params.tier = tierFilter;
    params.status = statusFilter;

    api
      .get<{ data: LeadResponse[] }>("/leads", { params })
      .then((res) => {
        if (res.data.data && res.data.data.length > 0) {
          setLeads(res.data.data);
        } else {
          setLeads([]);
        }
      })
      .catch(() => {
        setLeads([]);
      })
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
