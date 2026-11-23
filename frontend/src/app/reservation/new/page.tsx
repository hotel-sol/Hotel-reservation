import { Suspense } from "react";
import PageTitle from "@/components/PageTitle";
import ReservationForm from "./ReservationForm";

export default function NewReservationPage() {
  return (
    <>
      <PageTitle code="RSV-001" title="객실 예약" />
      <Suspense fallback={<p className="text-sm text-slate-500">불러오는 중…</p>}>
        <ReservationForm />
      </Suspense>
    </>
  );
}
