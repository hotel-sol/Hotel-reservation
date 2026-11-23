"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { fileUrl, won } from "@/lib/format";
import type { RecommendRoom } from "@/types/api";

/** ROOM-001 객실 카드: 대표 사진(+1등 "추천"), 객실명, 1박 요금 · 최대 인원, 조회 · 예약 수 */
export default function RoomCard({ room, query, onOpen }: { room: RecommendRoom; query: string; onOpen: () => void }) {
  const [broken, setBroken] = useState(false); // 사진을 못 불러오면 기본 아이콘
  const photo = room.thumbnailUrl && !broken ? fileUrl(room.thumbnailUrl) : null;
  // 인기순 기준인 전체 예약 수. 예전 백엔드는 안 주므로 최근 30일 예약 수로 대신한다
  const reservations = room.totalReservations ?? room.recentReservations;

  return (
    <div className="card flex flex-col gap-3">
      <div className="relative h-36 overflow-hidden rounded-lg bg-slate-100">
        {photo ? (
          <Image src={photo} alt={`${room.roomName} 사진`} fill unoptimized sizes="(min-width: 1024px) 33vw, 100vw"
            className="object-cover" onError={() => setBroken(true)} />
        ) : (
          <div className="flex h-full items-center justify-center text-4xl">🛏️</div>
        )}
        {room.isRecommended && (
          <span className="absolute right-2 top-2 rounded-full bg-orange-600 px-2 py-0.5 text-xs font-medium text-white">
            추천
          </span>
        )}
      </div>
      <div>
        <h3 className="font-semibold">{room.roomName}</h3>
        <p className="text-xs text-slate-500">{room.roomType}</p>
      </div>
      {room.description && <p className="line-clamp-2 text-sm text-slate-500">{room.description}</p>}
      <div className="space-y-0.5 text-sm">
        <p>
          1박 <span className="font-semibold">{won(room.price)}</span> · 최대 {room.maxGuest}명
        </p>
        <p className="text-xs text-slate-500">
          조회 {room.viewCount.toLocaleString("ko-KR")} · 예약 {reservations.toLocaleString("ko-KR")}
        </p>
      </div>
      <Link href={`/reservation/new?roomId=${room.roomId}${query}`} onClick={onOpen} className="btn-outline mt-auto">
        예약하기
      </Link>
    </div>
  );
}
