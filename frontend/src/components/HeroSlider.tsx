"use client";

import { useEffect, useState } from "react";

// USR-REC-01 ① 대표 이미지 슬라이드. 시연용 객실 사진(public/room-photos, AI 생성)을 쓴다
const SLIDES = [
  { src: "/room-photos/suite/suite_01.jpg", title: "스위트", caption: "넓은 거실과 전망을 함께 누리는 객실" },
  { src: "/room-photos/deluxe/deluxe_01.jpg", title: "디럭스", caption: "창가에서 강과 도시를 내려다보는 객실" },
  { src: "/room-photos/family/family_01.jpg", title: "패밀리", caption: "가족이 함께 머무는 넉넉한 객실" },
  { src: "/room-photos/standard/standard_01.jpg", title: "스탠다드", caption: "깔끔하고 편안한 기본 객실" },
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
