import type {
  AttachFile,
  ClosedDate,
  Page,
  Reservation,
  ReservationCounts,
  ReservationStatus,
  ReservationStatusCounts,
  Room,
  RoomSummary,
} from "@/types/api";
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
  // 목록 위 요약 카드 (전체 · 판매 중 · 오늘 휴무 · 휴무 예정 · 비활성)
  roomSummary: () => api<RoomSummary>("/admin/rooms/summary"),
  // 객실 사진 (jpg·png, 객실당 최대 5장. 첫 장이 추천 카드 대표 사진)
  roomPhotos: (roomId: number) => api<AttachFile[]>("/files", { query: { targetType: "ROOM", targetId: roomId } }),
  uploadRoomPhoto: (roomId: number, file: File) => {
    const form = new FormData();
    form.append("targetType", "ROOM");
    form.append("targetId", String(roomId));
    form.append("file", file);
    return api<AttachFile>("/files", { method: "POST", form });
  },
  deleteFile: (fileId: number) => api<void>(`/files/${fileId}`, { method: "DELETE" }),

  // ADM-002 예약 일자(휴무일) 관리. roomId 없음 = 모든 휴무, 있음 = 호텔 전체 휴무 + 그 방 휴무
  closedDates: (month: string, roomId?: number) => api<ClosedDate[]>("/admin/closed-dates", { query: { month, roomId } }),
  reservationCounts: (month: string, roomId?: number) =>
    api<ReservationCounts>("/admin/closed-dates/reservation-counts", { query: { month, roomId } }),
  // 날짜별 남은 객실 수(사용 중 객실 − 휴무 − 숙박 중). 전체 객실 달력용
  availableRooms: (month: string) => api<Record<string, number>>("/admin/closed-dates/available-rooms", { query: { month } }),
  // 409 ALREADY_CLOSED · 409 CLOSED_DATE_CONFLICT(그날 예약 있음). 지난 날짜도 가능
  createClosedDate: (body: { roomId: number | null; closedDate: string; reason: string }) =>
    api<ClosedDate>("/admin/closed-dates", { method: "POST", json: body }),
  // 기간 지정(최대 31일). 하루라도 막히면 전부 거부 — 400 RANGE_TOO_LONG · 409 는 위와 같음
  createClosedDateRange: (body: { roomId: number | null; startDate: string; endDate: string; reason: string }) =>
    api<ClosedDate[]>("/admin/closed-dates/range", { method: "POST", json: body }),
  // 기간 해제: 같은 범위(roomId 없음 = 호텔 전체, 있음 = 그 방)에 직접 지정된 휴무만. 없으면 404
  deleteClosedDateRange: (q: { startDate: string; endDate: string; roomId: number | null }) =>
    api<{ deleted: number }>("/admin/closed-dates/range", {
      method: "DELETE", query: { startDate: q.startDate, endDate: q.endDate, roomId: q.roomId ?? undefined },
    }),
  deleteClosedDate: (id: number) => api<void>(`/admin/closed-dates/${id}`, { method: "DELETE" }),

  // ADM-003 예약 관리
  reservations: (query: { status?: ReservationStatus | ""; from?: string; to?: string; keyword?: string; page?: number }) =>
    api<Page<Reservation>>("/admin/reservations", { query }),
  // 탭 옆 숫자. 검색 조건(기간 · 예약자명/번호)은 목록과 같다
  reservationStatusCounts: (query: { from?: string; to?: string; keyword?: string }) =>
    api<ReservationStatusCounts>("/admin/reservations/counts", { query }),
  approve: (id: number) => api<Reservation>(`/admin/reservations/${id}/approve`, { method: "PATCH" }),
  cancel: (id: number) => api<Reservation>(`/admin/reservations/${id}/cancel`, { method: "PATCH" }),
};
