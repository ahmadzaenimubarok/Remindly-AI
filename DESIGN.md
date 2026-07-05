---
name: Reseller AI Dashboard
description: Dashboard otomasi percakapan untuk reseller UMKM Indonesia
colors:
  ink-navy: "#0f172a"
  deep-ink: "#020817"
  teal-accent: "#0d7a8a"
  surface-white: "#ffffff"
  surface-page: "#f8fafc"
  surface-muted: "#f1f5f9"
  slate-mid: "#64748b"
  border-subtle: "#e2e8f0"
  border-default: "#cbd5e1"
  status-hot: "#ef4444"
  status-hot-bg: "#fee2e2"
  status-warm: "#f59e0b"
  status-warm-bg: "#fef3c7"
  status-cold: "#94a3b8"
  status-cold-bg: "#f1f5f9"
  status-active: "#059669"
  status-active-bg: "#d1fae5"
  destructive: "#ef4444"
typography:
  display:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "clamp(1.5rem, 3vw, 2.25rem)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  title:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.01em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink-navy}"
    textColor: "{colors.surface-page}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "#1e293b"
    textColor: "{colors.surface-page}"
  button-outline:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.slate-mid}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    height: "40px"
  button-outline-hover:
    backgroundColor: "{colors.surface-muted}"
    textColor: "#334155"
  badge-status:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.slate-mid}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  input-default:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
    height: "40px"
---

# Design System: Reseller AI Dashboard

## 1. Overview

**Creative North Star: "Mitra Terpercaya"**

Reseller AI Dashboard bukan sekadar alat — ia adalah rekan kerja senior yang tidak pernah panik. Setiap halaman dirancang untuk menjawab satu pertanyaan: *"Apa yang perlu aku lakukan sekarang?"* Informasi disajikan dengan hierarki yang tegas; elemen dekoratif yang tidak menjawab pertanyaan itu tidak ada tempat di sini.

Paletnya bertumpu pada slate yang dalam dan netral, dengan satu aksen teal yang muncul hanya pada elemen yang memerlukan aksi atau perhatian. Status warna — merah untuk eskalasi, kuning untuk perlu dipantau, hijau untuk berjalan, abu untuk tidak aktif — bersifat fungsional, bukan dekoratif. Warna datang dengan makna; tidak ada warna tanpa tugas.

Tipografi menggunakan satu keluarga (system-ui) dalam berbagai bobot. Tidak ada display font yang berteriak. Density sedang: cukup padat untuk operator yang perlu melihat banyak percakapan sekaligus, cukup bernapas agar tidak melelahkan dalam penggunaan panjang.

**Key Characteristics:**
- Monokromatik slate sebagai fondasi, teal sebagai satu-satunya aksen interaktif
- Status selalu visual seketika — tidak perlu membaca label untuk memahami kondisi
- Density sedang — bukan spreadsheet, bukan marketing page
- Komponen terasa solid dan tidak perlu ditelusuri; setiap elemen berperilaku seperti yang diharapkan
- Bahasa Indonesia sebagai first-class citizen, bukan terjemahan

## 2. Colors: The Trusted Slate Palette

Paleta didominasi slate dengan satu aksen teal terarah — restrained strategy, satu warna saturasi untuk CTA dan elemen aktif.

### Primary
- **Ink Navy** (`#0f172a`): Teks utama, button primary, navigasi, semua elemen yang butuh otoritas visual tertinggi. Ini bukan hitam murni — ada kedalaman biru di dalamnya yang membuat layar tidak terasa dingin.
- **Deep Ink** (`#020817`): Cadangan untuk teks paling kritis, heading halaman level display.

### Secondary
- **Teal Accent** (`#0d7a8a`): Satu-satunya warna saturasi dalam sistem ini. Digunakan pada CTA primer di landing page, elemen "aktif/terhubung", dan highlight interaktif yang bukan status. Tidak digunakan sebagai background area luas. Rarity-nya adalah fungsinya.

### Neutral
- **Surface White** (`#ffffff`): Background card, panel, modal — permukaan yang mengambang di atas page.
- **Surface Page** (`#f8fafc`): Background halaman utama — sedikit lebih gelap dari putih untuk memberi kontras dengan card.
- **Surface Muted** (`#f1f5f9`): Hover state, secondary badge background, area disabled.
- **Slate Mid** (`#64748b`): Teks sekunder, timestamp, label metadata, placeholder.
- **Border Subtle** (`#e2e8f0`): Divider antar baris, border card tipis.
- **Border Default** (`#cbd5e1`): Input border, border elemen interaktif default.

