"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";

/** next 가 우리 사이트 안의 주소면 검사한 전체 주소(href)를, 아니면 null.
 *  경로만 꺼내면 "/.//evil.com" → "//evil.com" 처럼 다시 외부 주소가 되므로 href 를 그대로 쓴다 */
function internalUrl(next: string | null): string | null {
  if (!next) return null;
  try {
    const url = new URL(next, window.location.origin);
    return url.origin === window.location.origin ? url.href : null;
  } catch {
    return null;
  }
}

export default function LoginForm() {
  const next = useSearchParams().get("next");
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const me = await membersApi.login(loginId, password);
      setPassword(""); // 이전 화면 상태 유지(Activity) 대비
      // 오픈 리다이렉트 방지: 브라우저와 같은 방식으로 주소를 풀어서 우리 사이트일 때만 허용.
      // 글자 검사(startsWith("/"))는 "/\evil.com" · "/<탭>/evil.com" 같은 외부 주소를 통과시킨다
      const safeNext = internalUrl(next);
      // 페이지 전체를 새로 읽는다(router.push 아님): 숨겨 둔 화면(Activity)에 로그인 전 상태가 남지 않게
      window.location.assign(safeNext ?? (me.role === "ADMIN" ? "/admin/reservations" : "/rooms"));
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
        <span className="mx-2 text-slate-300">|</span>
        <Link href="/password-reset" className="text-blue-600">비밀번호 찾기</Link>
      </p>
    </form>
  );
}
