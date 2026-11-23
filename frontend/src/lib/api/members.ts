import type { Member } from "@/types/api";
import { api } from "./client";

export const membersApi = {
  me: () => api<Member>("/members/me"),
  login: (loginId: string, password: string) =>
    api<Member>("/members/login", { method: "POST", json: { loginId, password } }),
  logout: () => api<{ message: string }>("/members/logout", { method: "POST" }),
  signup: (body: { loginId: string; password: string; name: string; phone?: string; email?: string }) =>
    api<Member>("/members/signup", { method: "POST", json: body }),
};
