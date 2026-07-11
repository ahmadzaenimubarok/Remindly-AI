import { useCallback, useState } from "react";
import api from "@/lib/api";

export interface InstagramAccount {
  page_id: string;
  page_name: string;
  page_token: string;
  instagram_account_id: string;
  instagram_username: string;
  instagram_name: string;
}

export interface InstagramOAuthData {
  accounts: InstagramAccount[];
}

export function useInstagramOAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLoginUrl = useCallback(async (): Promise<string | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<{ url: string }>("/auth/instagram/login");
      return res.data.url;
    } catch {
      setError("Gagal mendapatkan URL login Instagram.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const connectAccount = useCallback(
    async (
      pageId: string,
      pageName: string,
      pageToken: string,
      instagramAccountId: string,
      instagramUsername: string
    ): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await api.post("/auth/instagram/connect", {
          page_id: pageId,
          page_name: pageName,
          page_token: pageToken,
          instagram_account_id: instagramAccountId,
          instagram_username: instagramUsername,
        });
        return true;
      } catch {
        setError("Gagal menghubungkan Instagram.");
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const disconnect = useCallback(async (): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await api.delete("/auth/instagram/disconnect");
      return true;
    } catch {
      setError("Gagal memutus koneksi Instagram.");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, getLoginUrl, connectAccount, disconnect };
}
