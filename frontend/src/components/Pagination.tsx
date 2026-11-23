"use client";

export default function Pagination({
  page,
  size,
  total,
  onChange,
}: {
  page: number;
  size: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const last = Math.max(1, Math.ceil(total / size));
  if (last <= 1) return null;
  return (
    <div className="mt-6 flex justify-center gap-1">
      {Array.from({ length: last }, (_, i) => i + 1).map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`h-9 w-9 rounded-md text-sm ${p === page ? "bg-blue-600 text-white" : "bg-white hover:bg-slate-100"}`}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
