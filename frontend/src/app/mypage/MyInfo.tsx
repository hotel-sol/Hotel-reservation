"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Field, Notice, PasswordInput, fieldProps, formatPhone } from "@/components/FormField";
import { ApiError } from "@/lib/api/client";
import { membersApi, type ProfileInput } from "@/lib/api/members";
import type { Member } from "@/types/api";

type Msg = { ok: boolean; text: string } | null;

/** 마이페이지: 내 정보 보기 · 수정, 비밀번호 변경, 탈퇴 */
export default function MyInfo() {
  const [me, setMe] = useState<Member | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let ignore = false;
    membersApi
      .me()
      .then((m) => { if (!ignore) setMe(m); })
      .catch((e: ApiError) => { if (!ignore) setError(e); });
    return () => { ignore = true; };
  }, []);

  if (error) {
    return (
      <div className="card mx-auto max-w-md space-y-3 text-center text-sm">
        <p className="text-4xl" aria-hidden="true">🔒</p>
        <p>마이페이지는 로그인한 뒤에 볼 수 있어요.</p>
        <Link href="/login?next=/mypage" className="btn-primary">로그인하기</Link>
      </div>
    );
  }
  if (!me) return <p className="text-sm text-slate-500">불러오는 중…</p>;

  const admin = me.role === "ADMIN";
  return (
    <div className="space-y-4">
      {/* ---------- 인사 · 바로가기 ---------- */}
      <section className="card flex flex-wrap items-center gap-4">
        <div aria-hidden="true" className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-xl font-bold text-blue-700">
          {me.name.slice(0, 1)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-lg font-semibold">
            {me.name}님
            <span className={`ml-2 rounded-full px-2 py-0.5 align-middle text-xs font-medium ${admin ? "bg-slate-800 text-white" : "bg-blue-50 text-blue-700"}`}>
              {admin ? "관리자" : "회원"}
            </span>
          </p>
          <p className="text-sm text-slate-500">아이디 {me.loginId}</p>
        </div>
        <div className="flex gap-2">
          {admin ? (
            <Link href="/admin" className="btn-outline">관리자 페이지</Link>
          ) : (
            <>
              <Link href="/reservation/list" className="btn-outline">내 예약</Link>
              <Link href="/rooms" className="btn-primary">객실 찾기</Link>
            </>
          )}
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <ProfileCard me={me} onSaved={setMe} />
        <div className="space-y-4">
          <PasswordCard />
          {!admin && <WithdrawCard />}
        </div>
      </div>
    </div>
  );
}

