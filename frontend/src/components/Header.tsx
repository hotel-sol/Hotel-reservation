"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { membersApi } from "@/lib/api/members";
import { menusApi } from "@/lib/api/rooms";
import type { Member, MenuItem } from "@/types/api";

/** 상단 메뉴: DB menu 테이블 + 로그인 상태 */
export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [member, setMember] = useState<Member | null>(null);
  const [menus, setMenus] = useState<MenuItem[]>([]);

  useEffect(() => {
    membersApi.me().then(setMember).catch(() => setMember(null));
    menusApi.list().then(setMenus).catch(() => setMenus([]));
  }, [pathname]);

  async function logout() {
    await membersApi.logout();
    setMember(null);
    router.push("/login");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/rooms" className="font-bold text-blue-700">
          🏨 Hotel
        </Link>
        <nav className="flex flex-1 items-center gap-1 text-sm">
          {menus.map((m) => (
            <div key={m.menuId} className="group relative">
              {m.menuUrl ? (
                <Link href={m.menuUrl} className="rounded px-3 py-2 hover:bg-slate-100">
                  {m.menuName}
                </Link>
              ) : (
                <span className="cursor-default rounded px-3 py-2 hover:bg-slate-100">{m.menuName}</span>
              )}
              {m.children.length > 0 && (
                <div className="invisible absolute left-0 top-full z-10 min-w-36 rounded-md border border-slate-200 bg-white py-1 shadow-md group-hover:visible">
                  {m.children.map((c) => (
                    <Link key={c.menuId} href={c.menuUrl ?? "#"} className="block px-3 py-2 hover:bg-slate-50">
                      {c.menuName}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>
        <div className="flex items-center gap-2 text-sm">
          {member ? (
            <>
              <span className="text-slate-600">
                {member.name}님{member.role === "ADMIN" && " (관리자)"}
              </span>
              <button onClick={logout} className="btn-outline py-1">
                로그아웃
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="btn-outline py-1">
                로그인
              </Link>
              <Link href="/signup" className="btn-primary py-1">
                회원가입
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
