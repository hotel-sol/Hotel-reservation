"use client";

import { useEffect, useState } from "react";
import Pagination from "@/components/Pagination";
import { adminApi, type RoomInput } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { won } from "@/lib/format";
import type { Page, Room } from "@/types/api";

const EMPTY: RoomInput = { roomName: "", roomType: "", maxGuest: 2, price: 100000, description: "" };

export default function RoomManager() {
  const [keyword, setKeyword] = useState("");
  const [isActive, setIsActive] = useState<"" | "Y" | "N">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Room> | null>(null);
  const [editing, setEditing] = useState<{ id: number | null; form: RoomInput } | null>(null);
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

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    try {
      if (editing.id) await adminApi.updateRoom(editing.id, editing.form);
      else await adminApi.createRoom(editing.form);
      // TODO(ADM-001): 사진 업로드 (POST /files, jpg·png 최대 5장)
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

  return (
    <div className="space-y-4">
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
          <input className="input" placeholder="객실 종류 * (STANDARD, DELUXE…)" required value={f.roomType} onChange={(e) => setF({ roomType: e.target.value })} />
          <input className="input" type="number" min={1} placeholder="최대 인원 *" required value={f.maxGuest} onChange={(e) => setF({ maxGuest: Number(e.target.value) })} />
          <input className="input" type="number" min={1} placeholder="1박 요금 *" required value={f.price} onChange={(e) => setF({ price: Number(e.target.value) })} />
          <textarea className="input sm:col-span-2" placeholder="설명" value={f.description ?? ""} onChange={(e) => setF({ description: e.target.value })} />
          <div className="flex gap-2 sm:col-span-2">
            <button className="btn-primary">{editing.id ? "수정" : "등록"}</button>
            <button type="button" className="btn-outline" onClick={() => setEditing(null)}>취소</button>
          </div>
        </form>
      )}

      <table className="w-full overflow-hidden rounded-xl bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr><th className="p-3">번호</th><th>객실명</th><th>종류</th><th>인원</th><th>요금</th><th>조회수</th><th>상태</th><th></th></tr>
        </thead>
        <tbody>
          {data?.items.map((r) => (
            <tr key={r.roomId} className="border-t border-slate-100">
              <td className="p-3">{r.roomId}</td><td>{r.roomName}</td><td>{r.roomType}</td><td>{r.maxGuest}</td>
              <td>{won(r.price)}</td><td>{r.viewCount}</td>
              <td>{r.isActive === "Y" ? "사용" : <span className="text-slate-400">비활성</span>}</td>
              <td className="space-x-1 pr-3 text-right">
                <button className="btn-outline px-2 py-1" onClick={() => setEditing({ id: r.roomId, form: { roomName: r.roomName, roomType: r.roomType, maxGuest: r.maxGuest, price: r.price, description: r.description } })}>수정</button>
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
