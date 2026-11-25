import AuthLayout from "@/components/AuthLayout";
import PasswordResetForm from "./PasswordResetForm";

export default function PasswordResetPage() {
  return (
    <AuthLayout
      photo="/room-photos/standard/standard_01.jpg"
      tagline="비밀번호를 잊으셨나요?"
      points={["아이디와 가입할 때 쓴 이메일로 확인해요", "확인되면 바로 새 비밀번호로 바꿔요"]}
      title="비밀번호 찾기"
      desc="아이디와 가입할 때 쓴 이메일이 맞으면 새 비밀번호로 바꿔요."
    >
      <PasswordResetForm />
    </AuthLayout>
  );
}
