"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field, Notice, PasswordInput, fieldProps } from "@/components/FormField";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";

const EMPTY = { loginId: "", email: "", newPassword: "", confirm: "" };

export default function PasswordResetForm() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });
  const mismatch = form.confirm !== "" && form.confirm !== form.newPassword ? "비밀번호가 서로 달라요." : undefined;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (form.newPassword !== form.confirm) {
      setError("새 비밀번호가 서로 다릅니다.");
      return;
    }
    try {
      await membersApi.resetPassword({ loginId: form.loginId, email: form.email, newPassword: form.newPassword });
      setForm(EMPTY); // 이전 화면 상태 유지(Activity) 대비
      router.push("/login?done=reset");
    } catch (err) {
      setError((err as ApiError).message); // 5번 틀리면 10분 잠금
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      {error && <Notice tone="error">{error}</Notice>}
      <Field id="pr-id" label="아이디">
        <input {...fieldProps("pr-id", undefined, false)} value={form.loginId} onChange={set("loginId")} required autoComplete="username" />
      </Field>
      <Field id="pr-email" label="가입한 이메일" hint="가입할 때 이메일을 적지 않았다면 관리자에게 문의해 주세요.">
        <input {...fieldProps("pr-email")} type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="pr-pw" label="새 비밀번호" hint="8자 이상">
          <PasswordInput {...fieldProps("pr-pw")} value={form.newPassword} onChange={set("newPassword")}
            required minLength={8} maxLength={100} autoComplete="new-password" />
        </Field>
        <Field id="pr-pw2" label="새 비밀번호 확인" hint=" " error={mismatch}>
          <PasswordInput {...fieldProps("pr-pw2", mismatch)} value={form.confirm} onChange={set("confirm")}
            required minLength={8} maxLength={100} autoComplete="new-password" />
        </Field>
      </div>
      <button className="btn-primary w-full py-2.5">비밀번호 바꾸기</button>
      <p className="text-center text-sm text-slate-500">
        비밀번호가 생각났나요? <Link href="/login" className="font-medium text-blue-600 hover:underline">로그인</Link>
      </p>
    </form>
  );
}
