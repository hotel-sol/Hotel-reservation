"use client";

import { useEffect, useState } from "react";
import Pagination from "@/components/Pagination";
import { adminApi, type RoomInput } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { won } from "@/lib/format";
import type { Page, Room, RoomSummary } from "@/types/api";
import RoomPhotos from "./RoomPhotos";

const EMPTY: RoomInput = { roomName: "", roomType: "", maxGuest: 2, price: 100000, description: "" };

export default function RoomManager() {
  const [keyword, setKeyword] = useState("");
  const [isActive, setIsActive] = useState<"" | "Y" | "N">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Room> | null>(null);
  const [summary, setSummary] = useState<RoomSummary | null>(null);
  const [editing, setEditing] = useState<{ id: number | null; form: RoomInput } | null>(null);
  const [photoRoom, setPhotoRoom] = useState<Room | null>(null); // 사진 관리 중인 객실
  const [error, setError] = useState("");

  // 저장·승인 뒤 다시 불러올 때 reloadKey 를 올린다
  const [reloadKey, setReloadKey] = useState(0);
  const load = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let ignore = false; // 늦게 도착한 이전 요청의 응답은 버린다
    adminApi.rooms({ keyword, isActive: isActive || undefined, page })
      .then((d) => { if (!ignore) setData(d); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [keyword, isActive, page, reloadKey]);

  // 요약 카드: 검색 · 필터와 상관없이 전체 기준. 저장 · 활성화 뒤 다시 불러온다
  useEffect(() => {
    let ignore = false;
    adminApi.roomSummary()
      .then((s) => { if (!ignore) setSummary(s); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [reloadKey]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setError("");
    try {
      if (editing.id) await adminApi.updateRoom(editing.id, editing.form);
      else setPhotoRoom(await adminApi.createRoom(editing.form)); // 새 객실은 바로 사진을 올릴 수 있게 사진 창을 연다
      setEditing(null);
      load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function toggle(room: Room) {
    const next = room.isActive === "Y" ? "N" : "Y";
    if (next === "N" && !confirm(`${room.roomName} 객실을 비활성화할까요?`)) return;
    await adminApi.setRoomActive(room.roomId, next);
    load();
  }

  const f = editing?.form;
  const setF = (patch: Partial<RoomInput>) => editing && setEditing({ ...editing, form: { ...editing.form, ...patch } });

  const closedToday = new Set(summary?.closedTodayRoomIds);
  const closedSoon = new Set(summary?.closedSoonRoomIds);

  return (
    <div className="space-y-4">
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <SummaryCard label="전체 객실" value={summary.total} />
          <SummaryCard label="판매 중" value={summary.onSale} tone="text-emerald-700" hint="오늘 손님이 예약할 수 있는 객실" />
          <SummaryCard label="오늘 휴무" value={summary.closedToday} tone="text-red-600" hint="예약 일자 관리에서 지정" />
          <SummaryCard label="휴무 예정" value={summary.closedSoon} tone="text-amber-700" hint="오늘 이후 휴무가 잡힌 객실" />
          <SummaryCard label="비활성" value={summary.inactive} tone="text-slate-500" />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <input className="input max-w-60" placeholder="객실명 검색" value={keyword} onChange={(e) => { setKeyword(e.target.value); setPage(1); }} />
        <select className="input max-w-36" value={isActive} onChange={(e) => { setIsActive(e.target.value as "" | "Y" | "N"); setPage(1); }}>
          <option value="">전체</option>
          <option value="Y">사용</option>
          <option value="N">비활성</option>
        </select>
        <button className="btn-primary ml-auto" onClick={() => setEditing({ id: null, form: EMPTY })}>+ 객실 추가</button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {editing && f && (
        <form onSubmit={save} className="card grid gap-3 sm:grid-cols-2">
          <input className="input" placeholder="객실명 *" required value={f.roomName} onChange={(e) => setF({ roomName: e.target.value })} />
          <input className="input" placeholder="객실 종류 * (디럭스, 프리미어, 이그제큐티브 스위트, 로얄 스위트)" required value={f.roomType} onChange={(e) => setF({ roomType: e.target.value })} />
          <input className="input" type="number" min={1} placeholder="최대 인원 *" required value={f.maxGuest} onChange={(e) => setF({ maxGuest: Number(e.target.value) })} />
          <input className="input" type="number" min={1} placeholder="1박 요금 *" required value={f.price} onChange={(e) => setF({ price: Number(e.target.value) })} />
          <textarea className="input sm:col-span-2" placeholder="설명" value={f.description ?? ""} onChange={(e) => setF({ description: e.target.value })} />
          <div className="flex gap-2 sm:col-span-2">
            <button className="btn-primary">{editing.id ? "수정" : "등록"}</button>
            <button type="button" className="btn-outline" onClick={() => setEditing(null)}>취소</button>
          </div>
        </form>
      )}

      {photoRoom && <RoomPhotos key={photoRoom.roomId} room={photoRoom} onClose={() => setPhotoRoom(null)} />}

      <table className="w-full overflow-hidden rounded-xl bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr><th className="p-3">번호</th><th>객실명</th><th>종류</th><th>인원</th><th>요금</th><th>조회수</th><th>상태</th><th></th></tr>
        </thead>
        <tbody>
          {data?.items.map((r) => (
            <tr key={r.roomId} className="border-t border-slate-100">
              <td className="p-3">{r.roomId}</td><td>{r.roomName}</td><td>{r.roomType}</td><td>{r.maxGuest}</td>
              <td>{won(r.price)}</td><td>{r.viewCount}</td>
              <td>
                {r.isActive === "Y" ? "사용" : <span className="text-slate-400">비활성</span>}
                {r.isActive === "Y" && closedToday.has(r.roomId) && <Badge className="bg-red-100 text-red-700">오늘 휴무</Badge>}
                {r.isActive === "Y" && closedSoon.has(r.roomId) && <Badge className="bg-amber-100 text-amber-800">휴무 예정</Badge>}
              </td>
              <td className="space-x-1 pr-3 text-right">
                <button className="btn-outline px-2 py-1" onClick={() => setEditing({ id: r.roomId, form: { roomName: r.roomName, roomType: r.roomType, maxGuest: r.maxGuest, price: r.price, description: r.description } })}>수정</button>
                <button className="btn-outline px-2 py-1" onClick={() => setPhotoRoom(r)}>사진</button>
                <button className="btn-outline px-2 py-1" onClick={() => toggle(r)}>{r.isActive === "Y" ? "비활성화" : "활성화"}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
    </div>
  );
}

function SummaryCard({ label, value, tone = "text-slate-900", hint }: { label: string; value: number; tone?: string; hint?: string }) {
  return (
    <div className="card p-4" title={hint}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${tone}`}>{value}<span className="ml-1 text-sm font-normal text-slate-400">실</span></p>
    </div>
  );
}

function Badge({ className, children }: { className: string; children: React.ReactNode }) {
  return <span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${className}`}>{children}</span>;
}
