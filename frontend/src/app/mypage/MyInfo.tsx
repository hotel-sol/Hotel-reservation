"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { membersApi } from "@/lib/api/members";
import type { Member } from "@/types/api";

export default function MyInfo() {
  const [me, setMe] = useState<Member | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    membersApi.me().then(setMe).catch(setError);
  }, []);

  if (error) return <p className="text-sm">로그인이 필요합니다. <Link href="/login?next=/mypage" className="text-blue-600 underline">로그인</Link></p>;
  if (!me) return <p className="text-sm text-slate-500">불러오는 중…</p>;

  return (
    <div className="card max-w-lg text-sm">
      <dl className="grid grid-cols-[100px_1fr] gap-y-2">
        <dt className="text-slate-500">아이디</dt><dd>{me.loginId}</dd>
        <dt className="text-slate-500">이름</dt><dd>{me.name}</dd>
        <dt className="text-slate-500">전화번호</dt><dd>{me.phone ?? "-"}</dd>
        <dt className="text-slate-500">이메일</dt><dd>{me.email ?? "-"}</dd>
      </dl>
      {/* TODO: 내 정보 수정, 비밀번호 변경, 탈퇴 */}
    </div>
  );
}
