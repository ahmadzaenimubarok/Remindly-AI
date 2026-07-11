import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useSettings } from "@/hooks/useSettings";
import AppLayout from "@/components/AppLayout";

export default function Settings() {
  const navigate = useNavigate();
  const { status, isLoading } = useSettings();

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl p-6">
        <h1 className="mb-6 text-xl font-semibold text-slate-900">Pengaturan</h1>

        {/* Facebook Card */}
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium text-slate-800">Facebook Page</h2>
            {!isLoading && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  status?.facebook_connected
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {status?.facebook_connected ? "Terhubung" : "Belum terhubung"}
              </span>
            )}
          </div>

          <p className="mb-4 text-sm text-slate-500">
            Hubungkan Facebook Page Anda untuk mengaktifkan auto-reply komentar dan Messenger DM.
          </p>

          {status?.facebook_connected ? (
            <div className="space-y-3">
              <p className="text-sm text-green-600">✓ Facebook Page terhubung</p>
              <Button variant="outline" size="sm" onClick={() => navigate("/auth/facebook/pages")}>
                Hubungkan Page Lain
              </Button>
            </div>
          ) : (
            <Button onClick={() => navigate("/auth/facebook/pages")} size="sm">
              Connect Facebook
            </Button>
          )}
        </div>

        {/* Instagram Card */}
        <div className="mt-4 rounded-lg border bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium text-slate-800">Instagram Business</h2>
            {!isLoading && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  status?.instagram_connected
                    ? "bg-green-100 text-green-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {status?.instagram_connected ? "Terhubung" : "Belum terhubung"}
              </span>
            )}
          </div>

          <p className="mb-4 text-sm text-slate-500">
            Hubungkan akun Instagram Business Anda untuk mengaktifkan auto-reply DM Instagram.
          </p>

          {status?.instagram_connected ? (
            <div className="space-y-3">
              <p className="text-sm text-green-600">✓ Instagram terhubung</p>
              <Button variant="outline" size="sm" onClick={() => navigate("/auth/instagram/connect")}>
                Hubungkan Akun Lain
              </Button>
            </div>
          ) : (
            <Button onClick={() => navigate("/auth/instagram/connect")} size="sm">
              Connect Instagram
            </Button>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
