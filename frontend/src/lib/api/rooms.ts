import type { AvailableDates, MenuItem, Page, RecommendRoom, Room, RoomSort } from "@/types/api";
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
  view: (roomId: number) => api<void>(`/rooms/${roomId}/view`, { method: "POST" }),
  availableDates: (roomId: number, month: string) =>
    api<AvailableDates>(`/rooms/${roomId}/available-dates`, { query: { month } }),
};

export const menusApi = {
  list: () => api<MenuItem[]>("/menus"),
};
