import Link from "next/link";
import { won } from "@/lib/format";
import type { RecommendRoom } from "@/types/api";

export default function RoomCard({ room, query, onOpen }: { room: RecommendRoom; query: string; onOpen: () => void }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex h-36 items-center justify-center rounded-lg bg-slate-100 text-4xl">🛏️</div>
      <div className="flex items-center gap-2">
        <h3 className="font-semibold">{room.roomName}</h3>
        {room.isRecommended && <span className="rounded bg-blue-600 px-1.5 py-0.5 text-xs text-white">추천</span>}
      </div>
      <p className="line-clamp-2 text-sm text-slate-500">{room.description}</p>
      <div className="flex justify-between text-sm">
        <span className="text-slate-500">
          {room.roomType} · 최대 {room.maxGuest}명
        </span>
        <span className="font-semibold">{won(room.price)} / 1박</span>
      </div>
      <Link href={`/reservation/new?roomId=${room.roomId}${query}`} onClick={onOpen} className="btn-primary mt-auto">
        예약하기
      </Link>
    </div>
  );
}
