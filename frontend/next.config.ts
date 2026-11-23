import type { NextConfig } from "next";

// 브라우저 → Next(/api/*) → FastAPI 로 프록시. 같은 출처라 세션 쿠키·CORS 걱정이 없다.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
