import { useCallback, useState } from "react";
import api from "@/lib/api";

export interface FacebookPage {
  page_id: string;
  page_name: string;
  access_token: string;
}

export interface FacebookOAuthData {
  facebook_user_id: string | null;
  long_lived_token: string;
  pages: FacebookPage[];
}

export function useFacebookOAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLoginUrl = useCallback(async (): Promise<string | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<{ url: string }>("/auth/facebook/login");
      return res.data.url;
    } catch {
      setError("Gagal mendapatkan URL login Facebook.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const exchangeCode = useCallback(
    async (code: string): Promise<FacebookOAuthData | null> => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.post<FacebookOAuthData>("/auth/facebook/callback", {
          code,
        });
        return res.data;
      } catch {
        setError("Gagal menukar authorization code.");
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const connectPage = useCallback(
    async (pageId: string, pageName: string, accessToken: string): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await api.post("/auth/facebook/connect", {
          page_id: pageId,
          page_name: pageName,
          access_token: accessToken,
        });
        return true;
      } catch {
        setError("Gagal menghubungkan Facebook Page.");
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
      await api.delete("/auth/facebook/disconnect");
      return true;
    } catch {
      setError("Gagal memutus koneksi Facebook.");
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, getLoginUrl, exchangeCode, connectPage, disconnect };
}
