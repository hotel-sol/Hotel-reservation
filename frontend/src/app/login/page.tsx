import { Suspense } from "react";
import PageTitle from "@/components/PageTitle";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-sm">
      <PageTitle title="로그인" />
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
