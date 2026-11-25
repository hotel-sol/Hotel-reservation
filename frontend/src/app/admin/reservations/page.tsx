import PageTitle from "@/components/PageTitle";
import ReservationManager from "./ReservationManager";

// AdminGuard(클라이언트)가 권한 확인 전까지 화면을 렌더링하지 않으므로 instant 검증 제외
export const instant = false;

export default function AdminReservationsPage() {
  return (
    <>
      <PageTitle code="ADM-003" title="예약 관리" desc="대기 → 승인·취소, 승인 → 취소만 가능. 체크인이 지난 대기 예약은 취소만, 지난 승인 예약은 변경할 수 없습니다." />
      <ReservationManager />
    </>
  );
}
