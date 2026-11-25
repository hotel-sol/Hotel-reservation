import Link from "next/link";
import AuthLayout from "@/components/AuthLayout";

// 비밀번호 찾기는 시연 전까지 꺼 둔다(#67-1). 메일 서버가 없어 "아이디 + 이메일"만으로 바꾸면
// 이메일을 아는 남이 계정을 빼앗을 수 있어서. 정식은 메일 일회용 링크(1-A4)
export default function PasswordResetPage() {
  return (
    <AuthLayout
      photo="/room-photos/standard/standard_01.jpg"
      tagline="비밀번호를 잊으셨나요?"
      points={["계정을 지키려고 직접 바꾸기는 잠시 막아 두었어요", "호텔 프런트에서 본인 확인 뒤 도와드려요"]}
      title="비밀번호 찾기"
      desc="비밀번호를 잊으셨다면 호텔 프런트에 문의해 주세요."
    >
      <div className="space-y-4 text-sm">
        <p className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 leading-relaxed text-slate-700">
          지금은 이 화면에서 비밀번호를 바꿀 수 없어요.
          <br />
          아이디와 이메일만으로 바꾸면 다른 사람이 내 계정을 가져갈 수 있어서 잠시 막아 두었어요.
        </p>
        <p className="text-slate-500">비밀번호가 기억나면 바로 로그인할 수 있어요. 로그인한 뒤에는 마이페이지에서 비밀번호를 바꿀 수 있어요.</p>
        <Link href="/login" className="btn-primary w-full py-2.5">로그인으로 돌아가기</Link>
      </div>
    </AuthLayout>
  );
}
