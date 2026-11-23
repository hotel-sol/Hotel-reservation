import { STATUS_LABEL } from "@/lib/format";
import type { ReservationStatus } from "@/types/api";

const COLOR: Record<ReservationStatus, string> = {
  PENDING: "bg-amber-100 text-amber-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  CANCELED: "bg-slate-200 text-slate-600",
};

export default function StatusBadge({ status }: { status: ReservationStatus }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${COLOR[status]}`}>{STATUS_LABEL[status]}</span>;
}