function ProfileCard({ me, onSaved }: { me: Member; onSaved: (m: Member) => void }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ProfileInput>({ name: me.name, phone: me.phone, email: me.email });
  const [msg, setMsg] = useState<Msg>(null);

  function start() {
    setForm({ name: me.name, phone: me.phone, email: me.email });
    setMsg(null);
    setEditing(true);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      // 빈 칸은 백엔드에서 NULL 로 저장
      onSaved(await membersApi.updateMe(form));
      setEditing(false);
      setMsg({ ok: true, text: "저장했어요." });
    } catch (err) {
      setMsg({ ok: false, text: (err as ApiError).message });
    }
  }

  const set = (k: keyof ProfileInput) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <section className="card h-fit space-y-4 text-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">내 정보</h2>
        {!editing && <button type="button" className="btn-outline py-1" onClick={start}>수정</button>}
      </div>
      {msg && <Notice tone={msg.ok ? "ok" : "error"}>{msg.text}</Notice>}
      {editing ? (
        <form onSubmit={save} className="space-y-4">
          <Field id="me-id" label="아이디" hint="아이디는 바꿀 수 없어요.">
            <input {...fieldProps("me-id")} value={me.loginId} disabled className="input bg-slate-50 text-slate-500" />
          </Field>
          <Field id="me-name" label="이름">
            <input {...fieldProps("me-name", undefined, false)} value={form.name} onChange={set("name")} required maxLength={50} autoComplete="name" />
          </Field>
          <Field id="me-phone" label="전화번호" optional hint="숫자만 쓰면 - 는 자동으로 들어가요.">
            <input {...fieldProps("me-phone")} type="tel" inputMode="numeric" value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: formatPhone(e.target.value) })} maxLength={13} autoComplete="tel" />
          </Field>
          <Field id="me-email" label="이메일" optional hint="예약 안내를 받을 때 써요.">
            <input {...fieldProps("me-email")} type="email" value={form.email ?? ""} onChange={set("email")} maxLength={100} autoComplete="email" />
          </Field>
          <div className="flex gap-2">
            <button className="btn-primary flex-1">저장</button>
            <button type="button" className="btn-outline flex-1" onClick={() => setEditing(false)}>취소</button>
          </div>
        </form>
      ) : (
        <dl className="divide-y divide-slate-100">
          {[
            ["아이디", me.loginId],
            ["이름", me.name],
            ["전화번호", me.phone],
            ["이메일", me.email],
          ].map(([k, v]) => (
            <div key={k} className="grid grid-cols-[88px_1fr] py-2.5">
              <dt className="text-slate-500">{k}</dt>
              <dd className={v ? "" : "text-slate-400"}>{v || "등록 안 함"}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function PasswordCard() {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [msg, setMsg] = useState<Msg>(null);
  const mismatch = form.confirm !== "" && form.confirm !== form.next ? "비밀번호가 서로 달라요." : undefined;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (form.next !== form.confirm) {
      setMsg({ ok: false, text: "새 비밀번호가 서로 다릅니다." });
      return;
    }
    try {
      await membersApi.changePassword(form.current, form.next);
      setMsg({ ok: true, text: "비밀번호를 바꿨어요. 다른 기기에서는 다시 로그인해야 해요." });
    } catch (err) {
      setMsg({ ok: false, text: (err as ApiError).message });
    } finally {
      setForm({ current: "", next: "", confirm: "" }); // 화면 상태가 남지 않게 비운다
    }
  }

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <form onSubmit={submit} className="card space-y-4 text-sm">
      <h2 className="text-base font-semibold">비밀번호 변경</h2>
      {msg && <Notice tone={msg.ok ? "ok" : "error"}>{msg.text}</Notice>}
      <Field id="pw-current" label="현재 비밀번호">
        <PasswordInput {...fieldProps("pw-current", undefined, false)} value={form.current} onChange={set("current")}
          required autoComplete="current-password" />
      </Field>
      <Field id="pw-next" label="새 비밀번호" hint="8자 이상">
        <PasswordInput {...fieldProps("pw-next")} value={form.next} onChange={set("next")}
          required minLength={8} maxLength={100} autoComplete="new-password" />
      </Field>
      <Field id="pw-confirm" label="새 비밀번호 확인" error={mismatch}>
        <PasswordInput {...fieldProps("pw-confirm", mismatch, Boolean(mismatch))} value={form.confirm} onChange={set("confirm")}
          required minLength={8} maxLength={100} autoComplete="new-password" />
      </Field>
      <button className="btn-primary w-full">비밀번호 변경</button>
    </form>
  );
}

function WithdrawCard() {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!confirm("탈퇴하면 되돌릴 수 없습니다. 탈퇴할까요?")) return;
    try {
      await membersApi.withdraw(password);
      alert("탈퇴했습니다. 이용해 주셔서 감사합니다.");
      // 페이지 전체를 새로 읽는다: 상단 메뉴 등에 로그인 상태가 남지 않게(로그인 · 로그아웃과 같은 방식)
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- 의도적인 하드 이동
      window.location.assign("/rooms");
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setPassword("");
    }
  }

  return (
    <section className="card space-y-3 text-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">회원 탈퇴</h2>
        {!open && <button type="button" className="text-sm text-slate-500 hover:text-red-600 hover:underline" onClick={() => setOpen(true)}>탈퇴하기</button>}
      </div>
      <p className="text-slate-500">진행 중인 예약이 있으면 먼저 취소해야 탈퇴할 수 있어요.</p>
      {open && (
        <form onSubmit={submit} className="space-y-3">
          {error && <Notice tone="error">{error}</Notice>}
          <Field id="wd-pw" label="비밀번호 확인">
            <PasswordInput {...fieldProps("wd-pw", undefined, false)} value={password} onChange={(e) => setPassword(e.target.value)}
              required autoComplete="current-password" />
          </Field>
          <div className="flex gap-2">
            <button className="btn flex-1 border border-red-300 bg-white text-red-600 hover:bg-red-50">탈퇴</button>
            <button type="button" className="btn-outline flex-1" onClick={() => { setOpen(false); setError(""); }}>취소</button>
          </div>
        </form>
      )}
    </section>
  );
}
