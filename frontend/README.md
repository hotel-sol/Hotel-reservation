# Frontend — Next.js 16

## 실행

```bash
cp .env.example .env.local   # BACKEND_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
```

백엔드가 먼저 떠 있어야 합니다. `next.config.ts` 의 rewrites 가 `/api/*` 를 `BACKEND_URL` 로 넘깁니다.

> Next.js 16 + `cacheComponents` 사용 중입니다. `useSearchParams` · `useParams` · `usePathname` · `new Date()` 를 쓰는
> 클라이언트 컴포넌트는 `<Suspense>` 안에 두어야 빌드됩니다. 자세한 건 `node_modules/next/dist/docs/` 참고.

## 구조

```
src/
├── app/                              라우트 (DB menu 테이블의 menu_url 과 맞춤)
│   ├── layout.tsx                    공통 헤더(메뉴·로그인 상태)
│   ├── rooms/                        ROOM-001 객실 추천
│   ├── reservation/new/              RSV-001 객실 예약  (?roomId=&checkIn=&checkOut=&guests=)
│   ├── reservation/[reservationId]/complete/   RSV-002 예약 완료
│   ├── reservation/list/             내 예약 조회
│   ├── login/ · signup/ · mypage/ · password-reset/
│   └── admin/                        관리자 (AdminGuard 로 화면 보호, 실제 권한은 백엔드)
│       ├── rooms/                    ADM-001
│       ├── closed-dates/             ADM-002
│       └── reservations/             ADM-003
├── components/                       Header, RoomCard, Pagination, StatusBadge, PageTitle
├── lib/
│   ├── api/                          client.ts(fetch 래퍼·ApiError) + 도메인별 API 함수
│   └── format.ts                     금액·날짜·상태 라벨
└── types/api.ts                      백엔드 응답 타입 (camelCase)
```

각 라우트는 `page.tsx`(서버, 정적 셸) + `XxxForm.tsx`/`XxxManager.tsx`(`"use client"`, 상호작용) 로 나눴습니다.
