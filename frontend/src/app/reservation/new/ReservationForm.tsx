"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { reservationsApi } from "@/lib/api/reservations";
import { roomsApi } from "@/lib/api/rooms";
import { nightsBetween, today, won } from "@/lib/format";
import type { Room } from "@/types/api";

export default function ReservationForm() {
  const router = useRouter();
  const params = useSearchParams();
  const roomId = Number(params.get("roomId"));

  const [room, setRoom] = useState<Room | null>(null);
  const [form, setForm] = useState({
    checkInDate: params.get("checkIn") ?? "",
    checkOutDate: params.get("checkOut") ?? "",
    guestCount: Number(params.get("guests") ?? 1),
    requestMemo: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (roomId) roomsApi.get(roomId).then(setRoom).catch((e: ApiError) => setError(e.message));
  }, [roomId]);

  if (!roomId) {
    return (
      <p className="text-sm">
        객실을 먼저 선택하세요. <Link href="/rooms" className="text-blue-600 underline">객실 추천으로 →</Link>
      </p>
    );
  }

  const nights = form.checkInDate && form.checkOutDate ? nightsBetween(form.checkInDate, form.checkOutDate) : 0;
  const total = room ? room.price * nights : 0;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!confirm(`${room?.roomName} ${nights}박, ${won(total)} 예약할까요?`)) return;
    setSubmitting(true);
    try {
      const r = await reservationsApi.create({ roomId, ...form, requestMemo: form.requestMemo || undefined });
      router.push(`/reservation/${r.reservationId}/complete`);
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 401) router.push(`/login?next=${encodeURIComponent(location.pathname + location.search)}`);
      else setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_360px]">
      <form onSubmit={submit} className="card space-y-4">
        {/* TODO(RSV-001): /rooms/{id}/available-dates 로 휴무일·예약된 날짜 비활성화 달력 */}
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            체크인
            <input type="date" required className="input mt-1" min={today()} value={form.checkInDate}
              onChange={(e) => setForm({ ...form, checkInDate: e.target.value })} />
          </label>
          <label className="text-sm">
            체크아웃
            <input type="date" required className="input mt-1" min={form.checkInDate || today()} value={form.checkOutDate}
              onChange={(e) => setForm({ ...form, checkOutDate: e.target.value })} />
          </label>
        </div>
        <label className="block text-sm">
          인원
          <input type="number" required min={1} max={room?.maxGuest} className="input mt-1" value={form.guestCount}
            onChange={(e) => setForm({ ...form, guestCount: Number(e.target.value) })} />
        </label>
        <label className="block text-sm">
          요청 사항 <span className="text-slate-400">({form.requestMemo.length}/200)</span>
          <textarea maxLength={200} rows={3} className="input mt-1" value={form.requestMemo}
            onChange={(e) => setForm({ ...form, requestMemo: e.target.value })} />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn-primary w-full" disabled={submitting || nights < 1}>
          예약하기
        </button>
      </form>

      <aside className="card h-fit space-y-2 text-sm">
        <div className="flex h-32 items-center justify-center rounded-lg bg-slate-100 text-4xl">🛏️</div>
        <h2 className="text-lg font-semibold">{room?.roomName ?? "…"}</h2>
        <p className="text-slate-500">{room?.description}</p>
        <p>1박 {room ? won(room.price) : "-"} · 최대 {room?.maxGuest}명</p>
        <hr className="border-slate-200" />
        <p className="flex justify-between">
          <span>{nights}박</span>
          <strong className="text-lg">{won(total)}</strong>
        </p>
      </aside>
    </div>
  );
}
