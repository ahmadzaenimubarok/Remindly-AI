import { useEffect, useState } from "react";
import { useInstagramOAuth } from "@/hooks/useInstagramOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function InstagramConnect() {
  const { getLoginUrl, loading, error } = useInstagramOAuth();
  const [loginUrl, setLoginUrl] = useState<string | null>(null);

  useEffect(() => {
    getLoginUrl().then((url) => setLoginUrl(url));
  }, [getLoginUrl]);

  function handleConnect() {
    if (loginUrl) {
      window.location.href = loginUrl;
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl p-6">
        <h1 className="mb-4 text-xl font-semibold text-slate-900">Hubungkan Instagram</h1>
        <p className="mb-6 text-sm text-slate-500">
          Klik tombol di bawah untuk menghubungkan akun Instagram Business Anda.
        </p>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Instagram Business</h2>
          <p className="mb-4 text-sm text-slate-500">
            Anda akan diarahkan ke Meta untuk memberikan izin akses. Pastikan akun Instagram Anda
            adalah Business Account yang sudah terhubung ke Facebook Page.
          </p>

          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <Button onClick={handleConnect} disabled={loading || !loginUrl}>
            {loading ? "Memuat..." : "Connect Instagram"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