### Status (fungsional, bukan dekoratif)
- **Hot** (`#ef4444` / `#fee2e2`): Lead panas, eskalasi, human takeover aktif. Merah selalu berarti "butuh perhatian segera".
- **Warm** (`#f59e0b` / `#fef3c7`): Lead hangat, kondisi perlu dipantau.
- **Cold / Inactive** (`#94a3b8` / `#f1f5f9`): Lead dingin, elemen nonaktif, AI mode default.
- **Active / Positive** (`#059669` / `#d1fae5`): Sesi aktif, sentimen positif, status berjalan baik.

### Named Rules
**The One Accent Rule.** Teal (`#0d7a8a`) muncul di ≤10% permukaan layar mana pun. Jika lebih banyak dari itu, ada sesuatu yang salah dengan hierarki halaman. Status colors bukan accent — mereka data, bukan brand.

**The Status Contract Rule.** Merah = butuh tindakan segera. Kuning = pantau. Hijau = berjalan baik. Abu = tidak aktif. Kontrak ini tidak pernah dilanggar: jangan gunakan merah untuk dekorasi, jangan gunakan hijau untuk CTA.

## 3. Typography

**Body Font:** system-ui, -apple-system, sans-serif (native platform stack)
**No display font pairing** — satu keluarga, variasi bobot.

**Character:** System-ui dipilih bukan karena kurang pilihan, melainkan karena operator membaca dashboard ini dari HP Android dan laptop murah dengan berbagai OS. Font bawaan platform terbaca optimal di setiap resolusi dan tidak menambah beban unduhan. Kepercayaan dibangun lewat konsistensi baca, bukan lewat font mahal.

### Hierarchy
- **Display** (700, clamp 1.5rem→2.25rem, lh 1.2, ls -0.02em): Heading halaman level landing (`h1`). Jarang dipakai di dalam app.
- **Headline** (600, 1.25rem/20px, lh 1.35, ls -0.01em): Section title di dalam dashboard, nama halaman di header.
- **Title** (600, 15px, lh 1.4): Sub-section label, nama customer di thread card, kolom tabel.
- **Body** (400, 14px, lh 1.5): Konten pesan, deskripsi, semua teks operasional. Max line length 65–75ch.
- **Label** (500, 12px, lh 1.4, ls 0.01em): Badge text, timestamp, metadata sekunder, filter pills.

### Named Rules
**The Single Family Rule.** Tidak ada font tambahan kecuali ada keputusan eksplisit yang didokumentasikan. Satu keluarga dengan bobot 400/500/600/700 — cukup untuk semua hierarki yang dibutuhkan dashboard ini.

## 4. Elevation

Sistem ini menggunakan tonal layering, bukan shadow hierarki yang dalam. Surfaces dibedakan lewat warna background, bukan drop shadow bertumpuk.

Satu pengecualian: header bar mendapatkan `box-shadow: 0 1px 3px rgba(0,0,0,0.08)` — bukan untuk kedalaman dramatis, melainkan untuk memisahkan sticky header dari konten yang scroll di bawahnya. Ini adalah fungsi navigasi, bukan dekorasi.

### Shadow Vocabulary
- **Header separator** (`0 1px 3px rgba(0,0,0,0.08)`): Sticky header saja. Selain itu, gunakan border (`border-b border-slate-200`) sebagai pemisah.

### Named Rules
**The Flat-By-Default Rule.** Card dan panel tidak punya shadow di keadaan default. Jika ada informasi yang perlu "muncul" ke permukaan, naikkan background-nya (dari `surface-page` ke `surface-white`), bukan tambahkan shadow.

## 5. Components

### Buttons
- **Shape:** Gently rounded (6px / `rounded-md`)
- **Primary:** Ink Navy background (`#0f172a`), near-white text (`#f8fafc`), padding 8px 16px, height 40px. Semua CTA utama: logout, submit, simpan.
- **Hover / Focus:** Background naik satu step ke `#1e293b`. Focus ring 2px `#0f172a` dengan offset 2px.
- **Outline:** White background, Slate-Mid text, Border Default border. Untuk aksi sekunder: filter, ekspor.
- **Takeover Toggle (signature):** Dua state yang berbeda drastis — AI state: white/slate, border default; Human state: red-500 background, white text. Bukan pill toggle — button berbentuk penuh agar mudah ditekan di HP.
- **Disabled:** 50% opacity, pointer-events none. Tidak ada style khusus lain.

