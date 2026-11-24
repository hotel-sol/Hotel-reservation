import AdminGuard from "./AdminGuard";

// 관리자 메뉴는 상단 Header 가 보여 주므로 좌측 패널 없이 본문만 둔다 (손님 화면과 같은 배치)
export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return <AdminGuard>{children}</AdminGuard>;
}
