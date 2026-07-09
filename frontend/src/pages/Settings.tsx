import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/hooks/useSettings";
import AppLayout from "@/components/AppLayout";

export default function Settings() {
  const navigate = useNavigate();
  const { status, isLoading, saveIGToken } = useSettings();

  const [igPageToken, setIgPageToken] = useState("");
  const [igAccountId, setIgAccountId] = useState("");
  const [igSaving, setIgSaving] = useState(false);
  const [igSaveError, setIgSaveError] = useState<string | null>(null);
  const [igSaveSuccess, setIgSaveSuccess] = useState(false);

  async function handleIGSave(e: React.FormEvent) {
    e.preventDefault();
    if (!igPageToken.trim() || !igAccountId.trim()) {
      setIgSaveError("Page Access Token dan Instagram Account ID wajib diisi.");
      return;
    }
    setIgSaving(true);
    setIgSaveError(null);
    setIgSaveSuccess(false);
    try {
      await saveIGToken(igPageToken.trim(), igAccountId.trim());
      setIgPageToken("");
      setIgAccountId("");
      setIgSaveSuccess(true);
    } catch {
      setIgSaveError("Gagal menyimpan token. Pastikan token valid.");
    } finally {
      setIgSaving(false);
    }
  }

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
            Masukkan Page Access Token dan Instagram Account ID untuk mengaktifkan auto-reply DM
            Instagram. Generate token di{" "}
            <a
              href="https://developers.facebook.com/tools/explorer/?method=GET&path=me%2Faccounts&version=v21.0"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline"
            >
              Graph API Explorer
            </a>{" "}
            dengan permission{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">instagram_basic</code> dan{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">instagram_manage_messages</code>.
          </p>

          <form onSubmit={handleIGSave} className="space-y-3">
            <div>
              <Label htmlFor="igAccountId">Instagram Account ID</Label>
              <Input
                id="igAccountId"
                value={igAccountId}
                onChange={(e) => setIgAccountId(e.target.value)}
                placeholder="17841400000000000"
              />
            </div>
            <div>
              <Label htmlFor="igPageToken">Page Access Token</Label>
              <Input
                id="igPageToken"
                type="password"
                value={igPageToken}
                onChange={(e) => setIgPageToken(e.target.value)}
                placeholder="EAAxxxx..."
              />
            </div>
            {igSaveError && <p className="text-sm text-red-600">{igSaveError}</p>}
            {igSaveSuccess && (
              <p className="text-sm text-green-600">Token berhasil disimpan. AI aktif.</p>
            )}
            <Button type="submit" disabled={igSaving} size="sm">
              {igSaving ? "Menyimpan..." : "Simpan Token"}
            </Button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}
