import { Link } from "react-router-dom";

const LAST_UPDATED = "4 Juli 2026";
const CONTACT_EMAIL = "admin@jawakoentji.my.id";

export default function Terms() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="border-b border-slate-100 px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <Link to="/" className="text-sm font-semibold tracking-tight hover:text-slate-600">
            Remindly AI
          </Link>
          <Link to="/privacy" className="text-xs text-slate-400 hover:text-slate-700">
            Privacy Policy
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="mb-2 text-2xl font-bold tracking-tight">Terms of Service</h1>
        <p className="mb-10 text-xs text-slate-400">Terakhir diperbarui: {LAST_UPDATED}</p>

        <div className="space-y-8 text-sm text-slate-600 leading-relaxed">
          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">1. Penerimaan Syarat</h2>
            <p>
              Dengan mendaftar atau menggunakan platform Remindly AI, Anda menyatakan bahwa Anda telah membaca,
              memahami, dan menyetujui Syarat Penggunaan ini. Jika Anda tidak setuju, jangan gunakan layanan ini.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">2. Deskripsi Layanan</h2>
            <p>
              Remindly AI adalah platform SaaS yang menyediakan alat berbasis kecerdasan buatan untuk membantu
              reseller mengotomatisasi penemuan produk, pembuatan konten pemasaran, engagement media sosial, dan
              konversi penjualan. Layanan ini terhubung ke platform pihak ketiga (termasuk Meta/Facebook) atas
              instruksi dan konfigurasi pengguna.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">3. Kewajiban Pengguna</h2>
            <p className="mb-3">Sebagai pengguna platform, Anda bertanggung jawab untuk:</p>
            <ul className="list-disc space-y-2 pl-5">
              <li>Hanya menghubungkan akun media sosial dan Facebook Page yang merupakan milik Anda sendiri atau yang Anda kelola secara sah</li>
              <li>Mematuhi Syarat Penggunaan platform pihak ketiga yang Anda hubungkan (termasuk Meta Platform Terms, Facebook Page Policies)</li>
              <li>Memastikan konten yang dipublikasikan atau balasan yang dikirim melalui platform ini tidak melanggar hukum yang berlaku</li>
              <li>Tidak menggunakan platform untuk mengirim spam, konten menyesatkan, atau melanggar kebijakan platform sosial media</li>
              <li>Menjaga kerahasiaan kredensial akun Anda</li>
              <li>Memberikan informasi yang akurat saat mendaftar</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">4. Penggunaan AI dan Konten yang Dihasilkan</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Konten yang dihasilkan AI (caption, balasan, pesan) adalah saran otomatis — Anda bertanggung jawab atas konten yang dikirimkan atas nama akun Anda</li>
              <li>Anda dapat mengaktifkan mode review manusia untuk memeriksa konten sebelum dipublikasikan</li>
              <li>Platform tidak menjamin bahwa konten AI selalu akurat, sesuai, atau bebas dari kesalahan</li>
              <li>Anda tidak boleh menggunakan platform untuk membuat atau menyebarkan konten yang melanggar hak kekayaan intelektual pihak lain</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">5. Integrasi Meta / Facebook</h2>
            <p className="mb-3">
              Platform ini menggunakan Meta Platform API. Dengan menghubungkan Facebook Page Anda:
            </p>
            <ul className="list-disc space-y-2 pl-5">
              <li>Anda mengonfirmasi bahwa Anda memiliki hak dan izin untuk mengelola Page tersebut</li>
              <li>Anda memahami bahwa pelanggaran terhadap Meta Platform Terms dapat mengakibatkan pembatasan atau penangguhan akun Facebook Anda oleh Meta</li>
              <li>Platform ini tidak bertanggung jawab atas tindakan Meta terhadap akun Anda akibat penggunaan yang tidak sesuai</li>
              <li>Anda dapat mencabut akses platform ke Facebook Page Anda kapan saja melalui Settings</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">6. Subscription dan Pembayaran</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Plan berbayar ditagih bulanan di awal periode</li>
              <li>Pembatalan dapat dilakukan kapan saja — akses tetap aktif hingga akhir periode yang sudah dibayar</li>
              <li>Tidak ada refund untuk periode yang sudah berjalan kecuali diwajibkan oleh hukum</li>
              <li>Kami berhak mengubah harga dengan pemberitahuan minimal 30 hari sebelumnya</li>
              <li>Jika pembayaran gagal, akun akan downgrade ke Free plan setelah periode tenggang 7 hari</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">7. Batasan Tanggung Jawab</h2>
            <p className="mb-3">
              Platform ini disediakan "sebagaimana adanya" (<em>as is</em>). Kami tidak menjamin:
            </p>
            <ul className="mb-3 list-disc space-y-1 pl-5">
              <li>Bahwa layanan akan selalu tersedia tanpa gangguan</li>
              <li>Bahwa konten AI akan selalu menghasilkan penjualan</li>
              <li>Bahwa integrasi dengan platform pihak ketiga akan selalu berfungsi (platform pihak ketiga dapat mengubah API mereka)</li>
            </ul>
            <p>
              Kami tidak bertanggung jawab atas kerugian langsung maupun tidak langsung yang timbul dari penggunaan
              platform, termasuk hilangnya pendapatan, penangguhan akun sosial media oleh platform pihak ketiga, atau
              kerusakan reputasi akibat konten yang dihasilkan AI.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">8. Penghentian Akun</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Anda dapat menghapus akun kapan saja melalui Settings atau dengan menghubungi kami</li>
              <li>Kami berhak menangguhkan atau menghentikan akun yang melanggar syarat penggunaan ini tanpa pemberitahuan sebelumnya</li>
              <li>Setelah akun dihapus, data Anda akan dihapus permanen dalam 30 hari</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">9. Perubahan Syarat</h2>
            <p>
              Kami dapat memperbarui syarat ini sewaktu-waktu. Perubahan material akan diberitahukan melalui email atau
              notifikasi dashboard minimal 7 hari sebelum berlaku. Melanjutkan penggunaan layanan setelah perubahan
              berlaku berarti Anda menerima syarat yang baru.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">10. Hukum yang Berlaku</h2>
            <p>
              Syarat ini tunduk pada hukum Republik Indonesia. Sengketa diselesaikan melalui musyawarah terlebih
              dahulu, dan jika tidak tercapai kesepakatan, melalui jalur hukum yang berlaku di Indonesia.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-slate-900">11. Hubungi Kami</h2>
            <p>
              Pertanyaan tentang syarat penggunaan ini dapat dikirimkan ke:{" "}
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
            <Link to="/privacy" className="hover:text-slate-700">Privacy Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
