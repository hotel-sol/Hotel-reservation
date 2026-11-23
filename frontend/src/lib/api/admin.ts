import type { ClosedDate, Page, Reservation, ReservationStatus, Room } from "@/types/api";
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

  // ADM-002 휴무일 관리
  closedDates: (month: string, roomId?: number) => api<ClosedDate[]>("/admin/closed-dates", { query: { month, roomId } }),
  createClosedDate: (body: { roomId: number | null; closedDate: string; reason?: string }) =>
    api<ClosedDate>("/admin/closed-dates", { method: "POST", json: body }),
  deleteClosedDate: (id: number) => api<void>(`/admin/closed-dates/${id}`, { method: "DELETE" }),

  // ADM-003 예약 관리
  reservations: (query: { status?: ReservationStatus | ""; from?: string; to?: string; keyword?: string; page?: number }) =>
    api<Page<Reservation>>("/admin/reservations", { query }),
  approve: (id: number) => api<Reservation>(`/admin/reservations/${id}/approve`, { method: "PATCH" }),
  cancel: (id: number) => api<Reservation>(`/admin/reservations/${id}/cancel`, { method: "PATCH" }),
};
