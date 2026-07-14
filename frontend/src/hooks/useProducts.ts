import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  base_price: string | null;
  affiliate_link: string | null;
  status: string;
  source: string;
  shopify_product_id: string | null;
  shopify_synced_at: string | null;
}

export interface CreateProductPayload {
  name: string;
  description?: string;
  category?: string;
  base_price?: number;
  affiliate_link?: string;
}

export function useProducts() {
  const [products, setProducts] = useState<ProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<{ data: ProductResponse[] }>("/products");
      setProducts(res.data.data ?? []);
    } catch {
      setError("Gagal memuat produk.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  async function addProduct(payload: CreateProductPayload): Promise<ProductResponse> {
    const res = await api.post<{ data: ProductResponse }>("/products", payload);
    await fetchProducts();
    return res.data.data;
  }

  async function updateProduct(
    id: string,
    payload: Partial<CreateProductPayload & { status: string }>,
  ): Promise<void> {
    await api.patch(`/products/${id}`, payload);
    await fetchProducts();
  }

  async function deleteProduct(id: string): Promise<void> {
    await api.delete(`/products/${id}`);
    setProducts((prev) => prev.filter((p) => p.id !== id));
  }

  return { products, isLoading, error, addProduct, updateProduct, deleteProduct };
}
