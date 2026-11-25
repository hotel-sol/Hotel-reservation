import type { ReactNode } from "react";

/**
 * 1번 회원 화면(로그인 · 가입 · 비밀번호 찾기) 공통 틀: 왼쪽 객실 사진 + 오른쪽 폼.
 * 사진은 추천 화면 슬라이드와 같은 시연용 사진(public/room-photos, AI 생성). 좁은 화면에서는 사진을 숨긴다
 */
export default function AuthLayout({
  photo,
  tagline,
  points,
  title,
  desc,
  children,
}: {
  photo: string;
  tagline: string;
  points?: string[];
  title: string;
  desc?: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto grid max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm md:grid-cols-[5fr_6fr]">
      <aside className="relative hidden min-h-[520px] md:block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={photo} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/25 to-black/10" />
        <div className="absolute inset-x-0 bottom-0 space-y-3 p-7 text-white">
          <p className="text-xs font-semibold tracking-widest text-orange-300">HOTEL SOL</p>
          <p className="text-2xl font-bold leading-snug">{tagline}</p>
          {points && (
            <ul className="space-y-1.5 text-sm text-white/90">
              {points.map((p) => (
                <li key={p} className="flex gap-2"><span aria-hidden="true" className="text-orange-300">✓</span>{p}</li>
              ))}
            </ul>
          )}
        </div>
      </aside>
      <section className="p-6 sm:p-9">
        <h1 className="text-2xl font-bold">{title}</h1>
        {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
        <div className="mt-6">{children}</div>
      </section>
    </div>
  );
}
