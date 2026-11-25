"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field, Notice, PasswordInput, fieldProps, formatPhone } from "@/components/FormField";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";

const EMPTY = { loginId: "", password: "", confirm: "", name: "", email: "", phone: "" };
type Key = keyof typeof EMPTY;

// 서버(SignupRequest)와 같은 규칙. 서버가 다시 검사하므로 여기는 미리 알려 주는 용도
function check(f: typeof EMPTY): Partial<Record<Key, string>> {
  const e: Partial<Record<Key, string>> = {};
  if (!/^[A-Za-z0-9_]{4,20}$/.test(f.loginId.trim())) e.loginId = "영문 · 숫자 · _ 4~20자로 적어 주세요.";
  if (f.password.length < 8) e.password = "8자 이상 적어 주세요.";
  else if (f.password.length > 64) e.password = "64자까지 쓸 수 있어요.";
  if (!f.confirm) e.confirm = "비밀번호를 한 번 더 적어 주세요.";
  else if (f.confirm !== f.password) e.confirm = "비밀번호가 서로 달라요.";
  if (!f.name.trim()) e.name = "이름을 적어 주세요.";
  else if (f.name.trim().length > 50) e.name = "50자까지 쓸 수 있어요.";
  if (f.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim())) e.email = "이메일 형식이 아니에요. 예: guest@example.com";
  if (!f.phone.trim()) e.phone = "전화번호를 적어 주세요.";
  else if (!/^[0-9-]{9,20}$/.test(f.phone.trim())) e.phone = "전화번호를 끝까지 적어 주세요. 예: 010-1234-5678";
  return e;
}

export default function SignupForm() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [touched, setTouched] = useState<Partial<Record<Key, boolean>>>({});
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  // 중복확인 결과. 확인한 아이디(checkedId)와 지금 입력이 다르면 다시 확인해야 한다
  const [idCheck, setIdCheck] = useState<{ checkedId: string; available: boolean; message: string } | null>(null);
  const loginId = form.loginId.trim();
  const idChecked = idCheck?.available && idCheck.checkedId === loginId;
  const idResult = idCheck && idCheck.checkedId === loginId ? idCheck : null;

  const errors = check(form);
  const shown = (k: Key) => (submitted || touched[k] ? errors[k] : undefined);
  const bind = (k: Key) => ({
    value: form[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm({ ...form, [k]: k === "phone" ? formatPhone(e.target.value) : e.target.value }),
    onBlur: () => setTouched((t) => ({ ...t, [k]: true })),
  });

  async function checkId() {
    setTouched((t) => ({ ...t, loginId: true }));
    if (errors.loginId) return;
    try {
      setIdCheck({ checkedId: loginId, ...(await membersApi.checkId(loginId)) });
    } catch (err) {
      setIdCheck({ checkedId: loginId, available: false, message: (err as ApiError).message });
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    setError("");
    if (Object.keys(errors).length) return;
    if (!idChecked) {
      setError("아이디 중복확인을 해 주세요.");
      return;
    }
    try {
      await membersApi.signup({
        loginId,
        password: form.password,
        name: form.name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim() || undefined,
      });
      // cacheComponents 는 이전 화면 상태를 유지하므로 비밀번호가 남지 않게 비운다
      setForm(EMPTY);
      setIdCheck(null);
      router.push("/login?done=joined");
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  const idError = shown("loginId") ?? (idResult && !idResult.available ? idResult.message : undefined);
  const idHint = idResult?.available
    ? <span className="text-emerald-600">✓ {idResult.message}</span>
    : "영문 · 숫자 · _ 4~20자. 적은 뒤 중복확인을 눌러 주세요.";

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      {error && <Notice tone="error">{error}</Notice>}

      <Field id="su-id" label="아이디" hint={idHint} error={idError}>
        <div className="flex gap-2">
          <input {...fieldProps("su-id", idError)} {...bind("loginId")} autoComplete="username" maxLength={20} />
          <button type="button" onClick={checkId} disabled={Boolean(idChecked)} className="btn-outline shrink-0">
            {idChecked ? "확인됨" : "중복확인"}
          </button>
        </div>
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="su-pw" label="비밀번호" hint="8~64자" error={shown("password")}>
          <PasswordInput {...fieldProps("su-pw", shown("password"))} {...bind("password")} autoComplete="new-password" />
        </Field>
        <Field id="su-pw2" label="비밀번호 확인" hint={form.confirm && !errors.confirm ? <span className="text-emerald-600">✓ 같아요</span> : " "} error={shown("confirm")}>
          <PasswordInput {...fieldProps("su-pw2", shown("confirm"))} {...bind("confirm")} autoComplete="new-password" />
        </Field>
      </div>

      <Field id="su-name" label="이름" error={shown("name")}>
        <input {...fieldProps("su-name", shown("name"), Boolean(shown("name")))} {...bind("name")} autoComplete="name" maxLength={50} />
      </Field>

      <Field id="su-email" label="이메일" optional hint="예약 안내를 받을 때 써요." error={shown("email")}>
        <input {...fieldProps("su-email", shown("email"))} {...bind("email")} type="email" autoComplete="email" maxLength={100} />
      </Field>

      <Field id="su-phone" label="전화번호" hint="숫자만 쓰면 - 는 자동으로 들어가요. 예: 010-1234-5678" error={shown("phone")}>
        <input {...fieldProps("su-phone", shown("phone"))} {...bind("phone")} type="tel" inputMode="numeric" autoComplete="tel" maxLength={13} />
      </Field>

      <button className="btn-primary w-full py-2.5">가입하기</button>
      <p className="text-center text-sm text-slate-500">
        이미 회원이신가요? <Link href="/login" className="font-medium text-blue-600 hover:underline">로그인</Link>
      </p>
    </form>
  );
}
