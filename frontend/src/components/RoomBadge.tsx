import type { RecommendRoom } from "@/types/api";

// 뱃지는 하나만: BEST(추천 1~3위) > HOT(7일 예약 1~3위) > NEW(등록 14일 이내)
const BADGES = {
  BEST: { label: "★ 추천", color: "bg-orange-600" },
  HOT: { label: "HOT", color: "bg-red-600" },
  NEW: { label: "NEW", color: "bg-emerald-600" },
} as const;

/** 객실 뱃지. 예전 백엔드는 badge 를 안 주므로 isRecommended 로 대신한다 */
export default function RoomBadge({ room, className = "" }: { room: Pick<RecommendRoom, "badge" | "isRecommended">; className?: string }) {
  const key = room.badge === undefined ? (room.isRecommended ? "BEST" : null) : room.badge;
  if (!key) return null;
  const b = BADGES[key];
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium text-white ${b.color} ${className}`}>{b.label}</span>
  );
}
