import PageTitle from "@/components/PageTitle";
import PasswordResetForm from "./PasswordResetForm";

export default function PasswordResetPage() {
  return (
    <div className="mx-auto max-w-sm">
      <PageTitle title="비밀번호 찾기" desc="아이디와 가입할 때 쓴 이메일이 맞으면 새 비밀번호로 바꿔요." />
      <PasswordResetForm />
    </div>
  );
}