### Badges / Status Chips
- **Shape:** Fully rounded (`rounded-full`), padding 2px 10px, text 12px font-medium
- **Intent/Sentiment badges:** Background tinted (`bg-slate-100 text-slate-600 border border-slate-200`), atau status color variant (merah/kuning/hijau).
- **Escalation badge:** Red background + pulsing dot (`animate-pulse`) untuk eskalasi aktif di header.

### Cards / Thread Containers
- **Corner Style:** None to minimal (border-b untuk pemisah row, bukan card per-row)
- **Background:** White untuk panel utama, slate-50 untuk page background
- **Shadow Strategy:** Tidak ada shadow pada card. Header menggunakan shadow tipis.
- **Border:** `border border-slate-200` untuk panel. `border-b border-slate-100` untuk divider antar baris.
- **Internal Padding:** 12px 16px (px-4 py-3) untuk row data.

### Inputs / Fields
- **Style:** White background, Border Default border (`#cbd5e1`), 8px radius
- **Focus:** Ring 2px `#0f172a` dengan 2px offset — tidak ada glow warna lain
- **Placeholder:** `#64748b` (slate-500) — pastikan contrast ≥4.5:1 terhadap white background
- **Disabled:** 50% opacity, cursor not-allowed

### Navigation / Header
- **Style:** White background, bottom border `border-slate-200`, shadow tipis
- **Logo + product name:** h-7/w-7 rounded-full logo, 14px semibold teks kanan
- **Escalation indicator:** Badge merah dengan pulsing dot, hanya muncul saat ada eskalasi

### Thread Row (Signature Component)
Row percakapan di Inbox — bukan card tersendiri, melainkan row dengan border-b.
- Default: white background
- Human takeover: red-50 background (`bg-red-50`) sebagai visual cue kuat
- Struktur: timestamp kiri (10px slate-400), pesan kanan (14px slate-800), balasan AI (italic slate-500)
- Controls di kanan: badge intent, badge sentiment, takeover toggle

### Lead Card (Signature Component)
Card lead dengan heat bar — satu elemen visual yang menggantikan angka score.
- Heat bar: 4px height, full width, rounded-full, background slate-100, fill warna sesuai tier
- Dot indicator + badge di kiri sebagai secondary confirmation tier
- Padding `p-4`, border `border border-{tier}-200`, rounded-lg

## 6. Do's and Don'ts

### Do:
- **Do** gunakan status colors sesuai kontrak: merah = tindakan segera, kuning = pantau, hijau = baik, abu = nonaktif. Tidak ada pengecualian.
- **Do** gunakan teal (`#0d7a8a`) hanya untuk satu CTA atau elemen interaktif aktif per layar.
- **Do** bedakan permukaan lewat background color (slate-50 page vs white card), bukan shadow bertumpuk.
- **Do** gunakan `border-b border-slate-100` untuk divider antar baris — bukan `border-left` berwarna.
- **Do** pastikan placeholder text ≥4.5:1 contrast ratio terhadap background-nya.
- **Do** sertakan `@media (prefers-reduced-motion: reduce)` untuk setiap animasi — termasuk `animate-pulse` pada escalation badge.
- **Do** jaga text body ≤75ch line length pada halaman berkonten panjang.

### Don't:
- **Don't** gunakan gradient text (`background-clip: text` + gradient) pada label atau heading apapun — ini ada dalam anti-references PRODUCT.md secara eksplisit.
- **Don't** gunakan `border-left` tebal berwarna sebagai aksen card atau list item — rewrite dengan background tint atau border penuh.
- **Don't** gunakan `rounded-full` pada button besar, card, atau container — ini ada dalam anti-references PRODUCT.md.
- **Don't** buat layout yang terasa seperti generic US SaaS: Inter font + blue-purple gradient + identical card grid.
- **Don't** tambahkan warna aksen kedua tanpa revisi The One Accent Rule — sistem ini dirancang monokromatik slate + satu teal.
- **Don't** gunakan shadow bertumpuk (multiple `box-shadow` layers) kecuali ada kebutuhan fungsional yang jelas; flat-by-default.
- **Don't** animasikan layout properties (width, height, padding, top, left) — hanya transform dan opacity untuk performa.
- **Don't** tampilkan konten yang hanya visible setelah class ditambahkan JavaScript — content harus visible by default, animasi hanya enhance.
