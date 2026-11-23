import PageTitle from "@/components/PageTitle";
import RoomManager from "./RoomManager";

// AdminGuard(클라이언트)가 권한 확인 전까지 화면을 렌더링하지 않으므로 instant 검증 제외
export const instant = false;

export default function AdminRoomsPage() {
  return (
    <>
      <PageTitle code="ADM-001" title="객실 관리" desc="삭제 대신 비활성화합니다. 비활성 객실은 손님 화면에서 숨겨집니다." />
      <RoomManager />
    </>
  );
}
