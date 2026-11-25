"use client";

import { useEffect, useRef, useState } from "react";
import Pagination from "@/components/Pagination";
import StatusBadge from "@/components/StatusBadge";
import { adminApi } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { today, won } from "@/lib/format";
import type { Page, Reservation, ReservationStatus, ReservationStatusCounts } from "@/types/api";

/**
 * ADM-003 관리자 예약 관리
 *  ① 상태 탭      처음엔 "승인 대기". 탭 옆 숫자 = 지금 검색 조건에서 그 상태의 예약 수
 *  ② 검색         체크인 기간, 예약자명 또는 예약 번호
 *  ③ 승인 / 취소  대기: 승인 · 취소, 승인: 취소만, 취소: 없음.
 *                 체크인이 지난 예약: 대기는 취소만(승인 불가), 승인은 버튼 없음
 *  ④ 확인 팝업    예약 내용과 요청 사항을 한 번 더 보여주고 확인
 */
const TABS: { value: ReservationStatus | ""; label: string; countKey: keyof ReservationStatusCounts }[] = [
  { value: "", label: "전체", countKey: "ALL" },
  { value: "PENDING", label: "승인 대기", countKey: "PENDING" },
  { value: "APPROVED", label: "승인", countKey: "APPROVED" },
  { value: "CANCELED", label: "취소", countKey: "CANCELED" },
];

type Action = "approve" | "cancel";
const ACTION_LABEL: Record<Action, string> = { approve: "승인", cancel: "취소" };

const shortDate = (d: string) => d.slice(5).replace("-", "/");

