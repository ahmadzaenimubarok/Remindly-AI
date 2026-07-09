import { useEffect, useState } from "react";
import { useFacebookOAuth } from "@/hooks/useFacebookOAuth";
import AppLayout from "@/components/AppLayout";
import { Button } from "@/components/ui/button";

export default function FacebookPages() {
  const { getLoginUrl, loading, error } = useFacebookOAuth();
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
        <h1 className="mb-4 text-xl font-semibold text-slate-900">Hubungkan Facebook</h1>
        <p className="mb-6 text-sm text-slate-500">
          Klik tombol di bawah untuk menghubungkan Facebook Page Anda.
        </p>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Facebook Page</h2>
          <p className="mb-4 text-sm text-slate-500">
            Anda akan diarahkan ke Facebook untuk memberikan izin akses. Setelah itu, Anda dapat
            memilih Page yang ingin dihubungkan.
          </p>

          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

          <Button onClick={handleConnect} disabled={loading || !loginUrl}>
            {loading ? "Memuat..." : "Connect Facebook"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
