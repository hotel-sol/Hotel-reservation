"use client";

/**
 * RSV-001 예약 달력. GET /api/rooms/{id}/available-dates 로 날짜별 예약 가능 여부를 받아 그린다.
 *
 * 규칙 (백엔드와 같음: 예약이 차지하는 날은 체크인 <= 날짜 < 체크아웃)
 * - 체크인은 예약 가능한 날만 고를 수 있다.
 * - 체크아웃은 체크인 다음 날부터 "처음 막힌 날"까지 고를 수 있다.
 *   체크아웃 날은 묵지 않으므로 그날이 막혀 있어도 된다. 사이에 막힌 날이 끼면 그 뒤는 못 고른다.
 * - 달을 넘기는 예약도 같은 규칙. 두 달을 나란히 보여 주고, 필요한 달은 그때그때 불러온다.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ApiError } from "@/lib/api/client";
import { roomsApi } from "@/lib/api/rooms";
import { today } from "@/lib/format";
import type { CalendarDay } from "@/types/api";

const WEEK = ["일", "월", "화", "수", "목", "금", "토"];
const REASON_LABEL = { PAST: "지난 날", CLOSED: "휴무", BOOKED: "예약됨" } as const;

const pad = (n: number) => String(n).padStart(2, "0");

/** 백엔드 reservation_service 의 MAX_NIGHTS · BOOKING_WINDOW_DAYS 와 같은 값 (바꾸면 둘 다) */
export const MAX_NIGHTS = 6;
const BOOKING_WINDOW_DAYS = 30;

/** "2026-12-31" + 1 → "2027-01-01" (UTC 로 계산해서 시간대 영향 없음) */
export function addDays(date: string, n: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** "2026-12" + 1 → "2027-01" */
function addMonths(month: string, n: number): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 + n, 1)).toISOString().slice(0, 7);
}

/** 그달 날짜 칸 (앞쪽 빈칸은 null) */
function monthCells(month: string): (string | null)[] {
  const [y, m] = month.split("-").map(Number);
  const firstWeekday = new Date(Date.UTC(y, m - 1, 1)).getUTCDay();
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate();
  return [
    ...Array<null>(firstWeekday).fill(null),
    ...Array.from({ length: days }, (_, i) => `${month}-${pad(i + 1)}`),
  ];
}

