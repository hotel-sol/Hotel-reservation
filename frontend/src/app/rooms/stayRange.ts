import { nightsBetween, today } from "@/lib/format";

/**
 * 예약할 수 있는 기간 (#77). 백엔드 reservation_service 의 MAX_NIGHTS · BOOKING_WINDOW_DAYS,
 * 예약 달력(StayCalendar.tsx)과 같은 값 — 바꾸면 셋 다 바꾼다.
 */
export const MAX_NIGHTS = 30;
export const BOOKING_WINDOW_DAYS = 365;

/** YYYY-MM-DD 에 n 일 더하기 */
export function addDays(date: string, n: number): string {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + n);
  return d.toLocaleDateString("sv-SE");
}

/** 체크인 최대 날짜 (오늘 + BOOKING_WINDOW_DAYS) */
export const lastCheckIn = () => addDays(today(), BOOKING_WINDOW_DAYS);

/** 예약 가능 기간을 벗어나면 안내 문구, 괜찮으면 null */
export function stayRangeError(checkIn: string, checkOut: string): { field: "checkIn" | "checkOut"; message: string } | null {
  if (checkIn > lastCheckIn()) {
    return { field: "checkIn", message: `체크인은 오늘부터 ${BOOKING_WINDOW_DAYS}일 안의 날짜만 고를 수 있어요.` };
  }
  if (nightsBetween(checkIn, checkOut) > MAX_NIGHTS) {
    return { field: "checkOut", message: `한 번에 최대 ${MAX_NIGHTS}박까지 예약할 수 있어요.` };
  }
  return null;
}
