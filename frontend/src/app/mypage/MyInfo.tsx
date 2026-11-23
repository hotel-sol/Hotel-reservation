"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { membersApi, type ProfileInput } from "@/lib/api/members";
import type { Member } from "@/types/api";

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

  if (error) return <p className="text-sm">로그인이 필요합니다. <Link href="/login?next=/mypage" className="text-blue-600 underline">로그인</Link></p>;
  if (!me) return <p className="text-sm text-slate-500">불러오는 중…</p>;

  return (
    <div className="grid max-w-3xl gap-4 md:grid-cols-2">
      <ProfileCard me={me} onSaved={setMe} />
      <div className="space-y-4">
        <PasswordCard />
        {me.role !== "ADMIN" && <WithdrawCard />}
      </div>
    </div>
  );
}

function ProfileCard({ me, onSaved }: { me: Member; onSaved: (m: Member) => void }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ProfileInput>({ name: me.name, phone: me.phone, email: me.email });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

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
      setMsg({ ok: true, text: "저장했습니다." });
    } catch (err) {
      setMsg({ ok: false, text: (err as ApiError).message });
    }
  }

  const set = (k: keyof ProfileInput) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <div className="card space-y-3 text-sm">
      <h2 className="font-semibold">내 정보</h2>
      {editing ? (
        <form onSubmit={save} className="space-y-3">
          <p className="text-slate-500">아이디 {me.loginId} (바꿀 수 없음)</p>
          <input className="input" placeholder="이름" value={form.name} onChange={set("name")} required maxLength={50} />
          <input className="input" placeholder="전화번호 (숫자와 -)" value={form.phone ?? ""} onChange={set("phone")} maxLength={20} />
          <input className="input" type="email" placeholder="이메일" value={form.email ?? ""} onChange={set("email")} maxLength={100} />
          {msg && <p className={`whitespace-pre-line ${msg.ok ? "text-green-700" : "text-red-600"}`}>{msg.text}</p>}
          <div className="flex gap-2">
            <button className="btn-primary flex-1">저장</button>
            <button type="button" className="btn-outline flex-1" onClick={() => setEditing(false)}>취소</button>
          </div>
        </form>
      ) : (
        <>
          <dl className="grid grid-cols-[80px_1fr] gap-y-2">
            <dt className="text-slate-500">아이디</dt><dd>{me.loginId}</dd>
            <dt className="text-slate-500">이름</dt><dd>{me.name}</dd>
            <dt className="text-slate-500">전화번호</dt><dd>{me.phone ?? "-"}</dd>
            <dt className="text-slate-500">이메일</dt><dd>{me.email ?? "-"}</dd>
          </dl>
          {msg && <p className="text-green-700">{msg.text}</p>}
          <button type="button" className="btn-outline w-full" onClick={start}>정보 수정</button>
        </>
      )}
    </div>
  );
}

function PasswordCard() {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (form.next !== form.confirm) {
      setMsg({ ok: false, text: "새 비밀번호가 서로 다릅니다." });
      return;
    }
    try {
      await membersApi.changePassword(form.current, form.next);
      setMsg({ ok: true, text: "비밀번호를 바꿨습니다. 다른 기기에서는 다시 로그인해야 합니다." });
    } catch (err) {
      setMsg({ ok: false, text: (err as ApiError).message });
    } finally {
      setForm({ current: "", next: "", confirm: "" }); // 화면 상태가 남지 않게 비운다
    }
  }

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  return (
    <form onSubmit={submit} className="card space-y-3 text-sm">
      <h2 className="font-semibold">비밀번호 변경</h2>
      <input className="input" type="password" placeholder="현재 비밀번호" value={form.current} onChange={set("current")}
        required autoComplete="current-password" />
      <input className="input" type="password" placeholder="새 비밀번호 (8자 이상)" value={form.next} onChange={set("next")}
        required minLength={8} maxLength={100} autoComplete="new-password" />
      <input className="input" type="password" placeholder="새 비밀번호 확인" value={form.confirm} onChange={set("confirm")}
        required minLength={8} maxLength={100} autoComplete="new-password" />
      {msg && <p className={`whitespace-pre-line ${msg.ok ? "text-green-700" : "text-red-600"}`}>{msg.text}</p>}
      <button className="btn-primary w-full">비밀번호 변경</button>
    </form>
  );
}

function WithdrawCard() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!confirm("탈퇴하면 되돌릴 수 없습니다. 탈퇴할까요?")) return;
    try {
      await membersApi.withdraw(password);
      alert("탈퇴했습니다. 이용해 주셔서 감사합니다.");
      router.push("/rooms");
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setPassword("");
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3 text-sm">
      <h2 className="font-semibold">회원 탈퇴</h2>
      <p className="text-slate-500">진행 중인 예약이 있으면 먼저 취소해야 탈퇴할 수 있어요.</p>
      <input className="input" type="password" placeholder="비밀번호 확인" value={password}
        onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
      {error && <p className="whitespace-pre-line text-red-600">{error}</p>}
      <button className="btn-outline w-full text-red-600">탈퇴하기</button>
    </form>
  );
}
