import { useState } from "react";
import api from "@/lib/api";

interface ImportResult {
  imported: number;
  updated: number;
  errors: string[];
}

export function useShopifyImport() {
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function importFromShopify(): Promise<ImportResult | null> {
    setIsImporting(true);
    setError(null);

    try {
      const response = await api.post("/products/shopify/import");
      return response.data.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Gagal import produk dari Shopify.";
      setError(message);
      return null;
    } finally {
      setIsImporting(false);
    }
  }

  return {
    importFromShopify,
    isImporting,
    error,
  };
}
