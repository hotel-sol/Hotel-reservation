import { Suspense } from "react";
import PageTitle from "@/components/PageTitle";
import ReservationComplete from "./ReservationComplete";

export default function ReservationCompletePage() {
  return (
    <>
      <PageTitle code="RSV-002" title="예약 완료" desc="관리자가 승인하면 예약이 확정됩니다." />
      <Suspense fallback={<p className="text-sm text-slate-500">불러오는 중…</p>}>
        <ReservationComplete />
      </Suspense>
    </>
  );
}
