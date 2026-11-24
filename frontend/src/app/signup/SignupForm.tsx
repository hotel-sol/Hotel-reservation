"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";

export default function SignupForm() {
  const router = useRouter();
  const [form, setForm] = useState({ loginId: "", password: "", name: "", phone: "", email: "" });
  const [error, setError] = useState("");
  // 중복확인 결과. 확인한 아이디(checkedId)와 지금 입력이 다르면 다시 확인해야 한다
  const [idCheck, setIdCheck] = useState<{ checkedId: string; available: boolean; message: string } | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  const idChecked = idCheck?.available && idCheck.checkedId === form.loginId.trim();

  async function checkId() {
    const loginId = form.loginId.trim();
    if (!loginId) return setIdCheck({ checkedId: "", available: false, message: "아이디를 입력해 주세요." });
    try {
      setIdCheck({ checkedId: loginId, ...(await membersApi.checkId(loginId)) });
    } catch (err) {
      setIdCheck({ checkedId: loginId, available: false, message: (err as ApiError).message });
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!idChecked) {
      setError("아이디 중복확인을 해 주세요.");
      return;
    }
    try {
      await membersApi.signup({ ...form, phone: form.phone || undefined, email: form.email || undefined });
      // cacheComponents 는 이전 화면 상태를 유지하므로 비밀번호가 남지 않게 비운다
      setForm({ loginId: "", password: "", name: "", phone: "", email: "" });
      setIdCheck(null);
      alert("가입되었습니다. 로그인해 주세요.");
      router.push("/login");
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <div className="flex gap-2">
        <input className="input" placeholder="아이디 (영문·숫자·_ 4자 이상)" value={form.loginId} onChange={set("loginId")} required />
        <button type="button" onClick={checkId} className="shrink-0 rounded-lg border border-slate-300 bg-white px-3 text-sm hover:bg-slate-50">
          중복확인
        </button>
      </div>
      {idCheck && idCheck.checkedId === form.loginId.trim() && (
        <p className={`text-sm ${idCheck.available ? "text-green-600" : "text-red-600"}`}>{idCheck.message}</p>
      )}
      <input className="input" type="password" placeholder="비밀번호 (8자 이상)" value={form.password} onChange={set("password")} required minLength={8} />
      <input className="input" placeholder="이름" value={form.name} onChange={set("name")} required />
      <input className="input" placeholder="전화번호 (선택)" value={form.phone} onChange={set("phone")} />
      <input className="input" type="email" placeholder="이메일 (선택)" value={form.email} onChange={set("email")} />
      {error && <p className="whitespace-pre-line text-sm text-red-600">{error}</p>}
      <button className="btn-primary w-full">가입하기</button>
    </form>
  );
}
