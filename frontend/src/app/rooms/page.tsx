import { Suspense } from "react";
import PageTitle from "@/components/PageTitle";
import RoomRecommend from "./RoomRecommend";

export default function RoomsPage() {
  return (
    <>
      <PageTitle title="객실 추천" desc="날짜와 인원을 넣으면 예약 가능한 객실만 보여드려요." />
      <Suspense fallback={<p className="text-sm text-slate-500">불러오는 중…</p>}>
        <RoomRecommend />
      </Suspense>
    </>
  );
}
