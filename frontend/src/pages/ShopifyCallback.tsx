import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";

interface CallbackData {
  state: string;
  shop_domain: string;
  shop_name: string;
  access_token: string;
}

export default function ShopifyCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dataParam = searchParams.get("data");
    const errorParam = searchParams.get("error");

    if (errorParam) {
      setStatus("error");
      setError(`Gagal menghubungkan Shopify: ${errorParam}`);
      return;
    }

    if (!dataParam) {
      setStatus("error");
      setError("Data callback tidak ditemukan.");
      return;
    }

    try {
      const decoded = JSON.parse(atob(dataParam)) as CallbackData;
      
      // Simpan koneksi ke backend
      api.post("/auth/shopify/connect", {
        shop_domain: decoded.shop_domain,
        access_token: decoded.access_token,
        shop_name: decoded.shop_name,
      }).then(() => {
        setStatus("success");
        setTimeout(() => navigate("/settings"), 2000);
      }).catch((err) => {
        setStatus("error");
        setError(err.response?.data?.detail || "Gagal menyimpan koneksi Shopify.");
      });
    } catch {
      setStatus("error");
      setError("Gagal memproses data callback.");
    }
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="rounded-lg border bg-white p-6 shadow-sm text-center">
          {status === "loading" && (
            <>
              <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
              <p className="text-sm text-slate-600">Menghubungkan Shopify...</p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <span className="text-2xl">✓</span>
              </div>
              <h1 className="text-lg font-semibold text-slate-900">Berhasil!</h1>
              <p className="mt-2 text-sm text-slate-500">
                Shopify store berhasil dihubungkan. Mengalihkan ke pengaturan...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <span className="text-2xl">✕</span>
              </div>
              <h1 className="text-lg font-semibold text-slate-900">Gagal</h1>
              <p className="mt-2 text-sm text-red-600">{error}</p>
              <Button
                onClick={() => navigate("/settings")}
                className="mt-4"
                variant="outline"
              >
                Kembali ke Pengaturan
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