/** "2026-12-15" → "12월 15일 (화)" */
export function dayLabel(date: string): string {
  const d = new Date(`${date}T00:00:00Z`);
  return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${WEEK[d.getUTCDay()]})`;
}

type DayMap = Map<string, CalendarDay>;

/**
 * checkIn 에서 고를 수 있는 가장 늦은 체크아웃 (최대 MAX_NIGHTS 박).
 * last: 그 날짜 (checkIn 자체가 막혀 있으면 null)
 * unknown: 아직 불러오지 않은 달에서 멈췄으면 true (그 달을 불러오면 더 늘어날 수 있음)
 */
export function lastCheckout(byDay: DayMap, checkIn: string): { last: string | null; unknown: boolean } {
  let d = checkIn;
  let last: string | null = null;
  for (let i = 0; i < MAX_NIGHTS; i++) {
    const info = byDay.get(d);
    if (!info) return { last, unknown: true };
    if (!info.available) return { last, unknown: false };
    d = addDays(d, 1);
    last = d; // 이 날까지 묵는 날이 모두 비어 있으니 체크아웃 가능
  }
  return { last, unknown: false };
}

/** 객실 달력 데이터: 달마다 한 번만 불러와서 모아 둔다. */
export function useRoomCalendar(roomId: number) {
  const [months, setMonths] = useState<Record<string, CalendarDay[]>>({});
  const [serverToday, setServerToday] = useState(today);
  const [error, setError] = useState("");
  const requested = useRef(new Set<string>());

  const load = useCallback(
    (month: string) => {
      if (!roomId || requested.current.has(month)) return;
      requested.current.add(month);
      roomsApi
        .availableDates(roomId, month)
        .then((r) => {
          setMonths((prev) => ({ ...prev, [month]: r.days }));
          setServerToday(r.today);
        })
        .catch((e: ApiError) => {
          requested.current.delete(month);
          setError(e.message);
        });
    },
    [roomId],
  );

  /** 예약이 막혔을 때 등: 받아 둔 달력을 버리고 다시 불러온다. */
  const reload = useCallback(() => {
    requested.current.clear();
    setMonths({});
    setError("");
  }, []);

  const byDay: DayMap = useMemo(
    () => new Map(Object.values(months).flat().map((d) => [d.day, d])),
    [months],
  );

  return { months, byDay, today: serverToday, error, load, reload };
}

export type RoomCalendar = ReturnType<typeof useRoomCalendar>;

interface Props {
  cal: RoomCalendar;
  checkIn: string;
  checkOut: string;
  onChange: (checkIn: string, checkOut: string) => void;
}

export default function StayCalendar({ cal, checkIn, checkOut, onChange }: Props) {
  const thisMonth = cal.today.slice(0, 7);
  const [view, setView] = useState(() => (checkIn && checkIn.slice(0, 7) > thisMonth ? checkIn.slice(0, 7) : thisMonth));
  const shown = [view, addMonths(view, 1)];

  const { load, months } = cal;
  useEffect(() => {
    load(view);
    load(addMonths(view, 1));
  }, [load, view, months]); // months: reload() 로 비워지면 다시 불러오기

  const pickingCheckOut = !!checkIn && !checkOut;
  const windowEnd = addDays(cal.today, BOOKING_WINDOW_DAYS); // 이 날까지만 체크인 가능
  const canCheckIn = (day: CalendarDay) => day.available && day.day <= windowEnd;
  const limit = pickingCheckOut ? lastCheckout(cal.byDay, checkIn).last : null;

  /** 체크아웃을 고르는 중이면 checkIn 다음 날 ~ limit 까지는 막힌 날이어도 고를 수 있다. */
  const canCheckOut = (date: string) => pickingCheckOut && date > checkIn && limit !== null && date <= limit;

  function pick(day: CalendarDay) {
    if (canCheckOut(day.day)) onChange(checkIn, day.day);
    else if (canCheckIn(day)) onChange(day.day, ""); // 새로 체크인부터
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <button type="button" className="btn-outline px-3 py-1" disabled={view <= thisMonth}
          onClick={() => setView(addMonths(view, -1))} aria-label="이전 달">‹</button>
        <p className="text-sm text-slate-600">
          {!checkIn || checkOut ? "체크인 날짜를 고르세요" : "체크아웃 날짜를 고르세요"}
        </p>
        <button type="button" className="btn-outline px-3 py-1"
          disabled={addMonths(view, 1) >= windowEnd.slice(0, 7)}
          onClick={() => setView(addMonths(view, 1))} aria-label="다음 달">›</button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {shown.map((month) => (
          <div key={month}>
            <p className="mb-1 text-center text-sm font-semibold">
              {Number(month.slice(0, 4))}년 {Number(month.slice(5))}월
            </p>
            <div className="grid grid-cols-7 gap-1 text-center text-xs text-slate-500">
              {WEEK.map((w) => <div key={w} className="py-1">{w}</div>)}
            </div>
            {!cal.months[month] ? (
              <p className="py-10 text-center text-xs text-slate-400">불러오는 중…</p>
            ) : (
              <div className="grid grid-cols-7 gap-1">
                {monthCells(month).map((date, i) => {
                  const day = date ? cal.byDay.get(date) : undefined;
                  if (!date || !day) return <div key={`blank-${month}-${i}`} />;
                  const enabled = canCheckOut(date) || canCheckIn(day);
                  const isEdge = date === checkIn || date === checkOut;
                  const inRange = !!checkIn && !!checkOut && date > checkIn && date < checkOut;
                  return (
                    <button
                      key={date}
                      type="button"
                      disabled={!enabled}
                      onClick={() => pick(day)}
                      title={day.reason ? REASON_LABEL[day.reason] : undefined}
                      aria-label={`${date}${day.reason ? ` ${REASON_LABEL[day.reason]}` : ""}`}
                      className={[
                        "flex h-12 flex-col items-center justify-center rounded-md text-sm",
                        isEdge
                          ? "bg-blue-600 font-semibold text-white"
                          : inRange
                            ? "bg-blue-100 text-blue-900"
                            : day.reason === "CLOSED"
                              ? "bg-red-50 text-red-400"
                              : day.reason === "BOOKED"
                                ? "bg-slate-100 text-slate-400 line-through"
                                : day.reason === "PAST"
                                  ? "text-slate-300"
                                  : "hover:bg-blue-50",
                        enabled ? "" : "cursor-not-allowed",
                      ].join(" ")}
                    >
                      <span>{Number(date.slice(8))}</span>
                      {day.reason && day.reason !== "PAST" && !isEdge && (
                        <span className="text-[10px] leading-none no-underline">{REASON_LABEL[day.reason]}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      <p className="flex flex-wrap gap-4 text-xs text-slate-500">
        <span><span className="mr-1 inline-block size-3 rounded-sm bg-blue-600 align-middle" />체크인 · 체크아웃</span>
        <span><span className="mr-1 inline-block size-3 rounded-sm bg-red-50 align-middle ring-1 ring-red-200" />휴무</span>
        <span><span className="mr-1 inline-block size-3 rounded-sm bg-slate-100 align-middle ring-1 ring-slate-200" />예약됨</span>
        <span>체크아웃 날은 묵지 않아서, 다음 예약이 시작하는 날도 체크아웃으로 고를 수 있어요.</span>
      </p>
      {cal.error && <p className="text-sm text-red-600">{cal.error}</p>}
    </div>
  );
}
