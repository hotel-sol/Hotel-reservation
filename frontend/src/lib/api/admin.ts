import type { ClosedDate, Page, Reservation, ReservationCounts, ReservationStatus, Room } from "@/types/api";
import { api } from "./client";

export type RoomInput = Pick<Room, "roomName" | "roomType" | "maxGuest" | "price" | "description">;

export const adminApi = {
  // ADM-001 객실 관리
  rooms: (query: { keyword?: string; isActive?: "Y" | "N"; page?: number; size?: number }) =>
    api<Page<Room>>("/admin/rooms", { query }),
  createRoom: (body: RoomInput) => api<Room>("/admin/rooms", { method: "POST", json: body }),
  updateRoom: (roomId: number, body: RoomInput) => api<Room>(`/admin/rooms/${roomId}`, { method: "PUT", json: body }),
  setRoomActive: (roomId: number, isActive: "Y" | "N") =>
    api<Room>(`/admin/rooms/${roomId}/status`, { method: "PATCH", json: { isActive } }),

  // ADM-002 예약 일자(휴무일) 관리. roomId 없음 = 모든 휴무, 있음 = 호텔 전체 휴무 + 그 방 휴무
  closedDates: (month: string, roomId?: number) => api<ClosedDate[]>("/admin/closed-dates", { query: { month, roomId } }),
  reservationCounts: (month: string, roomId?: number) =>
    api<ReservationCounts>("/admin/closed-dates/reservation-counts", { query: { month, roomId } }),
  // 400 PAST_DATE · 409 ALREADY_CLOSED · 409 CLOSED_DATE_CONFLICT(그날 예약 있음)
  createClosedDate: (body: { roomId: number | null; closedDate: string; reason: string }) =>
    api<ClosedDate>("/admin/closed-dates", { method: "POST", json: body }),
  // 기간 지정(시작 ~ 끝 포함, 최대 31일). 하루라도 막히면 전부 거부(오류 문구에 막힌 날짜) · 400 RANGE_TOO_LONG
  createClosedDateRange: (body: { roomId: number | null; startDate: string; endDate: string; reason: string }) =>
    api<ClosedDate[]>("/admin/closed-dates/range", { method: "POST", json: body }),
  deleteClosedDate: (id: number) => api<void>(`/admin/closed-dates/${id}`, { method: "DELETE" }),

  // ADM-003 예약 관리
  reservations: (query: { status?: ReservationStatus | ""; from?: string; to?: string; keyword?: string; page?: number }) =>
    api<Page<Reservation>>("/admin/reservations", { query }),
  approve: (id: number) => api<Reservation>(`/admin/reservations/${id}/approve`, { method: "PATCH" }),
  cancel: (id: number) => api<Reservation>(`/admin/reservations/${id}/cancel`, { method: "PATCH" }),
};
