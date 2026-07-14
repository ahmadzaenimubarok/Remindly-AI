import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface SettingsStatus {
  facebook_connected: boolean;
  instagram_connected: boolean;
  shopify_connected: boolean;
  product_count: number;
}

export function useSettings() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: SettingsStatus }>("/settings");
      setStatus(res.data.data);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  async function saveFBToken(pageToken: string, pageId: string): Promise<void> {
    await api.post("/settings/facebook-token", { page_token: pageToken, page_id: pageId });
    await fetchStatus();
  }

  async function saveIGToken(pageToken: string, accountId: string): Promise<void> {
    await api.post("/settings/instagram-token", { page_token: pageToken, instagram_account_id: accountId });
    await fetchStatus();
  }

  return { status, isLoading, saveFBToken, saveIGToken };
}
