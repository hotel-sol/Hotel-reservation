"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import { ApiError } from "@/lib/api/client";
import { reservationsApi } from "@/lib/api/reservations";
import { won } from "@/lib/format";
import type { Reservation } from "@/types/api";

export default function ReservationComplete() {
  const { reservationId } = useParams<{ reservationId: string }>();
  const [r, setR] = useState<Reservation | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    reservationsApi.get(Number(reservationId)).then(setR).catch((e: ApiError) => setError(e.message));
  }, [reservationId]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!r) return <p className="text-sm text-slate-500">불러오는 중…</p>;

  return (
    <div className="card max-w-lg space-y-3 text-sm">
      <p className="text-center text-4xl">✅</p>
      <dl className="grid grid-cols-[100px_1fr] gap-y-2">
        <dt className="text-slate-500">예약 번호</dt><dd>{r.reservationId}</dd>
        <dt className="text-slate-500">객실</dt><dd>{r.roomName}</dd>
        <dt className="text-slate-500">일정</dt><dd>{r.checkInDate} ~ {r.checkOutDate}</dd>
        <dt className="text-slate-500">인원</dt><dd>{r.guestCount}명</dd>
        <dt className="text-slate-500">금액</dt><dd className="font-semibold">{won(r.totalPrice)}</dd>
        <dt className="text-slate-500">상태</dt><dd><StatusBadge status={r.status} /></dd>
      </dl>
      <div className="flex gap-2 pt-2">
        <Link href="/rooms" className="btn-outline flex-1">홈으로</Link>
        <Link href="/reservation/list" className="btn-primary flex-1">내 예약 보기</Link>
      </div>
    </div>
  );
}
