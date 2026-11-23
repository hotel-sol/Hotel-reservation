"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { membersApi } from "@/lib/api/members";

/** 화면 표시용 가드. 실제 권한 검사는 백엔드 require_admin 이 한다. */
export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"loading" | "ok" | "denied">("loading");

  useEffect(() => {
    membersApi.me().then((m) => setState(m.role === "ADMIN" ? "ok" : "denied")).catch(() => setState("denied"));
  }, []);

  if (state === "loading") return <p className="text-sm text-slate-500">권한 확인 중…</p>;
  if (state === "denied")
    return <p className="text-sm">관리자만 접근할 수 있습니다. <Link href="/login" className="text-blue-600 underline">로그인</Link></p>;
  return <>{children}</>;
}
