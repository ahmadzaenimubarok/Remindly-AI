import { Link } from "react-router-dom";

const LAST_UPDATED = "4 Juli 2026";
const CONTACT_EMAIL = "admin@jawakoentji.my.id";
const DOMAIN = "reseller.jawakoentji.my.id";

export default function Privacy() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="border-b border-slate-100 px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <Link to="/" className="text-sm font-semibold tracking-tight hover:text-slate-600">
            Remindly AI
          </Link>
          <Link to="/terms" className="text-xs text-slate-400 hover:text-slate-700">
            Terms of Service
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="mb-2 text-2xl font-bold tracking-tight">Privacy Policy</h1>
        <p className="mb-10 text-xs text-slate-400">Terakhir diperbarui: {LAST_UPDATED}</p>

        <div className="space-y-8 text-sm text-slate-600 leading-relaxed">
          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">1. Tentang Platform Ini</h2>
            <p>
              Remindly AI (<code className="text-xs bg-slate-100 px-1 rounded">{DOMAIN}</code>) adalah platform SaaS yang
              membantu reseller Indonesia mengotomatisasi penemuan produk, pembuatan konten, dan engagement media sosial
              menggunakan kecerdasan buatan. Kebijakan privasi ini menjelaskan data apa yang kami kumpulkan, bagaimana
              kami menggunakannya, dan hak-hak Anda sebagai pengguna.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">2. Data yang Kami Kumpulkan</h2>
            <h3 className="mb-2 text-sm font-medium text-slate-700">2.1 Data Akun</h3>
            <ul className="mb-4 list-disc space-y-1 pl-5">
              <li>Alamat email dan password (tersimpan ter-hash)</li>
              <li>Nama toko dan preferensi bisnis yang Anda isi saat onboarding</li>
            </ul>
            <h3 className="mb-2 text-sm font-medium text-slate-700">2.2 Data Integrasi Facebook / Meta</h3>
            <ul className="mb-4 list-disc space-y-1 pl-5">
              <li>Nama dan ID Facebook Page yang Anda hubungkan melalui OAuth</li>
              <li>Page Access Token yang diterbitkan oleh Meta — disimpan terenkripsi (AES-256) dan tidak pernah dibagikan ke pihak ketiga</li>
              <li>Komentar dan pesan masuk di Facebook Page dan Messenger yang dikirim oleh follower/customer Anda, diterima melalui Webhook Meta</li>
              <li>Balasan yang dikirimkan AI atas nama Page Anda</li>
            </ul>
            <h3 className="mb-2 text-sm font-medium text-slate-700">2.3 Data Percakapan Customer</h3>
            <p>
              Pesan yang dikirim oleh customer Anda ke Facebook Page atau Messenger Anda diproses oleh AI untuk menghasilkan
              balasan yang relevan. Data ini dikaitkan dengan workspace Anda dan tidak dapat diakses oleh pengguna lain
              (multi-tenant isolation).
            </p>
            <h3 className="mb-2 text-sm font-medium text-slate-700">2.4 Data Penggunaan Platform</h3>
            <ul className="list-disc space-y-1 pl-5">
              <li>Log aktivitas AI (post dibuat, reply dikirim, produk ditemukan) untuk billing dan analytics</li>
              <li>Data teknis: IP address, browser agent, waktu akses — untuk keamanan dan debugging</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">3. Bagaimana Kami Menggunakan Data</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Menjalankan fitur platform: auto-reply, content generation, product discovery</li>
              <li>Mengirimkan balasan AI ke Facebook Page dan Messenger atas permintaan dan konfigurasi Anda</li>
              <li>Menghitung penggunaan untuk keperluan billing dan quota enforcement</li>
              <li>Meningkatkan kualitas dan keamanan layanan</li>
              <li>Mengirimkan notifikasi penting terkait akun atau layanan</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">4. Data yang Tidak Kami Lakukan</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Kami <strong>tidak menjual</strong> data Anda atau data customer Anda ke pihak ketiga manapun</li>
              <li>Kami <strong>tidak menggunakan</strong> pesan customer Anda untuk melatih model AI tanpa persetujuan eksplisit</li>
              <li>Kami <strong>tidak membagikan</strong> Page Access Token Anda ke layanan selain Meta Graph API</li>
              <li>Kami <strong>tidak menyimpan</strong> konten pesan customer lebih lama dari yang diperlukan untuk fitur platform</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">5. Penyimpanan & Keamanan Data</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Semua credential OAuth (Page Access Token) disimpan terenkripsi menggunakan AES-256</li>
              <li>Data antar pengguna diisolasi secara ketat — tidak ada akses lintas workspace</li>
              <li>Koneksi ke server menggunakan HTTPS/TLS</li>
              <li>Password tidak pernah disimpan plaintext — selalu di-hash menggunakan bcrypt</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">6. Penggunaan Meta / Facebook API</h2>
            <p className="mb-3">
              Platform ini menggunakan Meta Platform API (Facebook Graph API) untuk mengakses konten Facebook Page dan
              Messenger yang telah Anda hubungkan. Dengan menghubungkan Facebook Page Anda, Anda memberikan izin kepada
              platform untuk:
            </p>
            <ul className="mb-3 list-disc space-y-1 pl-5">
              <li>Membaca komentar dan pesan masuk di Page Anda (<code className="text-xs bg-slate-100 px-1 rounded">pages_read_engagement</code>)</li>
              <li>Mengirimkan balasan ke komentar dan pesan (<code className="text-xs bg-slate-100 px-1 rounded">pages_manage_posts</code>, <code className="text-xs bg-slate-100 px-1 rounded">pages_messaging</code>)</li>
            </ul>
            <p>
              Anda dapat mencabut akses kapan saja melalui halaman Settings di dashboard, atau langsung dari pengaturan
              Facebook Page Anda. Penggunaan data Meta tunduk pada{" "}
              <a
                href="https://www.facebook.com/privacy/policy/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-900 underline"
              >
                Meta Privacy Policy
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">7. Hak-Hak Anda</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li><strong>Akses:</strong> Anda dapat melihat data akun dan percakapan Anda melalui dashboard</li>
              <li><strong>Koreksi:</strong> Anda dapat mengubah informasi akun kapan saja melalui Settings</li>
              <li><strong>Penghapusan:</strong> Anda dapat meminta penghapusan seluruh data akun dan workspace Anda dengan menghubungi kami — data akan dihapus dalam 30 hari</li>
              <li><strong>Portabilitas:</strong> Anda dapat meminta ekspor data percakapan Anda dalam format JSON</li>
              <li><strong>Pencabutan akses:</strong> Anda dapat memutus koneksi Facebook Page kapan saja dari Settings</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">8. Perubahan Kebijakan</h2>
            <p>
              Kami dapat memperbarui kebijakan privasi ini sewaktu-waktu. Perubahan material akan diberitahukan melalui
              email atau notifikasi di dashboard minimal 7 hari sebelum berlaku. Tanggal pembaruan terakhir selalu
              tercantum di bagian atas halaman ini.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">9. Hubungi Kami</h2>
            <p>
              Untuk pertanyaan, permintaan penghapusan data, atau laporan terkait privasi, hubungi kami di:{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="text-slate-900 underline">
                {CONTACT_EMAIL}
              </a>
            </p>
          </section>
        </div>
      </main>

      <footer className="border-t border-slate-100 px-6 py-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <span className="text-xs text-slate-400">© 2026 Remindly AI</span>
          <div className="flex gap-4 text-xs text-slate-400">
            <Link to="/" className="hover:text-slate-700">Beranda</Link>
            <Link to="/terms" className="hover:text-slate-700">Terms of Service</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
