import { Suspense } from "react";
import AuthLayout from "@/components/AuthLayout";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <AuthLayout
      photo="/room-photos/deluxe/deluxe_05.jpg"
      tagline="다시 오신 걸 환영해요"
      points={["로그인하면 바로 예약할 수 있어요", "내 예약에서 승인 상태를 확인해요"]}
      title="로그인"
      desc="아이디와 비밀번호를 입력해 주세요."
    >
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
