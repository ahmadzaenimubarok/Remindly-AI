import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import Landing from "@/pages/Landing";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import Login from "@/pages/Login";
import Inbox from "@/pages/Inbox";
import Leads from "@/pages/Leads";
import Products from "@/pages/Products";
import Settings from "@/pages/Settings";
import Billing from "@/pages/Billing";
import FacebookCallback from "@/pages/FacebookCallback";
import FacebookPages from "@/pages/FacebookPages";
import InstagramCallback from "@/pages/InstagramCallback";
import InstagramConnect from "@/pages/InstagramConnect";
import ShopifyConnect from "@/pages/ShopifyConnect";
import ShopifyCallback from "@/pages/ShopifyCallback";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Memuat...
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/inbox"
        element={
          <ProtectedRoute>
            <Inbox />
          </ProtectedRoute>
        }
      />
      <Route
        path="/leads"
        element={
          <ProtectedRoute>
            <Leads />
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={
          <ProtectedRoute>
            <Products />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/billing"
        element={
          <ProtectedRoute>
            <Billing />
          </ProtectedRoute>
        }
      />
      <Route
        path="/auth/facebook/callback"
        element={
          <ProtectedRoute>
            <FacebookCallback />
          </ProtectedRoute>
        }
      />
      <Route
        path="/auth/facebook/pages"
        element={
          <ProtectedRoute>
            <FacebookPages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/auth/instagram/callback"
        element={
          <ProtectedRoute>
            <InstagramCallback />
          </ProtectedRoute>
        }
      />
      <Route
        path="/auth/instagram/connect"
        element={
          <ProtectedRoute>
            <InstagramConnect />
          </ProtectedRoute>
        }
      />
      <Route
        path="/auth/shopify/connect"
        element={
          <ProtectedRoute>
            <ShopifyConnect />
          </ProtectedRoute>
        }
      />
      <Route
        path="/auth/shopify/callback"
        element={
          <ProtectedRoute>
            <ShopifyCallback />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
