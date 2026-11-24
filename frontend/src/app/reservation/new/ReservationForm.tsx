"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { reservationsApi } from "@/lib/api/reservations";
import { roomsApi } from "@/lib/api/rooms";
import { won } from "@/lib/format";
import type { Quote, Room } from "@/types/api";
import StayCalendar, { addDays, dayLabel, lastCheckout, useRoomCalendar } from "./StayCalendar";

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

  const cal = useRoomCalendar(roomId);

  useEffect(() => {
    if (roomId) roomsApi.get(roomId).then(setRoom).catch((e: ApiError) => setError(e.message));
  }, [roomId]);

  // 주소로 받은 날짜(객실 추천에서 넘어옴)가 여러 달에 걸치면 그 달들도 불러와서 확인한다.
  const { load } = cal;
  useEffect(() => {
    if (!form.checkInDate || !form.checkOutDate || form.checkOutDate <= form.checkInDate) return;
    for (let m = form.checkInDate.slice(0, 7); m <= form.checkOutDate.slice(0, 7); m = addDays(`${m}-28`, 7).slice(0, 7)) {
      load(m);
    }
  }, [load, form.checkInDate, form.checkOutDate]);

  // 고른 기간에 막힌 날이 끼어 있는지 (달력 데이터를 받은 뒤에만 판단)
  let rangeError = "";
  if (form.checkInDate && form.checkOutDate) {
    const { last, unknown } = lastCheckout(cal.byDay, form.checkInDate);
    if (form.checkOutDate <= form.checkInDate) rangeError = "체크아웃은 체크인 다음 날부터 선택할 수 있습니다.";
    else if (!(last && form.checkOutDate <= last) && !unknown)
      rangeError = "선택한 기간에 예약할 수 없는 날이 있습니다. 달력에서 날짜를 다시 골라 주세요.";
  }

  // 요금 견적(4C): 날짜 · 인원이 정해지면 서버에 물어본다. 금액은 화면에서 계산하지 않는다(저장 금액과 같게).
  const canQuote = !!roomId && !!form.checkInDate && form.checkOutDate > form.checkInDate && form.guestCount >= 1 && !rangeError;
  const quoteKey = canQuote ? `${form.checkInDate}|${form.checkOutDate}|${form.guestCount}` : "";
  const [quoteResult, setQuoteResult] = useState<{ key: string; data?: Quote; error?: string }>({ key: "" });
  useEffect(() => {
    if (!quoteKey) return;
    let current = true; // 빨리 바꿔 누르면 늦게 온 예전 답은 버린다
    roomsApi
      .quote(roomId, form.checkInDate, form.checkOutDate, form.guestCount)
      .then((data) => current && setQuoteResult({ key: quoteKey, data }))
      .catch((e: ApiError) => current && setQuoteResult({ key: quoteKey, error: e.message }));
    return () => { current = false; };
  }, [quoteKey]); // eslint-disable-line react-hooks/exhaustive-deps -- quoteKey 에 날짜 · 인원이 다 들어 있음
  const quote = quoteKey && quoteResult.key === quoteKey ? quoteResult : null; // null 이면 아직 계산 중

  if (!roomId) {
    return (
      <p className="text-sm">
        객실을 먼저 선택하세요. <Link href="/rooms" className="text-blue-600 underline">객실 추천으로 →</Link>
      </p>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!quote?.data) return;
    if (!confirm(`${room?.roomName} ${quote.data.nights}박, ${won(quote.data.totalPrice)} 예약할까요?`)) return;
    setSubmitting(true);
    try {
      const r = await reservationsApi.create({ roomId, ...form, requestMemo: form.requestMemo || undefined });
      router.push(`/reservation/${r.reservationId}/complete`);
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 401) router.push(`/login?next=${encodeURIComponent(location.pathname + location.search)}`);
      else setError(e.message);
      if (e.status === 409) cal.reload(); // 그사이 다른 예약 · 휴무가 생겼으면 달력을 새로 받아 보여 준다
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_360px]">
      <form onSubmit={submit} className="card space-y-4">
        <StayCalendar cal={cal} checkIn={form.checkInDate} checkOut={form.checkOutDate}
          onChange={(checkInDate, checkOutDate) => { setForm({ ...form, checkInDate, checkOutDate }); setError(""); }} />
        <div className="grid grid-cols-2 gap-3 text-sm">
          <p className="rounded-md border border-slate-200 px-3 py-2">
            <span className="block text-xs text-slate-500">체크인</span>
            {form.checkInDate ? dayLabel(form.checkInDate) : "-"}
          </p>
          <p className="rounded-md border border-slate-200 px-3 py-2">
            <span className="block text-xs text-slate-500">체크아웃</span>
            {form.checkOutDate ? dayLabel(form.checkOutDate) : "-"}
          </p>
        </div>
        {rangeError && <p className="text-sm text-red-600">{rangeError}</p>}
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
        <button className="btn-primary w-full" disabled={submitting || !quote?.data}>
          예약하기
        </button>
      </form>

      <aside className="card h-fit space-y-2 text-sm">
        <div className="flex h-32 items-center justify-center rounded-lg bg-slate-100 text-4xl">🛏️</div>
        <h2 className="text-lg font-semibold">{room?.roomName ?? "…"}</h2>
        <p className="text-slate-500">{room?.description}</p>
        <p>1박 {room ? won(room.price) : "-"} · 최대 {room?.maxGuest}명</p>
        <hr className="border-slate-200" />
        {!canQuote ? (
          <p className="text-slate-500">날짜와 인원을 고르면 요금이 나와요.</p>
        ) : !quote ? (
          <p className="text-slate-500">요금 계산 중…</p>
        ) : quote.error ? (
          <p className="text-red-600">{quote.error}</p>
        ) : quote.data && (
          <>
            <p className="flex justify-between text-slate-600">
              <span>{won(quote.data.pricePerNight)} × {quote.data.nights}박</span>
              <span>{quote.data.guests}명</span>
            </p>
            <p className="flex justify-between">
              <span>총액</span>
              <strong className="text-lg">{won(quote.data.totalPrice)}</strong>
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
