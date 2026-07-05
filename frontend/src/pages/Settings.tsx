import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/hooks/useSettings";
import AppLayout from "@/components/AppLayout";

export default function Settings() {
  const { status, isLoading, saveFBToken } = useSettings();
  const [pageToken, setPageToken] = useState("");
  const [pageId, setPageId] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!pageToken.trim() || !pageId.trim()) {
      setSaveError("Page Token dan Page ID wajib diisi.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await saveFBToken(pageToken.trim(), pageId.trim());
      setPageToken("");
      setPageId("");
      setSaveSuccess(true);
    } catch {
      setSaveError("Gagal menyimpan token. Pastikan token valid.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl p-6">
        <h1 className="mb-6 text-xl font-semibold text-slate-900">Pengaturan</h1>

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
            Masukkan Facebook Page Access Token untuk mengaktifkan auto-reply komentar dan Messenger
            DM. Generate token di{" "}
            <a
              href="https://developers.facebook.com/tools/explorer"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline"
            >
              Graph API Explorer
            </a>{" "}
            dengan permission{" "}
            <code className="rounded bg-slate-100 px-1 text-xs">pages_manage_engagement</code>.
          </p>

          <form onSubmit={handleSave} className="space-y-3">
            <div>
              <Label htmlFor="pageId">Page ID</Label>
              <Input
                id="pageId"
                value={pageId}
                onChange={(e) => setPageId(e.target.value)}
                placeholder="1234567890"
              />
            </div>
            <div>
              <Label htmlFor="pageToken">Page Access Token</Label>
              <Input
                id="pageToken"
                type="password"
                value={pageToken}
                onChange={(e) => setPageToken(e.target.value)}
                placeholder="EAAxxxx..."
              />
            </div>
            {saveError && <p className="text-sm text-red-600">{saveError}</p>}
            {saveSuccess && (
              <p className="text-sm text-green-600">Token berhasil disimpan. AI aktif.</p>
            )}
            <Button type="submit" disabled={saving} size="sm">
              {saving ? "Menyimpan..." : "Simpan Token"}
            </Button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}
