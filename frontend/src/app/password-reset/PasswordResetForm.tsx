"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";

const EMPTY = { loginId: "", email: "", newPassword: "", confirm: "" };

export default function PasswordResetForm() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (form.newPassword !== form.confirm) {
      setError("새 비밀번호가 서로 다릅니다.");
      return;
    }
    try {
      await membersApi.resetPassword({ loginId: form.loginId, email: form.email, newPassword: form.newPassword });
      setForm(EMPTY); // 이전 화면 상태 유지(Activity) 대비
      alert("비밀번호를 바꿨습니다. 새 비밀번호로 로그인해 주세요.");
      router.push("/login");
    } catch (err) {
      setError((err as ApiError).message); // 5번 틀리면 10분 잠금
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <input className="input" placeholder="아이디" value={form.loginId} onChange={set("loginId")} required autoComplete="username" />
      <input className="input" type="email" placeholder="가입한 이메일" value={form.email} onChange={set("email")} required />
      <input className="input" type="password" placeholder="새 비밀번호 (8자 이상)" value={form.newPassword}
        onChange={set("newPassword")} required minLength={8} maxLength={100} autoComplete="new-password" />
      <input className="input" type="password" placeholder="새 비밀번호 확인" value={form.confirm}
        onChange={set("confirm")} required minLength={8} maxLength={100} autoComplete="new-password" />
      {error && <p className="whitespace-pre-line text-sm text-red-600">{error}</p>}
      <button className="btn-primary w-full">비밀번호 바꾸기</button>
      <p className="text-center text-sm text-slate-500">
        <Link href="/login" className="text-blue-600">로그인으로 돌아가기</Link>
      </p>
    </form>
  );
}
