"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import StatusBadge from "@/components/StatusBadge";
import { ApiError } from "@/lib/api/client";
import { reservationsApi } from "@/lib/api/reservations";
import { won } from "@/lib/format";
import type { Reservation } from "@/types/api";

export default function MyReservations() {
  const [rows, setRows] = useState<Reservation[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    reservationsApi.mine().then(setRows).catch(setError);
  }, []);

  if (error?.status === 401)
    return <p className="text-sm">로그인이 필요합니다. <Link href="/login?next=/reservation/list" className="text-blue-600 underline">로그인</Link></p>;
  if (error) return <p className="text-sm text-red-600">{error.message}</p>;
  if (!rows) return <p className="text-sm text-slate-500">불러오는 중…</p>;
  if (rows.length === 0) return <p className="text-sm text-slate-500">예약 내역이 없습니다.</p>;

  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.reservationId} className="card flex items-center justify-between text-sm">
          <div>
            <p className="font-semibold">#{r.reservationId} {r.roomName}</p>
            <p className="text-slate-500">{r.checkInDate} ~ {r.checkOutDate} · {r.guestCount}명</p>
          </div>
          <div className="flex items-center gap-3">
            <span>{won(r.totalPrice)}</span>
            <StatusBadge status={r.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
