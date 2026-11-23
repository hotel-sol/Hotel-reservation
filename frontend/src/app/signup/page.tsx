import PageTitle from "@/components/PageTitle";
import SignupForm from "./SignupForm";

export default function SignupPage() {
  return (
    <div className="mx-auto max-w-sm">
      <PageTitle title="회원가입" />
      <SignupForm />
    </div>
  );
}
