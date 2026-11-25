"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import RoomBadge from "@/components/RoomBadge";
import RoomCard from "@/components/RoomCard";
import { ApiError } from "@/lib/api/client";
import { roomsApi } from "@/lib/api/rooms";
import { fileUrl, nightsBetween, won } from "@/lib/format";
import { stayRangeError } from "../stayRange";
import type { RecommendRoom, RoomDetail as Detail } from "@/types/api";

const BADGE_NOTE = {
  BEST: "추천 점수 1~3위 객실이에요.",
  HOT: "최근 7일 동안 예약이 많은 객실이에요.",
  NEW: "새로 등록된 객실이에요.",
} as const;

/** 1B 객실 상세: 사진 갤러리(크게 보기) · 객실 정보 · 예약 패널 · 다른 추천 객실 */
export default function RoomDetail() {
  const { roomId } = useParams<{ roomId: string }>();
  const params = useSearchParams();
  const [room, setRoom] = useState<Detail | null>(null);
  const [others, setOthers] = useState<RecommendRoom[]>([]);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<number | null>(null); // 크게 보는 사진 번호

  // 추천 화면에서 고른 검색 조건(날짜 · 인원)을 그대로 이어 간다
  const checkIn = params.get("checkIn") ?? "";
  const checkOut = params.get("checkOut") ?? "";
  const guests = params.get("guests") ?? "";
  const dated = Boolean(checkIn && checkOut);
  const query = [dated && `checkIn=${checkIn}&checkOut=${checkOut}`, guests && `guests=${guests}`].filter(Boolean).join("&");

  useEffect(() => {
    let ignore = false;
    const id = Number(roomId);
    roomsApi
      .detail(id)
      .then((d) => { if (!ignore) setRoom(d); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    roomsApi
      .recommend({ size: 4 })
      .then((d) => { if (!ignore) setOthers(d.items.filter((r) => r.roomId !== id).slice(0, 3)); })
      .catch(() => {});
    // 조회수: 같은 탭에서 같은 방은 한 번만 센다(새로고침 · 뒤로 가기로 늘지 않게)
    try {
      const key = `viewed-room-${id}`;
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, "1");
        roomsApi.view(id).catch(() => {});
      }
    } catch {
      roomsApi.view(id).catch(() => {});
    }
    return () => { ignore = true; };
  }, [roomId]);

  // 크게 보기: Esc 닫기, ← → 넘기기
  useEffect(() => {
    if (open === null || !room) return;
    const total = room.photos.length;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(null);
      if (e.key === "ArrowLeft") setOpen((i) => (i === null ? i : (i - 1 + total) % total));
      if (e.key === "ArrowRight") setOpen((i) => (i === null ? i : (i + 1) % total));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, room]);

  if (error) {
    return (
      <div className="card mx-auto max-w-md space-y-3 text-center text-sm">
        <p className="text-4xl">🛏️</p>
        <p className="text-red-600">{error}</p>
        <Link href="/rooms" className="btn-primary">객실 추천으로 돌아가기</Link>
      </div>
    );
  }
  if (!room) return <p className="text-sm text-slate-500">불러오는 중…</p>;

  const photos = room.photos.map(fileUrl);
  const nights = dated ? nightsBetween(checkIn, checkOut) : 0;
  const tooMany = guests !== "" && Number(guests) > room.maxGuest;
  // #77: 예약과 같은 기간 제한을 벗어나면 예상 금액 대신 안내 + [날짜 다시 고르기]
  const rangeError = dated ? stayRangeError(checkIn, checkOut)?.message ?? "" : "";
  const reserveHref = `/reservation/new?roomId=${room.roomId}${query ? `&${query}` : ""}`;

  return (
    <div className="space-y-8">
      <nav className="text-sm text-slate-500" aria-label="현재 위치">
        <Link href={`/rooms${query ? `?${query}` : ""}`} className="hover:underline">객실 추천</Link>
        <span className="mx-2" aria-hidden="true">›</span>
        <span className="text-slate-900">{room.roomName}</span>
      </nav>

      {/* ---------- 사진 ---------- */}
      <section aria-label="객실 사진" className="relative">
        {photos.length ? (
          <div className="grid h-72 gap-2 overflow-hidden rounded-xl sm:h-96 sm:grid-cols-3 sm:grid-rows-2">
            <button type="button" onClick={() => setOpen(0)} aria-label="사진 크게 보기"
              className="relative sm:col-span-2 sm:row-span-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photos[0]} alt={`${room.roomName} 대표 사진`} className="h-full w-full object-cover" />
            </button>
            {photos.slice(1, 3).map((src, i) => (
              <button key={src} type="button" onClick={() => setOpen(i + 1)} aria-label={`사진 ${i + 2} 크게 보기`}
                className="relative hidden sm:block">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={src} alt={`${room.roomName} 사진 ${i + 2}`} loading="lazy" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        ) : (
          <div className="flex h-72 items-center justify-center rounded-xl bg-slate-100 text-sm text-slate-500">
            <span className="mr-2 text-4xl">🛏️</span> 사진 준비 중
          </div>
        )}
        <RoomBadge room={room} className="absolute left-3 top-3 px-3 py-1 text-sm shadow" />
        {photos.length > 1 && (
          <button type="button" onClick={() => setOpen(0)}
            className="absolute bottom-3 right-3 rounded-md bg-white/90 px-3 py-1.5 text-sm font-medium shadow hover:bg-white">
            사진 {photos.length}장 모두 보기
          </button>
        )}
      </section>

      {open !== null && photos.length > 0 && (
        <div role="dialog" aria-modal="true" aria-label={`${room.roomName} 사진`}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4" onClick={() => setOpen(null)}>
          <button type="button" className="absolute right-4 top-4 text-sm text-white" onClick={() => setOpen(null)}>닫기 ✕</button>
          {photos.length > 1 && (
            <button type="button" aria-label="이전 사진" className="absolute left-2 px-3 text-4xl text-white sm:left-6"
              onClick={(e) => { e.stopPropagation(); setOpen((open - 1 + photos.length) % photos.length); }}>‹</button>
          )}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={photos[open]} alt={`${room.roomName} 사진 ${open + 1}`} onClick={(e) => e.stopPropagation()}
            className="max-h-[85vh] max-w-full rounded-lg object-contain" />
          {photos.length > 1 && (
            <button type="button" aria-label="다음 사진" className="absolute right-2 px-3 text-4xl text-white sm:right-6"
              onClick={(e) => { e.stopPropagation(); setOpen((open + 1) % photos.length); }}>›</button>
          )}
          <p className="absolute bottom-4 text-sm text-white">{open + 1} / {photos.length}</p>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        {/* ---------- 객실 정보 ---------- */}
        <article className="space-y-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-blue-600">{room.roomType}</p>
            <h1 className="mt-1 text-3xl font-bold">{room.roomName}</h1>
            {room.badge && <p className="mt-2 text-sm text-slate-500">{BADGE_NOTE[room.badge]}</p>}
          </div>

          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["1박 요금", won(room.price)],
              ["최대 인원", `${room.maxGuest}명`],
              ["조회", room.viewCount.toLocaleString("ko-KR")],
              ["예약", `${(room.totalReservations ?? 0).toLocaleString("ko-KR")}건`],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg border border-slate-200 bg-white p-3">
                <dt className="text-xs text-slate-500">{k}</dt>
                <dd className="mt-1 font-semibold">{v}</dd>
              </div>
            ))}
          </dl>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">객실 소개</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">
              {room.description || "객실 소개를 준비하고 있어요."}
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">이용 안내</h2>
            <dl className="grid grid-cols-[110px_1fr] gap-y-2 text-sm">
              <dt className="text-slate-500">예약 확정</dt><dd>예약하면 &lsquo;승인 대기&rsquo;가 되고, 관리자가 승인하면 확정돼요.</dd>
              <dt className="text-slate-500">결제 금액</dt><dd>1박 요금 × 숙박일수</dd>
              <dt className="text-slate-500">인원</dt><dd>최대 {room.maxGuest}명까지 머물 수 있어요.</dd>
              <dt className="text-slate-500">회원</dt><dd>예약은 로그인한 회원만 할 수 있어요.</dd>
            </dl>
          </section>
        </article>

        {/* ---------- 예약 패널 ---------- */}
        <aside className="card h-fit space-y-4 lg:sticky lg:top-6" aria-label="예약">
          <p>
            <span className="text-2xl font-bold">{won(room.price)}</span>
            <span className="text-sm text-slate-500"> / 1박</span>
          </p>
          {dated ? (
            <dl className="grid grid-cols-[64px_1fr] gap-y-1 text-sm">
              <dt className="text-slate-500">일정</dt><dd>{checkIn.slice(5)} ~ {checkOut.slice(5)} ({nights}박)</dd>
              {guests && <><dt className="text-slate-500">인원</dt><dd>{guests}명</dd></>}
              {!rangeError && <><dt className="text-slate-500">예상 금액</dt><dd className="font-semibold">{won(room.price * nights)}</dd></>}
            </dl>
          ) : (
            <p className="text-sm text-slate-500">날짜는 다음 화면에서 고를 수 있어요.</p>
          )}
          {rangeError ? (
            <>
              <p className="text-sm text-red-600">{rangeError} 날짜를 다시 골라 주세요.</p>
              <Link href={`/rooms${query ? `?${query}` : ""}`} className="btn-outline w-full">날짜 다시 고르기</Link>
            </>
          ) : tooMany ? (
            <p className="text-sm text-red-600">이 객실은 최대 {room.maxGuest}명까지예요. 인원을 줄이거나 다른 객실을 골라 주세요.</p>
          ) : (
            <Link href={reserveHref} className="btn-primary w-full">예약하기</Link>
          )}
        </aside>
      </div>

      {/* ---------- 다른 추천 객실 ---------- */}
      {others.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">다른 추천 객실</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {others.map((r) => (
              <RoomCard key={r.roomId} room={r} query={query ? `&${query}` : ""} onOpen={() => roomsApi.view(r.roomId).catch(() => {})} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
