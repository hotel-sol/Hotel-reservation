"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Field, Notice, PasswordInput, fieldProps } from "@/components/FormField";
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

// 다른 화면에서 끝내고 넘어올 때 보여 줄 안내(?done=)
const DONE: Record<string, string> = {
  joined: "가입이 끝났어요. 로그인해 주세요.",
};

export default function LoginForm() {
  const params = useSearchParams();
  const next = params.get("next");
  const done = DONE[params.get("done") ?? ""];
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
    <form onSubmit={submit} className="space-y-4">
      {done && !error && <Notice tone="ok">{done}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      <Field id="login-id" label="아이디">
        <input {...fieldProps("login-id", undefined, false)} value={loginId} onChange={(e) => setLoginId(e.target.value)}
          required autoComplete="username" autoFocus />
      </Field>
      <Field id="login-password" label="비밀번호" hint="5번 틀리면 10분 동안 로그인할 수 없어요.">
        <PasswordInput {...fieldProps("login-password")} value={password} onChange={(e) => setPassword(e.target.value)}
          required autoComplete="current-password" />
      </Field>
      <button className="btn-primary w-full py-2.5">로그인</button>
      <div className="flex flex-wrap justify-between gap-2 text-sm text-slate-500">
        <span>아직 회원이 아니신가요? <Link href="/signup" className="font-medium text-blue-600 hover:underline">회원가입</Link></span>
        <Link href="/password-reset" className="hover:underline">비밀번호 찾기</Link>
      </div>
    </form>
  );
}
