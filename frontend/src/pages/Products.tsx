import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useProducts, type CreateProductPayload } from "@/hooks/useProducts";
import AppLayout from "@/components/AppLayout";

function formatPrice(price: string | null) {
  if (!price) return "—";
  return `Rp ${parseInt(price).toLocaleString("id-ID")}`;
}

export default function Products() {
  const { products, isLoading, error, addProduct, deleteProduct } = useProducts();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateProductPayload>({ name: "" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setFormError("Nama produk wajib diisi.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await addProduct(form);
      setForm({ name: "" });
      setShowForm(false);
    } catch {
      setFormError("Gagal menambahkan produk. Coba lagi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-900">Produk</h1>
          <Button onClick={() => setShowForm((v) => !v)} size="sm">
            {showForm ? "Batal" : "+ Tambah Produk"}
          </Button>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="mb-6 rounded-lg border bg-white p-4 shadow-sm space-y-3"
          >
            <div>
              <Label htmlFor="name">Nama Produk *</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Sepatu Lari Pro"
              />
            </div>
            <div>
              <Label htmlFor="desc">Deskripsi</Label>
              <Input
                id="desc"
                value={form.description ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Cocok untuk lari marathon..."
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <Label htmlFor="price">Harga (Rp)</Label>
                <Input
                  id="price"
                  type="number"
                  min={0}
                  value={form.base_price ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      base_price: e.target.value ? Number(e.target.value) : undefined,
                    }))
                  }
                  placeholder="150000"
                />
              </div>
              <div className="flex-1">
                <Label htmlFor="link">Link Affiliate</Label>
                <Input
                  id="link"
                  value={form.affiliate_link ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, affiliate_link: e.target.value }))}
                  placeholder="https://..."
                />
              </div>
            </div>
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <Button type="submit" disabled={submitting} size="sm">
              {submitting ? "Menyimpan..." : "Simpan Produk"}
            </Button>
          </form>
        )}

        {isLoading && <p className="text-sm text-slate-500">Memuat produk...</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}

        {!isLoading && products.length === 0 && (
          <div className="rounded-lg border bg-white p-8 text-center text-sm text-slate-500">
            Belum ada produk. Tambahkan produk agar AI bisa menjawab pertanyaan customer.
          </div>
        )}

        <div className="space-y-3">
          {products.map((p) => (
            <div
              key={p.id}
              className="flex items-start justify-between gap-3 rounded-lg border bg-white p-4 shadow-sm"
            >
              <div className="min-w-0">
                <p className="font-medium text-slate-900 truncate">{p.name}</p>
                {p.description && (
                  <p className="text-sm text-slate-500 mt-0.5 truncate">{p.description}</p>
                )}
                <div className="mt-1 flex gap-3 text-xs text-slate-400">
                  <span>{formatPrice(p.base_price)}</span>
                  {p.affiliate_link && (
                    <span className="truncate max-w-[200px]">{p.affiliate_link}</span>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-red-500 hover:text-red-700 shrink-0"
                onClick={() => deleteProduct(p.id)}
              >
                Hapus
              </Button>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
