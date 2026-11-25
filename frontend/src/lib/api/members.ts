import type { Member } from "@/types/api";
import { api } from "./client";

export type ProfileInput = { name: string; phone: string | null; email: string | null };

export const membersApi = {
  me: () => api<Member>("/members/me"),
  // 5번 틀리면 10분 잠금(429 TOO_MANY_ATTEMPTS)
  login: (loginId: string, password: string) =>
    api<Member>("/members/login", { method: "POST", json: { loginId, password } }),
  logout: () => api<{ message: string }>("/members/logout", { method: "POST" }),
  // 가입 전 아이디 중복확인. 형식이 틀리면 400 INVALID_LOGIN_ID
  checkId: (loginId: string) =>
    api<{ available: boolean; message: string }>(`/members/check-id?loginId=${encodeURIComponent(loginId)}`),
  signup: (body: { loginId: string; password: string; name: string; phone?: string; email?: string }) =>
    api<Member>("/members/signup", { method: "POST", json: body }),

  // 마이페이지
  updateMe: (body: ProfileInput) => api<Member>("/members/me", { method: "PUT", json: body }),
  // 바꾸면 다른 기기 로그인은 끊기고 지금 화면은 새 쿠키로 유지
  changePassword: (currentPassword: string, newPassword: string) =>
    api<void>("/members/me/password", { method: "PUT", json: { currentPassword, newPassword } }),
  // 409 HAS_RESERVATION(진행 중 예약) · 400 ADMIN_CANNOT_WITHDRAW
  withdraw: (password: string) => api<void>("/members/me/withdraw", { method: "POST", json: { password } }),
};
