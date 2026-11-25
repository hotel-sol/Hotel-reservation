"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { membersApi } from "@/lib/api/members";
import { menusApi } from "@/lib/api/rooms";
import type { Member, MenuItem } from "@/types/api";

/**
 * 상단 메뉴: DB menu 테이블 + 로그인 상태
 * - 화면 영역에 맞는 묶음만 보여준다: /admin/* = 관리자 메뉴, 그 밖 = 손님 메뉴
 * - 관리자는 오른쪽 위 이름 옆 버튼으로 "관리자 페이지" ↔ "고객 화면"을 오간다(같은 자리, 글자만 바뀜)
 */
export default function Header() {
  const pathname = usePathname();
  const [member, setMember] = useState<Member | null>(null);
  const [menus, setMenus] = useState<MenuItem[]>([]);

  useEffect(() => {
    let ignore = false; // 페이지 이동이 빠를 때 이전 응답이 로그인 상태를 덮어쓰지 않게
    membersApi.me().then((m) => { if (!ignore) setMember(m); }).catch(() => { if (!ignore) setMember(null); });
    menusApi.list().then((m) => { if (!ignore) setMenus(m); }).catch(() => { if (!ignore) setMenus([]); });
    return () => { ignore = true; };
  }, [pathname]);

  const isAdmin = member?.role === "ADMIN";
  const adminArea = pathname === "/admin" || pathname.startsWith("/admin/");
  const visibleMenus = menus.filter((m) => m.role === (adminArea ? "ADMIN" : "USER"));

  async function logout() {
    await membersApi.logout();
    // 페이지 전체를 새로 읽는다(router.push 아님): 숨겨 둔 화면(Activity)에 이전 사람의 예약 · 정보가 남지 않게
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- 의도적인 하드 이동
    window.location.assign("/login");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href={adminArea ? "/admin" : "/rooms"} className="flex items-baseline gap-1.5 font-bold text-blue-700">
          🏨 Hotel
          {adminArea && <span className="text-xs font-medium text-slate-500">관리자</span>}
        </Link>
        <nav className="flex flex-1 items-center gap-1 text-sm">
          {visibleMenus.map((m) => (
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
                {member.name}님{isAdmin && " (관리자)"}
              </span>
              {isAdmin &&
                (adminArea ? (
                  <Link href="/rooms" className="btn-outline py-1">
                    고객 화면
                  </Link>
                ) : (
                  <Link href="/admin" className="inline-flex items-center rounded-md bg-slate-900 px-3 py-1 font-medium text-white transition hover:bg-slate-700">
                    관리자 페이지
                  </Link>
                ))}
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
