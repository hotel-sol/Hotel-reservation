"use client";

import { useEffect, useState } from "react";

// USR-REC-01 ① 대표 이미지 슬라이드. 시연용 객실 사진(public/room-photos, AI 생성)을 쓴다
// 등급명 · 설명은 시연 데이터(demo_seed.sql)와 같게: 로얄 스위트 · 이그제큐티브 스위트 → suite, 프리미어 → deluxe, 디럭스 → standard 사진
const SLIDES = [
  { src: "/room-photos/suite/suite_01.jpg", title: "로얄 스위트", caption: "두 개의 침실과 독립 거실을 갖춘 200㎡" },
  { src: "/room-photos/suite/suite_05.jpg", title: "이그제큐티브 스위트", caption: "독립 거실이 있는 80㎡ 1베드룸 스위트" },
  { src: "/room-photos/deluxe/deluxe_01.jpg", title: "프리미어", caption: "휴식 공간을 갖춘 55㎡ 상위 객실" },
  { src: "/room-photos/standard/standard_01.jpg", title: "디럭스", caption: "리버 · 시티 · 마운틴 전망의 40㎡ 기본 객실" },
  { src: "/room-photos/deluxe/deluxe_05.jpg", title: "오늘의 추천", caption: "날짜와 인원을 넣고 빈 객실을 찾아보세요" },
];
const INTERVAL_MS = 5000;

export default function HeroSlider() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const total = SLIDES.length;
  const go = (step: number) => setIndex((i) => (i + step + total) % total);

  useEffect(() => {
    if (paused) return;
    const timer = setInterval(() => setIndex((i) => (i + 1) % total), INTERVAL_MS);
    return () => clearInterval(timer);
  }, [paused, total, index]); // index: 손으로 넘기면 5초를 다시 센다

  const slide = SLIDES[index];
  return (
    <section className="relative h-56 overflow-hidden rounded-xl bg-slate-900 sm:h-72" aria-roledescription="carousel" aria-label="대표 객실 사진">
      {SLIDES.map((s, i) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={s.src} src={s.src} alt={`${s.title} 객실 사진`} aria-hidden={i !== index}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${i === index ? "opacity-100" : "opacity-0"}`} />
      ))}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
      <div className="absolute bottom-4 left-5 text-white" aria-live={paused ? "polite" : "off"}>
        <p className="text-xs font-semibold tracking-widest text-orange-300">HOTEL SOL</p>
        <p className="text-2xl font-bold">{slide.title}</p>
        <p className="text-sm text-white/85">{slide.caption}</p>
      </div>
      <div className="absolute right-3 top-3 flex sm:bottom-4 sm:right-4 sm:top-auto items-center gap-1 rounded-full bg-black/45 px-2 py-1 text-sm text-white">
        <span className="px-1 tabular-nums">{index + 1} / {total}</span>
        <button type="button" onClick={() => go(-1)} aria-label="이전 사진" className="rounded-full px-2 hover:bg-white/20">‹</button>
        <button type="button" onClick={() => setPaused((p) => !p)} aria-label={paused ? "자동 넘김 다시 시작" : "자동 넘김 멈춤"}
          className="rounded-full px-2 hover:bg-white/20">{paused ? "▶" : "⏸"}</button>
        <button type="button" onClick={() => go(1)} aria-label="다음 사진" className="rounded-full px-2 hover:bg-white/20">›</button>
      </div>
    </section>
  );
}
