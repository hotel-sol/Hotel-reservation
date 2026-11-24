import type { ApiErrorBody } from "@/types/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

function toQueryString(query?: Query) {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function parseError(status: number, body: ApiErrorBody | null): ApiError {
  const detail = body?.detail;
  if (detail && typeof detail === "object" && "code" in detail) {
    return new ApiError(status, detail.code, detail.message);
  }
  if (Array.isArray(detail)) {
    return new ApiError(status, "VALIDATION_ERROR", detail.map((d) => d.msg).join("\n"));
  }
  return new ApiError(status, "UNKNOWN", typeof detail === "string" ? detail : "요청을 처리하지 못했습니다.");
}

/** 브라우저에서 /api/* 호출 (Next 가 FastAPI 로 프록시). 쿠키 자동 포함.
 *  json: JSON 본문 / form: 파일 업로드용 FormData (Content-Type 은 브라우저가 정함) */
export async function api<T>(
  path: string,
  init: Omit<RequestInit, "body"> & { query?: Query; json?: unknown; form?: FormData } = {},
): Promise<T> {
  const { query, json, form, headers, ...rest } = init;
  const res = await fetch(`/api${path}${toQueryString(query)}`, {
    ...rest,
    credentials: "same-origin",
    headers: json !== undefined ? { "Content-Type": "application/json", ...headers } : headers,
    body: form ?? (json !== undefined ? JSON.stringify(json) : undefined),
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw parseError(res.status, body);
  return body as T;
}