export default function ReservationManager() {
  const [status, setStatus] = useState<ReservationStatus | "">("PENDING");
  const [filter, setFilter] = useState({ from: "", to: "", keyword: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Reservation> | null>(null);
  const [counts, setCounts] = useState<ReservationStatusCounts | null>(null);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState<{ r: Reservation; action: Action } | null>(null);

  // 승인 · 취소 뒤 다시 불러올 때 reloadKey 를 올린다
  const [reloadKey, setReloadKey] = useState(0);
  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let ignore = false; // 늦게 도착한 이전 요청의 응답은 버린다
    Promise.all([adminApi.reservations({ status, ...filter, page }), adminApi.reservationStatusCounts(filter)])
      .then(([list, c]) => {
        if (ignore) return;
        setData(list);
        setCounts(c);
        setError("");
      })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [status, filter, page, reloadKey]);

  const todayStr = today();
  // 백엔드 규칙과 같게 버튼을 보인다 (어긋나면 409 PAST_CHECK_IN)
  //  - 체크인 날(오늘)까지: 대기는 승인 · 취소, 승인은 취소
  //  - 체크인이 지남: 대기는 묵지 않은 예약이라 취소로만 정리, 승인은 묵은 기록이라 그대로 둔다
  const isPast = (r: Reservation) => r.checkInDate < todayStr;
  const canApprove = (r: Reservation) => r.status === "PENDING" && !isPast(r);
  const canCancel = (r: Reservation) => r.status === "PENDING" || (r.status === "APPROVED" && !isPast(r));

  return (
    <div className="space-y-4">
      {/* ① 상태 탭 */}
      <div className="flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button key={t.value} type="button" onClick={() => { setStatus(t.value); setPage(1); }}
            className={`rounded-full border px-3 py-1 text-sm ${
              status === t.value ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white"
            }`}>
            {t.label}
            {counts && <span className="ml-1 font-semibold">{counts[t.countKey]}</span>}
          </button>
        ))}
      </div>

      {/* ② 검색 */}
      <form className="flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          setFilter({ from: String(fd.get("from")), to: String(fd.get("to")), keyword: String(fd.get("keyword")).trim() });
          setPage(1);
        }}>
        <input name="from" type="date" aria-label="체크인 시작" className="input max-w-40" />
        <span className="text-slate-400">~</span>
        <input name="to" type="date" aria-label="체크인 끝" className="input max-w-40" />
        <input name="keyword" className="input max-w-60" placeholder="예약자명 또는 예약 번호" />
        <button className="btn-primary">검색</button>
      </form>
      {error && <p className="whitespace-pre-line text-sm text-red-600">{error}</p>}

      {/* ③ 예약 목록 */}
      <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-slate-100 text-left text-slate-600">
            <tr>
              <th className="p-3">예약 번호</th><th>예약자</th><th>객실</th><th>숙박 기간</th>
              <th>인원</th><th>금액</th><th>상태</th><th className="pr-3 text-right">관리</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((r) => (
              <tr key={r.reservationId} className="border-t border-slate-100">
                <td className="p-3">{r.reservationId}</td>
                <td>{r.memberName}</td>
                <td>{r.roomName}</td>
                <td>{r.checkInDate} ~ {r.checkOutDate}</td>
                <td>{r.guestCount}명</td>
                <td>{won(r.totalPrice)}</td>
                <td><StatusBadge status={r.status} /></td>
                <td className="space-x-1 whitespace-nowrap pr-3 text-right">
                  {r.status === "PENDING" && isPast(r) && (
                    <span className="text-xs text-amber-700">체크인 지남</span>
                  )}
                  {canApprove(r) && (
                    <button type="button" className="btn-primary px-2 py-1"
                      onClick={() => setConfirming({ r, action: "approve" })}>승인</button>
                  )}
                  {canCancel(r) && (
                    <button type="button" className="btn-outline px-2 py-1"
                      onClick={() => setConfirming({ r, action: "cancel" })}>취소</button>
                  )}
                  {!canApprove(r) && !canCancel(r) && (
                    <span className="text-slate-400" title={r.status === "CANCELED" ? "취소된 예약" : "체크인이 지난 예약"}>-</span>
                  )}
                </td>
              </tr>
            ))}
            {data?.items.length === 0 && (
              <tr><td colSpan={8} className="p-6 text-center text-slate-400">예약이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}

      {/* ④ 확인 팝업 */}
      {confirming && (
        <ConfirmDialog
          reservation={confirming.r}
          action={confirming.action}
          // 오류로 닫았어도 그 사이 상태가 바뀌었을 수 있으니 목록 · 숫자를 새로 받는다
          onClose={() => { setConfirming(null); reload(); }}
          onDone={() => { setConfirming(null); reload(); }}
        />
      )}
    </div>
  );
}

function ConfirmDialog({ reservation: r, action, onClose, onDone }: {
  reservation: Reservation;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const closeRef = useRef<HTMLButtonElement>(null);
  const label = ACTION_LABEL[action];

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function confirm() {
    setBusy(true);
    setError("");
    try {
      await adminApi[action](r.reservationId);
      onDone();
    } catch (err) {
      setError((err as ApiError).message); // 예: 체크인이 지난 예약 · 이미 바뀐 상태
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-title"
        className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <h2 id="confirm-title" className="text-lg font-semibold">예약을 {label}하시겠습니까?</h2>
        <div className="space-y-1 text-sm text-slate-600">
          <p>#{r.reservationId} {r.memberName}</p>
          <p>{r.roomName} · {shortDate(r.checkInDate)} ~ {shortDate(r.checkOutDate)} · {r.guestCount}명 · {won(r.totalPrice)}</p>
          <p>요청 사항: {r.requestMemo || "없음"}</p>
          {action === "cancel" && <p className="text-amber-700">취소하면 이 날짜는 다시 예약할 수 있게 됩니다.</p>}
        </div>
        {error && <p className="whitespace-pre-line text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button ref={closeRef} type="button" className="btn-outline" onClick={onClose}>닫기</button>
          <button type="button" className={action === "approve" ? "btn-primary" : "btn-primary bg-red-600 hover:bg-red-700"}
            disabled={busy} onClick={confirm}>
            {label}하기
          </button>
        </div>
      </div>
    </div>
  );
}
