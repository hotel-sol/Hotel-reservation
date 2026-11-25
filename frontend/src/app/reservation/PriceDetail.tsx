import { nightsBetween, won } from "@/lib/format";
import type { Reservation } from "@/types/api";

/**
 * 예약 금액 표시 (4-A3): 저장된 1박 요금이 있으면 "1박 요금 × N박", 없으면(옛 예약) 총액만 (#60 R5).
 * 계산은 서버가 저장한 값만 쓰고, 화면에서 room.price 로 다시 계산하지 않는다(#60 문제 ④).
 */
export default function PriceDetail({ r }: { r: Pick<Reservation, "checkInDate" | "checkOutDate" | "pricePerNight" | "totalPrice"> }) {
  const nights = nightsBetween(r.checkInDate, r.checkOutDate);
  return (
    <span>
      <span className="font-semibold">{won(r.totalPrice)}</span>
      {r.pricePerNight != null && (
        <span className="ml-1 text-xs text-slate-500">({won(r.pricePerNight)} × {nights}박)</span>
      )}
    </span>
  );
}
