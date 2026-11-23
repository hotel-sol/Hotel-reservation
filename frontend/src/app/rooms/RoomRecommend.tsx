"use client";

import { useEffect, useState } from "react";
import Pagination from "@/components/Pagination";
import RoomCard from "@/components/RoomCard";
import { ApiError } from "@/lib/api/client";
import { roomsApi } from "@/lib/api/rooms";
import { today } from "@/lib/format";
import type { Page, RecommendRoom, RoomSort } from "@/types/api";

const SORTS: { value: RoomSort; label: string }[] = [
  { value: "recommend", label: "추천순" },
  { value: "popular", label: "인기순" },
  { value: "price", label: "낮은 가격순" },
];

export default function RoomRecommend() {
  const [form, setForm] = useState({ checkIn: "", checkOut: "", guests: 2 });
  const [search, setSearch] = useState(form);
  const [sort, setSort] = useState<RoomSort>("recommend");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<RecommendRoom> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false; // 정렬·페이지를 빠르게 바꿔도 마지막 요청 결과만 반영
    const dated = search.checkIn && search.checkOut;
    roomsApi
      .recommend({
        checkIn: dated ? search.checkIn : undefined,
        checkOut: dated ? search.checkOut : undefined,
        guests: search.guests,
        sort,
        page,
        size: 6,
      })
      .then((d) => {
        if (ignore) return;
        setData(d);
        setError("");
      })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [search, sort, page]);

  const query = search.checkIn && search.checkOut
    ? `&checkIn=${search.checkIn}&checkOut=${search.checkOut}&guests=${search.guests}`
    : `&guests=${search.guests}`;

  return (
    <div className="space-y-6">
      <form
        className="card grid gap-3 sm:grid-cols-4"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
          setSearch(form);
        }}
      >
        <label className="text-sm">
          체크인
          <input type="date" className="input mt-1" min={today()} value={form.checkIn}
            onChange={(e) => setForm({ ...form, checkIn: e.target.value })} />
        </label>
        <label className="text-sm">
          체크아웃
          <input type="date" className="input mt-1" min={form.checkIn || today()} value={form.checkOut}
            onChange={(e) => setForm({ ...form, checkOut: e.target.value })} />
        </label>
        <label className="text-sm">
          인원
          <input type="number" min={1} className="input mt-1" value={form.guests}
            onChange={(e) => setForm({ ...form, guests: Number(e.target.value) })} />
        </label>
        <button className="btn-primary self-end">검색</button>
      </form>

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{data ? `${search.checkIn && search.checkOut ? "예약 가능한 객실" : "객실"} ${data.total}개` : "불러오는 중…"}</p>
        <div className="flex gap-1">
          {SORTS.map((s) => (
            <button key={s.value} onClick={() => { setSort(s.value); setPage(1); }}
              className={`rounded-full px-3 py-1 text-sm ${sort === s.value ? "bg-slate-900 text-white" : "bg-white"}`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.items.map((room) => (
          <RoomCard key={room.roomId} room={room} query={query} onOpen={() => roomsApi.view(room.roomId).catch(() => {})} />
        ))}
      </div>
      {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
    </div>
  );
}
