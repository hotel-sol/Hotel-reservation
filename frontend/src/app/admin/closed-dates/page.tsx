import { Suspense } from "react";
import PageTitle from "@/components/PageTitle";
import ClosedDateManager from "./ClosedDateManager";

// AdminGuard(클라이언트)가 권한 확인 전까지 화면을 렌더링하지 않으므로 instant 검증 제외
export const instant = false;

export default function AdminClosedDatesPage() {
  return (
    <>
      <PageTitle title="예약 일자 관리" desc="전체 객실 = 호텔 전체 휴무, 특정 객실 = 그 방만 휴무. 예약이 있는 날은 지정할 수 없어요." />
      <Suspense fallback={<p className="text-sm text-slate-500">불러오는 중…</p>}>
        <ClosedDateManager />
      </Suspense>
    </>
  );
}
