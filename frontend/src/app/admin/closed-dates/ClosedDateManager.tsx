"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { today } from "@/lib/format";
import type { ClosedDate, ReservationCounts, Room } from "@/types/api";

/**
 * ADM-002 예약 일자(휴무일) 관리
 *  ① 객실 선택 · 월 이동   "전체 객실" = 호텔 전체 휴무, 특정 객실 = 그 방만 휴무
 *  ② 달력                  날짜별 휴무 여부 + 예약 수(대기 + 승인). 지난 날짜는 누를 수 없다
 *  ③ 휴무 지정 / 해제      예약이 있는 날은 백엔드가 409 로 막는다
 *  ④ 이번 달 휴무일 목록   바로 해제
 */
const WEEK = ["일", "월", "화", "수", "목", "금", "토"];

const pad = (n: number) => String(n).padStart(2, "0");

/** "2026-12" → 그달 날짜 칸 (앞쪽 빈칸은 null) */
function monthCells(month: string): (string | null)[] {
  const [y, m] = month.split("-").map(Number);
  const firstWeekday = new Date(Date.UTC(y, m - 1, 1)).getUTCDay();
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return [
    ...Array<null>(firstWeekday).fill(null),
    ...Array.from({ length: days }, (_, i) => `${month}-${pad(i + 1)}`),
  ];
}

function shiftMonth(month: string, delta: number) {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}`;
}

function dayLabel(date: string) {
  const d = new Date(`${date}T00:00:00Z`);
  return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${WEEK[d.getUTCDay()]})`;
}

const shortDate = (date: string) => date.slice(5).replace("-", "/");

// 3C 사유 선택지(화면 선택지). DB에는 "점검 · 보일러" 같은 글자로 저장한다(테이블 변경 없음)
const REASON_TYPES = ["공사", "점검", "행사", "휴관", "기타"];

const MAX_RANGE_DAYS = 31; // 백엔드 POST /admin/closed-dates/range 와 같은 값

