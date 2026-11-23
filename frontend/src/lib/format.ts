import type { ReservationStatus } from "@/types/api";

export const won = (n: number) => `${n.toLocaleString("ko-KR")}원`;

export const nightsBetween = (checkIn: string, checkOut: string) =>
  Math.max(0, Math.round((Date.parse(checkOut) - Date.parse(checkIn)) / 86_400_000));

export const STATUS_LABEL: Record<ReservationStatus, string> = {
  PENDING: "승인 대기",
  APPROVED: "승인",
  CANCELED: "취소",
};

/** 오늘 날짜 YYYY-MM-DD (로컬 기준) */
export const today = () => new Date().toLocaleDateString("sv-SE");
