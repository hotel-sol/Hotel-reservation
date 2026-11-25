"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import HeroSlider from "@/components/HeroSlider";
import Pagination from "@/components/Pagination";
import RoomCard from "@/components/RoomCard";
import { ApiError } from "@/lib/api/client";
import { roomsApi } from "@/lib/api/rooms";
import { nightsBetween, today } from "@/lib/format";
import { addDays, lastCheckIn, MAX_NIGHTS, stayRangeError } from "./stayRange";
import type { Page, RecommendRoom, RoomSort } from "@/types/api";

const SORTS: { value: RoomSort; label: string }[] = [
  { value: "recommend", label: "추천순" },
  { value: "popular", label: "인기순" },
  { value: "price", label: "낮은 가격순" },
];

const MAX_GUESTS = 10;

/** 검색 조건 검사. API 를 부르기 전에 화면에서 막는다(USR-REC-01 C. 날짜 오류) */
function checkForm(f: { checkIn: string; checkOut: string; guests: number }) {
  if (f.checkIn && f.checkIn < today()) return { field: "checkIn", message: "지난 날짜는 선택할 수 없어요." };
  if (Boolean(f.checkIn) !== Boolean(f.checkOut)) {
    return { field: f.checkIn ? "checkOut" : "checkIn", message: "체크인과 체크아웃을 함께 골라 주세요." };
  }
  if (f.checkIn && f.checkOut <= f.checkIn) return { field: "checkOut", message: "체크아웃은 체크인 다음 날부터 선택할 수 있어요." };
  if (f.checkIn) {
    const range = stayRangeError(f.checkIn, f.checkOut); // #77 예약과 같은 기간 제한
    if (range) return range;
  }
  if (!(f.guests >= 1 && f.guests <= MAX_GUESTS)) return { field: "guests", message: `인원은 1~${MAX_GUESTS}명이에요.` };
  return null;
}

