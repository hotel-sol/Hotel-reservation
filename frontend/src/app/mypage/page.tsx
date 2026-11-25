import PageTitle from "@/components/PageTitle";
import MyInfo from "./MyInfo";

export default function MyPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <PageTitle title="마이페이지" desc="내 정보와 비밀번호를 관리해요." />
      <MyInfo />
    </div>
  );
}
