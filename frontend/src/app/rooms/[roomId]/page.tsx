import { Suspense } from "react";
import RoomDetail from "./RoomDetail";

export default function RoomDetailPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">불러오는 중…</p>}>
      <RoomDetail />
    </Suspense>
  );
}
