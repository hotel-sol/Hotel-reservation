import AuthLayout from "@/components/AuthLayout";
import SignupForm from "./SignupForm";

export default function SignupPage() {
  return (
    <AuthLayout
      photo="/room-photos/suite/suite_01.jpg"
      tagline="회원이 되면 이렇게 쓸 수 있어요"
      points={["날짜 · 인원으로 지금 예약할 수 있는 객실 추천", "온라인으로 예약 신청", "내 예약에서 승인 · 취소 상태 확인"]}
      title="회원가입"
      desc="(선택) 표시가 없는 칸은 꼭 적어 주세요."
    >
      <SignupForm />
    </AuthLayout>
  );
}