function addDays(date: string, n: number) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export default function ClosedDateManager() {
  const [roomId, setRoomId] = useState<number | null>(null); // null = 전체 객실
  const [month, setMonth] = useState(() => today().slice(0, 7));
  const [rooms, setRooms] = useState<Room[]>([]);
  const [closed, setClosed] = useState<ClosedDate[]>([]);
  const [counts, setCounts] = useState<ReservationCounts>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [endDate, setEndDate] = useState(""); // 기간 지정 끝 날짜. 비면 하루만
  const [reasonType, setReasonType] = useState("");
  const [reason, setReason] = useState(""); // 자세한 내용(기타면 필수)
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // 지정 · 해제 뒤 다시 불러올 때 reloadKey 를 올린다
  const [reloadKey, setReloadKey] = useState(0);
  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let ignore = false;
    adminApi
      .rooms({ size: 100 })
      .then((p) => { if (!ignore) setRooms(p.items); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    let ignore = false; // 월 · 객실을 빠르게 바꿔도 마지막 조회 결과만 반영
    const id = roomId ?? undefined;
    Promise.all([adminApi.closedDates(month, id), adminApi.reservationCounts(month, id)])
      .then(([c, n]) => {
        if (ignore) return;
        setClosed(c);
        setCounts(n);
      })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [month, roomId, reloadKey]);

  const todayStr = today();
  const hotelClosed = (date: string) => closed.find((c) => c.closedDate === date && c.roomId === null);
  // 지금 고른 범위(전체 객실 / 그 방)에 직접 지정된 휴무 — 해제 대상
  const ownClosed = (date: string) => closed.find((c) => c.closedDate === date && c.roomId === roomId);
  const roomClosedCount = (date: string) => closed.filter((c) => c.closedDate === date && c.roomId !== null).length;

  // 남은 객실 = 사용 중 객실 − 그날 휴무 객실 − 그날 숙박 예약 (전체 객실 화면에서만)
  // ponytail: 예약 수에 비활성 객실 예약이 섞이면 1~2실 적게 보인다. 정확히 필요하면 백엔드에서 계산.
  const activeIds = new Set(rooms.filter((r) => r.isActive === "Y").map((r) => r.roomId));
  const remaining = (date: string) =>
    hotelClosed(date)
      ? 0
      : Math.max(
          0,
          activeIds.size -
            closed.filter((c) => c.closedDate === date && c.roomId !== null && activeIds.has(c.roomId)).length -
            (counts[date] ?? 0),
        );

  function pick(date: string | null) {
    setSelected(date);
    setEndDate("");
    setError("");
  }

  function changeScope(next: { month?: string; roomId?: number | null }) {
    if (next.month !== undefined) setMonth(next.month);
    if (next.roomId !== undefined) setRoomId(next.roomId);
    pick(null);
    setReasonType("");
    setReason("");
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      setReasonType("");
      setReason("");
      setEndDate("");
      reload();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  const detail = reason.trim();
  const fullReason = reasonType === "기타" ? detail : detail ? `${reasonType} · ${detail}` : reasonType;
  const reasonReady = !!reasonType && (reasonType !== "기타" || !!detail);

  const isRange = !!selected && endDate > selected;
  const inRange = (date: string) => isRange && date > selected! && date <= endDate;

  const close = () =>
    selected &&
    run(() =>
      isRange
        ? adminApi.createClosedDateRange({ roomId, startDate: selected, endDate, reason: fullReason })
        : adminApi.createClosedDate({ roomId, closedDate: selected, reason: fullReason }),
    );

  function open(row: ClosedDate) {
    const where = row.roomName ?? "호텔 전체";
    if (!confirm(`${shortDate(row.closedDate)} ${where} 휴무를 해제할까요?`)) return;
    run(() => adminApi.deleteClosedDate(row.closedDateId));
  }

  const sel = selected
    ? { own: ownClosed(selected), hotel: hotelClosed(selected), count: counts[selected] ?? 0 }
    : null;
  // 방을 골랐는데 그날 호텔 전체 휴무면 방 휴무는 따로 지정할 수 없다(ALREADY_CLOSED)
  const blockedByHotel = roomId !== null && !!sel?.hotel;

  return (
    <div className="space-y-4">
      {/* ① 객실 선택 · 월 이동 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm font-medium">
          객실
          <select
            className="input w-48"
            value={roomId ?? ""}
            onChange={(e) => changeScope({ roomId: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">전체 객실 (호텔 전체 휴무)</option>
            {rooms.map((r) => (
              <option key={r.roomId} value={r.roomId}>
                {r.roomName}
                {r.isActive === "N" ? " (비활성)" : ""}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-2 font-semibold">
          <button type="button" className="btn-outline px-2 py-1" aria-label="이전 달"
            onClick={() => changeScope({ month: shiftMonth(month, -1) })}>‹</button>
          <span className="w-28 text-center">{month.replace("-", "년 ")}월</span>
          <button type="button" className="btn-outline px-2 py-1" aria-label="다음 달"
            onClick={() => changeScope({ month: shiftMonth(month, 1) })}>›</button>
        </div>
      </div>

      {error && <p className="whitespace-pre-line text-sm text-red-600">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        {/* ② 달력 */}
        <div>
          <div className="grid grid-cols-7 gap-1 text-center text-xs text-slate-500">
            {WEEK.map((w) => <div key={w} className="py-1">{w}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {monthCells(month).map((date, i) => {
              if (!date) return <div key={`blank-${i}`} />;
              const past = date < todayStr;
              const isClosed = !!hotelClosed(date) || !!ownClosed(date);
              const n = counts[date] ?? 0;
              const roomsOff = roomId === null ? roomClosedCount(date) : 0;
              const left = roomId === null && rooms.length > 0 && !past ? remaining(date) : null;
              return (
                <button
                  key={date}
                  type="button"
                  disabled={past}
                  onClick={() => pick(date)}
                  className={[
                    "flex h-16 flex-col justify-between rounded-md border p-1.5 text-left text-xs sm:h-20",
                    isClosed ? "border-red-200 bg-red-50" : inRange(date) ? "border-slate-300 bg-slate-100" : "border-slate-200 bg-white",
                    selected === date || inRange(date) ? "ring-2 ring-slate-800" : "",
                    past ? "cursor-not-allowed opacity-40" : "hover:border-slate-400",
                  ].join(" ")}
                >
                  <span className="text-sm">{Number(date.slice(8))}</span>
                  <span className="space-y-0.5">
                    {isClosed && <span className="block font-medium text-red-600">휴무</span>}
                    {roomsOff > 0 && <span className="block text-red-500">객실 휴무 {roomsOff}</span>}
                    {n > 0 && <span className="block text-slate-500">예약 {n}</span>}
                    {left !== null && !isClosed && (
                      <span className={`block ${left === 0 ? "text-red-500" : "text-emerald-700"}`}>남은 {left}실</span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
            <span><span className="mr-1 inline-block size-3 rounded-sm border border-red-200 bg-red-50 align-middle" />휴무일</span>
            <span><span className="mr-1 inline-block size-3 rounded-sm ring-2 ring-slate-800 align-middle" />선택한 날짜</span>
            <span>&quot;예약 N&quot; = 그날 잡힌 예약 수(대기 + 승인)</span>
            <span>&quot;남은 N실&quot; = 사용 중 객실 − 휴무 객실 − 예약 (전체 객실 화면)</span>
          </p>
        </div>

        <div className="space-y-4">
          {/* ③ 휴무 지정 / 해제 */}
          <div className="card space-y-3 text-sm">
            {!selected || !sel ? (
              <p className="text-slate-500">달력에서 날짜를 고르세요. 지난 날짜는 고를 수 없어요.</p>
            ) : (
              <>
                <div>
                  <p className="font-semibold">{dayLabel(selected)}</p>
                  <p className="mt-1 text-slate-500">
                    {roomId === null ? "이 날 예약" : `${rooms.find((r) => r.roomId === roomId)?.roomName ?? ""} 예약`} {sel.count}건
                  </p>
                </div>
                {sel.own ? (
                  <>
                    <p className="rounded-md bg-red-50 px-3 py-2 text-red-700">휴무 · {sel.own.reason ?? "사유 없음"}</p>
                    <button type="button" className="btn-outline w-full" disabled={busy} onClick={() => open(sel.own!)}>
                      휴무 해제
                    </button>
                  </>
                ) : blockedByHotel ? (
                  <p className="rounded-md bg-red-50 px-3 py-2 text-red-700">
                    호텔 전체 휴무일이에요 ({sel.hotel!.reason ?? "사유 없음"}). 해제는 &quot;전체 객실&quot;에서 하세요.
                  </p>
                ) : (
                  <form
                    className="space-y-3"
                    onSubmit={(e) => { e.preventDefault(); close(); }}
                  >
                    <label className="block text-xs text-slate-500">
                      휴무 사유
                      <select className="input mt-1" value={reasonType} required
                        onChange={(e) => setReasonType(e.target.value)}>
                        <option value="">선택하세요</option>
                        {REASON_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </label>
                    <label className="block text-xs text-slate-500">
                      자세한 내용 {reasonType === "기타" ? "(필수)" : "(선택)"}
                      <input className="input mt-1" value={reason} maxLength={180} required={reasonType === "기타"}
                        placeholder="예: 보일러 교체" onChange={(e) => setReason(e.target.value)} />
                    </label>
                    <label className="block text-xs text-slate-500">
                      끝 날짜 (기간으로 지정할 때만, 최대 31일)
                      <input className="input mt-1" type="date" value={endDate} min={selected}
                        max={addDays(selected, MAX_RANGE_DAYS - 1)} onChange={(e) => setEndDate(e.target.value)} />
                    </label>
                    <button className="btn-primary w-full" disabled={busy || !reasonReady}>
                      {isRange ? `${shortDate(selected)} ~ ${shortDate(endDate)} 휴무로 지정` : "휴무일로 지정"}
                    </button>
                    {isRange && (
                      <p className="text-xs text-slate-500">기간 중 하루라도 예약이나 휴무가 있으면 전부 지정되지 않아요.</p>
                    )}
                    {sel.count > 0 && (
                      <p className="text-xs text-amber-700">이 날짜에 예약이 있어 지정되지 않아요. 먼저 예약을 취소해 주세요.</p>
                    )}
                  </form>
                )}
              </>
            )}
          </div>

          {/* ④ 이번 달 휴무일 목록 */}
          <div className="card text-sm">
            <h2 className="mb-2 font-semibold">이번 달 휴무일</h2>
            {closed.length === 0 ? (
              <p className="text-slate-400">휴무일이 없습니다.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {closed.map((c) => (
                  <li key={c.closedDateId} className="flex items-center justify-between gap-2 py-2">
                    <span>
                      {shortDate(c.closedDate)} {c.roomName ?? "전체"}
                      <span className="text-slate-500"> · {c.reason ?? "사유 없음"}</span>
                    </span>
                    <button type="button" className="shrink-0 text-red-600 hover:underline disabled:opacity-50"
                      disabled={busy} onClick={() => open(c)}>해제</button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
