"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import type { ClosedDate } from "@/types/api";

/**
 * TODO(ADM-002)
 *  - 객실 선택 드롭다운 (adminApi.rooms)
 *  - 월 달력: 날짜별 휴무 여부 + 예약 수, 지난 날짜 선택 불가
 *  - 날짜 클릭 → 휴무 지정 (POST /admin/closed-dates, 백엔드 구현 필요)
 */
export default function ClosedDateManager() {
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [rows, setRows] = useState<ClosedDate[]>([]);
  const [error, setError] = useState("");

  // 저장·승인 뒤 다시 불러올 때 reloadKey 를 올린다
  const [reloadKey, setReloadKey] = useState(0);
  const load = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let ignore = false; // 늦게 도착한 이전 요청의 응답은 버린다
    adminApi.closedDates(month)
      .then((d) => { if (!ignore) setRows(d); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [month, reloadKey]);

  async function remove(id: number) {
    if (!confirm("휴무를 해제할까요?")) return;
    await adminApi.deleteClosedDate(id);
    load();
  }

  return (
    <div className="space-y-4">
      <input type="month" className="input max-w-48" value={month} onChange={(e) => setMonth(e.target.value)} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="card">
        <h2 className="mb-3 font-semibold">이번 달 호텔 전체 휴무일</h2>
        {rows.length === 0 ? (
          <p className="text-sm text-slate-400">휴무일이 없습니다.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {rows.map((r) => (
              <li key={r.closedDateId} className="flex items-center justify-between py-2">
                <span>{r.closedDate} <span className="text-slate-500">{r.reason}</span></span>
                <button className="btn-outline px-2 py-1" onClick={() => remove(r.closedDateId)}>해제</button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
