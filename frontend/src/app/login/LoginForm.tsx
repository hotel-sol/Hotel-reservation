"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";

export default function LoginForm() {
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const me = await membersApi.login(loginId, password);
      setPassword(""); // 이전 화면 상태 유지(Activity) 대비
      // 오픈 리다이렉트 방지: 내부 경로만 허용
      const safeNext = next?.startsWith("/") && !next.startsWith("//") ? next : null;
      router.push(safeNext ?? (me.role === "ADMIN" ? "/admin/reservations" : "/rooms"));
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <input className="input" placeholder="아이디" value={loginId} onChange={(e) => setLoginId(e.target.value)} required />
      <input className="input" type="password" placeholder="비밀번호" value={password}
        onChange={(e) => setPassword(e.target.value)} required />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button className="btn-primary w-full">로그인</button>
      <p className="text-center text-sm text-slate-500">
        계정이 없나요? <Link href="/signup" className="text-blue-600">회원가입</Link>
      </p>
    </form>
  );
}
