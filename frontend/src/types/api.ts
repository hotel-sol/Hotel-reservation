// 백엔드(app/schemas) 응답과 1:1. JSON 키는 camelCase.

export type Role = "USER" | "ADMIN";
export type ReservationStatus = "PENDING" | "APPROVED" | "CANCELED";
export type RoomSort = "recommend" | "popular" | "price";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface Member {
  memberId: number;
  loginId: string;
  name: string;
  phone: string | null;
  email: string | null;
  role: Role;
}

export interface Room {
  roomId: number;
  roomName: string;
  roomType: string;
  maxGuest: number;
  price: number;
  description: string | null;
  viewCount: number;
  isActive: "Y" | "N";
}

/** 객실 관리 목록 요약 (GET /api/admin/rooms/summary). 휴무 = 예약 일자 관리(closed_date) 기준, 오늘 = 한국 시간 */
export interface RoomSummary {
  total: number;
  onSale: number; // 사용 중이고 오늘 휴무가 아닌 객실 (휴무 예정 포함)
  closedToday: number;
  closedSoon: number;
  inactive: number;
  closedTodayRoomIds: number[];
  closedSoonRoomIds: number[];
}

/** 첨부파일 (POST/GET /api/files). savedPath 는 fileUrl() 로 감싸 <img src> 에 쓴다 */
export interface AttachFile {
  fileId: number;
  targetType: string;
  targetId: number;
  originalName: string;
  savedPath: string;
  fileSize: number;
}

export interface RecommendRoom extends Room {
  score: number;
  recentReservations: number; // 최근 30일 승인 예약 수
  // 전체 승인 예약 수(인기순 기준). feature/rooms-recommend 백엔드부터 내려와서, 그 전 서버에서는 없을 수 있다
  totalReservations?: number;
  isRecommended: boolean; // 추천 점수 1~3위 (= badge "BEST")
  // 뱃지 하나: BEST(점수 1~3위) > HOT(7일 승인 예약 1~3위) > NEW(등록 14일 이내). 예전 서버에서는 없을 수 있다
  badge?: "BEST" | "HOT" | "NEW" | null;
  thumbnailUrl: string | null; // 대표 사진 경로 (예: "uploads/rooms/a.jpg"), 없으면 null
}

// GET /api/rooms/{id} — 객실 상세(1B). 추천 카드 정보 + 사진 전부(올린 순서)
export interface RoomDetail extends RecommendRoom {
  photos: string[];
}

export interface Reservation {
  reservationId: number;
  memberId: number;
  roomId: number;
  roomName: string | null;
  memberName: string | null;
  checkInDate: string; // YYYY-MM-DD
  checkOutDate: string;
  guestCount: number;
  totalPrice: number;
  status: ReservationStatus;
  requestMemo: string | null;
  canceledAt: string | null; // 취소 시각 (취소 예약만)
  canceledBy: number | null; // 취소한 회원 번호 (관리자 취소면 그 관리자)
  createdAt: string;
  updatedAt: string;
}

export interface ClosedDate {
  closedDateId: number;
  roomId: number | null; // null = 호텔 전체 휴무
  roomName: string | null;
  closedDate: string;
  reason: string | null;
}

/** 예약 달력 하루 (RSV-001). reason: 지난 날 · 휴무 · 예약됨, 예약 가능하면 null */
export interface CalendarDay {
  day: string; // YYYY-MM-DD
  available: boolean;
  reason: "PAST" | "CLOSED" | "BOOKED" | null;
}

/** GET /api/rooms/{id}/available-dates?month=YYYY-MM */
export interface AvailableDates {
  month: string;
  today: string; // 한국 시간 기준 오늘
  days: CalendarDay[];
}

/** GET /api/rooms/{id}/quote 요금 견적. 예약 저장과 같은 계산: totalPrice = pricePerNight * nights */
export interface Quote {
  roomId: number;
  checkIn: string;
  checkOut: string;
  guests: number;
  nights: number;
  pricePerNight: number;
  totalPrice: number;
}

/** 날짜별 예약 수(대기 + 승인). 0건인 날은 빠진다. 예: {"2026-12-15": 1} */
export type ReservationCounts = Record<string, number>;

/** 관리자 예약 관리 탭 옆 숫자: 상태별 건수 + 전체 */
export type ReservationStatusCounts = Record<"ALL" | ReservationStatus, number>;

export interface MenuItem {
  menuId: number;
  parentId: number | null;
  menuName: string;
  menuUrl: string | null;
  role: Role;
  sortOrder: number;
  children: MenuItem[];
}

export interface ApiErrorBody {
  detail: { code: string; message: string } | { msg: string }[] | string;
}
