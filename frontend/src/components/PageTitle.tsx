export default function PageTitle({ code, title, desc }: { code?: string; title: string; desc?: string }) {
  return (
    <div className="mb-6">
      {code && <p className="text-xs font-semibold tracking-wide text-blue-600">{code}</p>}
      <h1 className="text-2xl font-bold">{title}</h1>
      {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
    </div>
  );
}
