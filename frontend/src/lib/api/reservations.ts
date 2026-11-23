import type { Reservation } from "@/types/api";
import { api } from "./client";

export interface ReservationCreate {
  roomId: number;
  checkInDate: string;
  checkOutDate: string;
  guestCount: number;
  requestMemo?: string;
}

export const reservationsApi = {
  create: (body: ReservationCreate) => api<Reservation>("/reservations", { method: "POST", json: body }),
  get: (id: number) => api<Reservation>(`/reservations/${id}`),
  mine: () => api<Reservation[]>("/reservations/me"),
};
