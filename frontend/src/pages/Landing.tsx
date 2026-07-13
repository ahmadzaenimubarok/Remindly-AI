import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: "↩",
    title: "24/7 Auto Reply",
    desc: "AI replies to Facebook Messenger, Instagram DMs, and page comments on behalf of your business — with the right context, anytime.",
  },
  {
    icon: "⬡",
    title: "Lead Scoring",
    desc: "Every customer interaction is automatically categorized: hot, warm, or cold — no manual input needed.",
  },
  {
    icon: "↑",
    title: "Smart Prioritization",
    desc: "The lead dashboard helps you focus on the most promising prospects, not drown in hundreds of conversations.",
  },
  {
    icon: "⚡",
    title: "Human Takeover",
    desc: "When AI detects complaints or sensitive issues, notifications come through instantly and you take over.",
  },
];

const STEPS = [
  {
    num: "01",
    title: "Create an account",
    desc: "Workspace ready in 2 minutes. No credit card required to start.",
  },
  {
    num: "02",
    title: "Connect your channels",
    desc: "Connect your Facebook Page and Instagram Business account. Secure OAuth, encrypted token storage.",
  },
  {
    num: "03",
    title: "AI goes to work",
    desc: "Active engagement — AI replies to chats, detects purchase intent, and manages leads automatically.",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "Free",
    period: false,
    features: ["1 social account (FB or IG)", "50 AI replies/month", "Unified inbox"],
    highlight: false,
  },
  {
    name: "Starter",
    price: "Rp 149,000",
    period: true,
    features: [
      "3 social accounts",
      "500 AI replies/month",
      "Lead scoring",
      "Basic analytics",
    ],
    highlight: true,
  },
  {
    name: "Pro",
    price: "Rp 399,000",
    period: true,
    features: [
      "10 social accounts",
      "3,000 AI replies/month",
      "Advanced lead scoring",
      "Custom AI tone",
      "Priority support",
      "Shopify import (coming soon)",
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
              <Link to="/login">Sign In</Link>
            </Button>
            <Button
              size="sm"
              className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm"
              asChild
            >
              <Link to="/login">Try Free</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <p className="mb-5 text-xs font-medium uppercase tracking-widest text-slate-400">
          AI customer engagement
        </p>
        <h1 className="mb-5 text-[2.75rem] font-bold leading-[1.15] tracking-tight text-slate-900">
          Sell more on Facebook & Instagram.
          <br />
          <span className="text-slate-400">Without working harder.</span>
        </h1>
        <p className="mb-10 text-base text-slate-500 max-w-lg mx-auto leading-relaxed">
          AI that replies to Facebook Messenger, Instagram DMs, and page comments —
          detects purchase intent, and manages leads — working 24/7 on your behalf.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm px-7"
            asChild
          >
            <Link to="/login">Get Started Free</Link>
          </Button>
          <span className="text-xs text-slate-400">No credit card required</span>
        </div>
      </section>

      {/* Features */}
      <section className="border-y border-slate-100 bg-slate-50 py-20">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="mb-3 text-center text-2xl font-bold tracking-tight">
            Everything your AI handles
          </h2>
          <p className="mb-12 text-center text-sm text-slate-400">
            Multi-platform engagement and lead intelligence — in one dashboard.
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
            Three steps to get started
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
            Simple pricing
          </h2>
          <p className="mb-12 text-center text-sm text-slate-400">
            Start free, upgrade anytime.
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
                      Popular
                    </span>
                  )}
                </div>
                <p className="mb-5 mt-2 text-2xl font-bold text-slate-900">
                  {p.price}
                  {p.period && (
                    <span className="text-xs font-normal text-slate-400">
                      /month
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
                  <Link to="/login">Get Started</Link>
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Coming Soon */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-6 text-center">
          <p className="mb-3 text-xs font-medium uppercase tracking-widest text-slate-400">
            Roadmap
          </p>
          <h2 className="mb-6 text-2xl font-bold tracking-tight">
            More integrations coming soon
          </h2>
          <div className="flex flex-wrap justify-center gap-3">
            {["WhatsApp Business", "TikTok", "Shopify Product Import"].map(
              (name) => (
                <span
                  key={name}
                  className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500 shadow-sm"
                >
                  {name}
                </span>
              )
            )}
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
            Ready to automate your business?
          </h2>
          <p className="mb-8 text-sm text-slate-500">
            Join now and let AI work across all your channels today.
          </p>
          <Button
            size="lg"
            className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm px-8"
            asChild
          >
            <Link to="/login">Get Started Free Now</Link>
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
              © 2026 Remindly AI. All rights reserved.
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
