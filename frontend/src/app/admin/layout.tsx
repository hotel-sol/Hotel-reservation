import Link from "next/link";
import AdminGuard from "./AdminGuard";

const LINKS = [
  { href: "/admin/rooms", label: "객실 관리" },
  { href: "/admin/closed-dates", label: "예약 일자 관리" },
  { href: "/admin/reservations", label: "예약 관리" },
];

export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return (
    <div className="grid gap-6 md:grid-cols-[180px_1fr]">
      <aside className="space-y-1 text-sm">
        <p className="mb-2 font-semibold text-slate-500">관리자</p>
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="block rounded px-3 py-2 hover:bg-white">
            {l.label}
          </Link>
        ))}
      </aside>
      <section>
        <AdminGuard>{children}</AdminGuard>
      </section>
    </div>
  );
}
