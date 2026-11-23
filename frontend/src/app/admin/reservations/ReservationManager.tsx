"use client";

import { useCallback, useEffect, useState } from "react";
import Pagination from "@/components/Pagination";
import StatusBadge from "@/components/StatusBadge";
import { adminApi } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { won } from "@/lib/format";
import type { Page, Reservation, ReservationStatus } from "@/types/api";

const TABS: { value: ReservationStatus | ""; label: string }[] = [
  { value: "", label: "전체" },
  { value: "PENDING", label: "승인 대기" },
  { value: "APPROVED", label: "승인" },
  { value: "CANCELED", label: "취소" },
];

export default function ReservationManager() {
  const [status, setStatus] = useState<ReservationStatus | "">("PENDING");
  const [filter, setFilter] = useState({ from: "", to: "", keyword: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Reservation> | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    adminApi.reservations({ status, ...filter, page }).then(setData).catch((e: ApiError) => setError(e.message));
  }, [status, filter, page]);

  useEffect(load, [load]);

  async function act(r: Reservation, action: "approve" | "cancel") {
    const label = action === "approve" ? "승인" : "취소";
    const memo = r.requestMemo ? `\n요청 사항: ${r.requestMemo}` : "";
    if (!confirm(`#${r.reservationId} ${r.memberName} / ${r.roomName}\n${r.checkInDate} ~ ${r.checkOutDate}${memo}\n\n${label}할까요?`)) return;
    try {
      await adminApi[action](r.reservationId);
      load();
    } catch (err) {
      alert((err as ApiError).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-1">
        {TABS.map((t) => (
          <button key={t.value} onClick={() => { setStatus(t.value); setPage(1); }}
            className={`rounded-full px-3 py-1 text-sm ${status === t.value ? "bg-slate-900 text-white" : "bg-white"}`}>
            {t.label}
          </button>
        ))}
      </div>
      <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); const fd = new FormData(e.currentTarget); setFilter({ from: String(fd.get("from")), to: String(fd.get("to")), keyword: String(fd.get("keyword")) }); setPage(1); }}>
        <input name="from" type="date" className="input max-w-40" />
        <input name="to" type="date" className="input max-w-40" />
        <input name="keyword" className="input max-w-60" placeholder="예약자명 또는 예약 번호" />
        <button className="btn-outline">검색</button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <table className="w-full overflow-hidden rounded-xl bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr><th className="p-3">번호</th><th>예약자</th><th>객실</th><th>일정</th><th>인원</th><th>금액</th><th>상태</th><th></th></tr>
        </thead>
        <tbody>
          {data?.items.map((r) => (
            <tr key={r.reservationId} className="border-t border-slate-100">
              <td className="p-3">{r.reservationId}</td><td>{r.memberName}</td><td>{r.roomName}</td>
              <td>{r.checkInDate} ~ {r.checkOutDate}</td><td>{r.guestCount}</td><td>{won(r.totalPrice)}</td>
              <td><StatusBadge status={r.status} /></td>
              <td className="space-x-1 pr-3 text-right">
                {r.status === "PENDING" && <button className="btn-primary px-2 py-1" onClick={() => act(r, "approve")}>승인</button>}
                {r.status !== "CANCELED" && <button className="btn-outline px-2 py-1" onClick={() => act(r, "cancel")}>취소</button>}
              </td>
            </tr>
          ))}
          {data?.items.length === 0 && <tr><td colSpan={8} className="p-6 text-center text-slate-400">예약이 없습니다.</td></tr>}
        </tbody>
      </table>
      {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
    </div>
  );
}
