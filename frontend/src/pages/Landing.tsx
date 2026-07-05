import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: "↩",
    title: "Balas Otomatis 24/7",
    desc: "AI membalas komentar dan DM Facebook atas nama tokomu — dengan konteks produk yang tepat, kapan saja.",
  },
  {
    icon: "⬡",
    title: "Klasifikasi Lead",
    desc: "Setiap pelanggan yang interaksi otomatis dikategorikan: panas, hangat, atau dingin — tanpa input manual.",
  },
  {
    icon: "↑",
    title: "Prioritas Cerdas",
    desc: "Dashboard lead membantumu fokus ke calon pembeli paling potensial, bukan tenggelam di ratusan chat.",
  },
  {
    icon: "⚡",
    title: "Human Takeover",
    desc: "Ketika AI mendeteksi komplain atau isu sensitif, notifikasi langsung masuk dan kamu ambil alih.",
  },
];

const STEPS = [
  {
    num: "01",
    title: "Buat akun",
    desc: "Workspace siap dalam 2 menit. Tidak perlu kartu kredit untuk mulai.",
  },
  {
    num: "02",
    title: "Hubungkan Facebook",
    desc: "Connect Facebook Page bisnismu. OAuth aman, token tersimpan terenkripsi.",
  },
  {
    num: "03",
    title: "AI bekerja",
    desc: "Engagement aktif — AI balas chat, deteksi niat beli, dan kelola lead secara otomatis.",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "Gratis",
    period: false,
    features: ["1 akun Facebook", "50 AI reply/bulan", "Dashboard percakapan"],
    highlight: false,
  },
  {
    name: "Starter",
    price: "Rp 149.000",
    period: true,
    features: [
      "3 akun Facebook",
      "500 AI reply/bulan",
      "Klasifikasi lead",
      "Analitik dasar",
    ],
    highlight: true,
  },
  {
    name: "Pro",
    price: "Rp 399.000",
    period: true,
    features: [
      "10 akun Facebook",
      "3.000 AI reply/bulan",
      "Klasifikasi lead lanjutan",
      "Custom AI tone",
      "Priority support",
    ],
    highlight: false,
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-slate-900 antialiased">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-100 bg-white/90 backdrop-blur-sm px-6 py-3.5">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img
              src="/logo.jpeg"
              alt="Remindly AI"
              className="h-7 w-7 rounded-full object-cover"
            />
            <span className="text-sm font-semibold tracking-tight text-slate-900">
              Remindly AI
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              asChild
              className="text-slate-600 hover:text-slate-900"
            >
              <Link to="/login">Masuk</Link>
            </Button>
            <Button
              size="sm"
              className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm"
              asChild
            >
              <Link to="/login">Coba Gratis</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <p className="mb-5 text-xs font-medium uppercase tracking-widest text-slate-400">
          Untuk reseller UMKM Indonesia
        </p>
        <h1 className="mb-5 text-[2.75rem] font-bold leading-[1.15] tracking-tight text-slate-900">
          Jual lebih banyak.
          <br />
          <span className="text-slate-400">Tanpa kerja lebih keras.</span>
        </h1>
        <p className="mb-10 text-base text-slate-500 max-w-lg mx-auto leading-relaxed">
          AI yang membantu reseller balas chat Facebook, deteksi calon pembeli,
          dan kelola lead — bekerja 24 jam atas nama tokomu.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm px-7"
            asChild
          >
            <Link to="/login">Mulai Gratis</Link>
          </Button>
          <span className="text-xs text-slate-400">Tidak perlu kartu kredit</span>
        </div>
      </section>

      {/* Features */}
      <section className="border-y border-slate-100 bg-slate-50 py-20">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-3 text-center text-2xl font-bold tracking-tight">
            Dua hal yang AI-mu kuasai
          </h2>
          <p className="mb-12 text-center text-sm text-slate-400">
            Engagement otomatis dan intelijen lead — dalam satu platform.
          </p>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-sm font-medium text-slate-600">
                  {f.icon}
                </div>
                <h3 className="mb-2 text-sm font-semibold text-slate-900">
                  {f.title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-12 text-center text-2xl font-bold tracking-tight">
            Tiga langkah untuk mulai
          </h2>
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.num}>
                <span className="mb-4 block text-3xl font-bold text-slate-100 leading-none select-none">
                  {s.num}
                </span>
                <h3 className="mb-2 text-sm font-semibold text-slate-900">
                  {s.title}
                </h3>
                <p className="text-sm text-slate-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="border-y border-slate-100 bg-slate-50 py-20">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-3 text-center text-2xl font-bold tracking-tight">
            Harga yang jelas
          </h2>
          <p className="mb-12 text-center text-sm text-slate-400">
            Mulai gratis, upgrade kapan saja.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className={[
                  "rounded-xl border bg-white p-6",
                  p.highlight
                    ? "border-slate-900 shadow-md ring-1 ring-slate-900/5"
                    : "border-slate-200 shadow-sm",
                ].join(" ")}
              >
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    {p.name}
                  </span>
                  {p.highlight && (
                    <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-semibold text-white">
                      Populer
                    </span>
                  )}
                </div>
                <p className="mb-5 mt-2 text-2xl font-bold text-slate-900">
                  {p.price}
                  {p.period && (
                    <span className="text-xs font-normal text-slate-400">
                      /bulan
                    </span>
                  )}
                </p>
                <ul className="mb-6 space-y-2">
                  {p.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2 text-xs text-slate-500"
                    >
                      <span className="mt-0.5 text-slate-300">—</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className={[
                    "w-full text-sm",
                    p.highlight
                      ? "bg-slate-900 text-white hover:bg-slate-800 shadow-sm"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50",
                  ].join(" ")}
                  variant={p.highlight ? "default" : "outline"}
                  size="sm"
                  asChild
                >
                  <Link to="/login">Mulai</Link>
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 text-center">
        <div className="mx-auto max-w-xl px-6">
          <img
            src="/logo.jpeg"
            alt="Remindly AI"
            className="mx-auto mb-6 h-12 w-12 rounded-full object-cover opacity-90"
          />
          <h2 className="mb-4 text-2xl font-bold tracking-tight">
            Siap otomasi toko kamu?
          </h2>
          <p className="mb-8 text-sm text-slate-500">
            Bergabung dan biarkan AI bekerja untuk tokomu hari ini.
          </p>
          <Button
            size="lg"
            className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm px-8"
            asChild
          >
            <Link to="/login">Mulai Gratis Sekarang</Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-100 px-6 py-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-2 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <img
              src="/logo.jpeg"
              alt="Remindly AI"
              className="h-5 w-5 rounded-full object-cover opacity-60"
            />
            <span className="text-xs text-slate-400">
              © 2026 Remindly AI. Semua hak dilindungi.
            </span>
          </div>
          <div className="flex gap-4 text-xs text-slate-400">
            <Link to="/privacy" className="hover:text-slate-700 transition-colors">
              Privacy Policy
            </Link>
            <Link to="/terms" className="hover:text-slate-700 transition-colors">
              Terms of Service
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
