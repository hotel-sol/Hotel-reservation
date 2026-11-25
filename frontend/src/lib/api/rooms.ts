import type { AvailableDates, MenuItem, Page, Quote, RecommendRoom, Room, RoomDetail, RoomSort } from "@/types/api";
import { api } from "./client";

export interface RecommendQuery {
  checkIn?: string;
  checkOut?: string;
  guests?: number;
  sort?: RoomSort;
  page?: number;
  size?: number;
}

export const roomsApi = {
  recommend: (query: RecommendQuery) => api<Page<RecommendRoom>>("/rooms/recommend", { query: { ...query } }),
  get: (roomId: number) => api<Room>(`/rooms/${roomId}`),
  // 같은 주소. 상세 화면은 사진 · 뱃지 · 예약 수까지 쓴다
  detail: (roomId: number) => api<RoomDetail>(`/rooms/${roomId}`),
  view: (roomId: number) => api<void>(`/rooms/${roomId}/view`, { method: "POST" }),
  availableDates: (roomId: number, month: string) =>
    api<AvailableDates>(`/rooms/${roomId}/available-dates`, { query: { month } }),
  quote: (roomId: number, checkIn: string, checkOut: string, guests: number) =>
    api<Quote>(`/rooms/${roomId}/quote`, { query: { checkIn, checkOut, guests } }),
};

export const menusApi = {
  list: () => api<MenuItem[]>("/menus"),
};
