"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import RoomBadge from "@/components/RoomBadge";
import { fileUrl, won } from "@/lib/format";
import type { RecommendRoom } from "@/types/api";

/** ROOM-001 객실 카드: 대표 사진(+뱃지), 객실명(사진 · 이름을 누르면 상세), 1박 요금 · 최대 인원, 조회 · 예약 수 */
export default function RoomCard({ room, query, onOpen }: { room: RecommendRoom; query: string; onOpen: () => void }) {
  const [broken, setBroken] = useState(false); // 사진을 못 불러오면 기본 아이콘
  const photo = room.thumbnailUrl && !broken ? fileUrl(room.thumbnailUrl) : null;
  // 인기순 기준인 전체 예약 수. 예전 백엔드는 안 주므로 최근 30일 예약 수로 대신한다
  const reservations = room.totalReservations ?? room.recentReservations;
  // 상세 화면으로 갈 때도 검색 조건(날짜 · 인원)을 들고 간다. query 는 "&checkIn=..." 꼴
  const detailHref = `/rooms/${room.roomId}${query ? `?${query.replace(/^&/, "")}` : ""}`;

  return (
    <div className="card flex flex-col gap-3">
      <Link href={detailHref} className="relative block h-36 overflow-hidden rounded-lg bg-slate-100" aria-label={`${room.roomName} 상세 보기`}>
        {photo ? (
          <Image src={photo} alt={`${room.roomName} 사진`} fill unoptimized sizes="(min-width: 1024px) 33vw, 100vw"
            className="object-cover" onError={() => setBroken(true)} />
        ) : (
          <div className="flex h-full items-center justify-center text-4xl">🛏️</div>
        )}
        <RoomBadge room={room} className="absolute right-2 top-2" />
      </Link>
      <div>
        <h3 className="font-semibold"><Link href={detailHref} className="hover:underline">{room.roomName}</Link></h3>
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