export default function RoomRecommend() {
  // 객실 상세에서 "객실 추천"으로 돌아오면 주소의 검색 조건을 그대로 쓴다
  const params = useSearchParams();
  const [form, setForm] = useState(() => ({
    checkIn: params.get("checkIn") ?? "",
    checkOut: params.get("checkOut") ?? "",
    guests: Number(params.get("guests")) || 2,
  }));
  // 주소로 받은 날짜가 규칙에 안 맞으면(지난 날짜 · 40박 등) 날짜 없이 보여 주고, 위 칸에 빨간 안내가 뜬다
  const [search, setSearch] = useState(() => (checkForm(form) ? { ...form, checkIn: "", checkOut: "" } : form));
  const [sort, setSort] = useState<RoomSort>("recommend");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<RecommendRoom> | null>(null);
  // 마지막으로 응답을 받은 요청. 지금 조건과 다르면 '불러오는 중'
  const [doneKey, setDoneKey] = useState("");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0); // [다시 시도] 를 누르면 같은 조건으로 다시 부른다

  const requestKey = JSON.stringify([search, sort, page, retry]);
  const loading = doneKey !== requestKey;

  useEffect(() => {
    let ignore = false; // 정렬·페이지를 빠르게 바꿔도 마지막 요청 결과만 반영
    const dated = search.checkIn && search.checkOut;
    const key = JSON.stringify([search, sort, page, retry]);
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
      .catch((e: ApiError) => {
        if (ignore) return;
        setData(null);
        setError(e.message);
      })
      .finally(() => { if (!ignore) setDoneKey(key); });
    return () => { ignore = true; };
  }, [search, sort, page, retry]);

  const query = search.checkIn && search.checkOut
    ? `&checkIn=${search.checkIn}&checkOut=${search.checkOut}&guests=${search.guests}`
    : `&guests=${search.guests}`;
  const invalid = checkForm(form);
  const nights = form.checkIn && form.checkOut && !invalid ? nightsBetween(form.checkIn, form.checkOut) : 0;
  const bad = (field: string) => (invalid?.field === field ? "border-red-500 ring-2 ring-red-100" : "");

  function showAll() {
    const all = { checkIn: "", checkOut: "", guests: 1 };
    setForm(all);
    setSearch(all);
    setSort("recommend");
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <HeroSlider />

      <form
        className="card grid gap-3 sm:grid-cols-[1fr_1fr_120px_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          if (invalid) return;
          setPage(1);
          setSearch(form);
        }}
      >
        <label className="text-sm">
          체크인
          <input type="date" className={`input mt-1 ${bad("checkIn")}`} min={today()} max={lastCheckIn()} value={form.checkIn}
            onChange={(e) => setForm({ ...form, checkIn: e.target.value })} />
        </label>
        <label className="text-sm">
          체크아웃
          <input type="date" className={`input mt-1 ${bad("checkOut")}`} min={form.checkIn || today()} max={form.checkIn ? addDays(form.checkIn, MAX_NIGHTS) : undefined} value={form.checkOut}
            onChange={(e) => setForm({ ...form, checkOut: e.target.value })} />
        </label>
        <label className="text-sm">
          인원
          <input type="number" min={1} max={MAX_GUESTS} className={`input mt-1 ${bad("guests")}`} value={form.guests}
            onChange={(e) => setForm({ ...form, guests: Number(e.target.value) })} />
        </label>
        <div className="flex items-end gap-2">
          {nights > 0 && (
            <span className="mb-2 whitespace-nowrap rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">{nights}박</span>
          )}
          <button className="btn-primary w-full sm:w-auto" disabled={Boolean(invalid)}>객실 찾기</button>
        </div>
        {invalid && <p className="text-sm text-red-600 sm:col-span-4">{invalid.message}</p>}
      </form>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">이런 객실은 어떠세요?</h2>
          <p className="text-sm text-slate-500">
            {data ? `${search.checkIn && search.checkOut ? "예약 가능한 객실" : "객실"} ${data.total}개` : loading ? "불러오는 중…" : ""}
          </p>
        </div>
        <div className="flex gap-1">
          {SORTS.map((s) => (
            <button key={s.value} onClick={() => { setSort(s.value); setPage(1); }}
              className={`rounded-full px-3 py-1 text-sm ${sort === s.value ? "bg-slate-900 text-white" : "bg-white"}`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="card space-y-3 text-center text-sm">
          <p className="text-3xl">⚠️</p>
          <p className="font-medium">추천 객실을 불러오지 못했어요.</p>
          <p className="text-slate-500">{error}</p>
          <button className="btn-outline" onClick={() => setRetry((n) => n + 1)}>다시 시도</button>
        </div>
      ) : loading && !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="불러오는 중">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="card animate-pulse space-y-3">
              <div className="h-36 rounded-lg bg-slate-200" />
              <div className="h-4 w-1/3 rounded bg-slate-200" />
              <div className="h-3 w-2/3 rounded bg-slate-100" />
              <div className="h-9 rounded bg-slate-100" />
            </div>
          ))}
        </div>
      ) : (
        <div className={`grid gap-4 transition-opacity sm:grid-cols-2 lg:grid-cols-3 ${loading ? "opacity-50" : ""}`}>
          {data?.items.map((room) => (
            <RoomCard key={room.roomId} room={room} query={query} onOpen={() => roomsApi.view(room.roomId).catch(() => {})} />
          ))}
        </div>
      )}
      {data?.total === 0 && !error && (
        <div className="card space-y-2 text-center text-sm text-slate-500">
          <p className="text-3xl">🛏️</p>
          {search.checkIn && search.checkOut && (
            <p className="text-xs">{search.checkIn.slice(5)} ~ {search.checkOut.slice(5)} · {search.guests}명</p>
          )}
          <p className="font-medium text-slate-800">
            {search.checkIn ? "선택한 날짜에 예약 가능한 객실이 없어요." : "조건에 맞는 객실이 없어요."}
          </p>
          <p>날짜나 인원을 바꿔 보세요.</p>
          <button className="btn-primary mt-1" onClick={showAll}>전체 추천 보기</button>
        </div>
      )}
      {data && !error && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
    </div>
  );
}
