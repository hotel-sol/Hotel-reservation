"use client";

import { useState, type InputHTMLAttributes, type ReactNode } from "react";

/** 칸 위 이름표 + 칸 + 칸 아래 안내(틀리면 빨간 오류). 1번 회원 화면에서 쓴다 */
export function Field({
  id,
  label,
  optional,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  optional?: boolean;
  hint?: ReactNode;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
        {optional && <span className="ml-1 text-xs font-normal text-slate-400">(선택)</span>}
      </label>
      {children}
      {error ? (
        <p id={`${id}-msg`} className="text-xs text-red-600" role="alert">{error}</p>
      ) : hint ? (
        <p id={`${id}-msg`} className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  );
}

/** 칸 공통 속성: 오류면 빨간 테두리 + 스크린 리더에 알림 */
export function fieldProps(id: string, error?: string, hasMsg = true) {
  return {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": hasMsg ? `${id}-msg` : undefined,
    className: `input ${error ? "border-red-500 ring-2 ring-red-100" : ""}`,
  };
}

/** 비밀번호 칸 + 보기/숨기기 */
export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input {...props} type={show ? "text" : "password"} className={`${props.className ?? "input"} pr-14`} />
      <button type="button" onClick={() => setShow((s) => !s)} aria-pressed={show}
        aria-label={show ? "비밀번호 숨기기" : "비밀번호 보기"}
        className="absolute inset-y-0 right-0 px-3 text-xs text-slate-500 hover:text-slate-800">
        {show ? "숨기기" : "보기"}
      </button>
    </div>
  );
}

/** 전화번호: 숫자만 남기고 "-"를 자동으로 넣는다. 010-1234-5678 · 02-123-4567 · 031-123-4567 */
export function formatPhone(value: string): string {
  const d = value.replace(/\D/g, "").slice(0, 11);
  const [a, b] = d.startsWith("02") ? [2, d.length > 9 ? 4 : 3] : [3, d.length > 10 ? 4 : 3];
  if (d.length <= a) return d;
  if (d.length <= a + b) return `${d.slice(0, a)}-${d.slice(a)}`;
  return `${d.slice(0, a)}-${d.slice(a, a + b)}-${d.slice(a + b)}`;
}

/** 화면 위쪽 알림 상자(성공 · 오류) */
export function Notice({ tone, children }: { tone: "ok" | "error"; children: ReactNode }) {
  const color = tone === "ok" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-700";
  return (
    <p role={tone === "error" ? "alert" : "status"} className={`whitespace-pre-line rounded-md border px-3 py-2 text-sm ${color}`}>
      {children}
    </p>
  );
}
