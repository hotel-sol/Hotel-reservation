import { Suspense } from "react";
import PageTitle from "@/components/PageTitle";
import ReservationSteps from "../ReservationSteps";
import ReservationForm from "./ReservationForm";

export default function NewReservationPage() {
  return (
    <>
      <PageTitle title="객실 예약" />
      <ReservationSteps current={2} />
      <Suspense fallback={<p className="text-sm text-slate-500">불러오는 중…</p>}>
        <ReservationForm />
      </Suspense>
    </>
  );
}
