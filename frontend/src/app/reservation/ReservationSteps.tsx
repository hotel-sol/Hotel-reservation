/**
 * 예약 단계 표시 (Step 2 4B): 객실 선택 → 정보 입력 → 완료
 * current: 지금 단계 번호(1~3). 앞 단계는 "완료"로, 지금 단계는 진하게 보인다.
 */
const STEPS = ["객실 선택", "정보 입력", "완료"] as const;

export default function ReservationSteps({ current }: { current: 1 | 2 | 3 }) {
  return (
    <ol className="mb-6 flex items-center gap-2 text-sm" aria-label="예약 단계">
      {STEPS.map((label, i) => {
        const step = i + 1;
        const done = step < current;
        const now = step === current;
        return (
          <li key={label} className="flex items-center gap-2" aria-current={now ? "step" : undefined}>
            {i > 0 && <span className={`h-px w-6 sm:w-10 ${done || now ? "bg-blue-600" : "bg-slate-300"}`} />}
            <span
              className={[
                "flex size-6 items-center justify-center rounded-full text-xs font-semibold",
                now ? "bg-blue-600 text-white" : done ? "bg-blue-100 text-blue-700" : "bg-slate-200 text-slate-500",
              ].join(" ")}
            >
              {done ? "✓" : step}
            </span>
            <span className={now ? "font-semibold text-slate-900" : done ? "text-blue-700" : "text-slate-400"}>
              {label}
              <span className="sr-only">{done ? " (완료)" : now ? " (현재 단계)" : ""}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
