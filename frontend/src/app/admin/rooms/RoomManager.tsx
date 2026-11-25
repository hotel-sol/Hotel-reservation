"use client";

import { useEffect, useRef, useState } from "react";
import Pagination from "@/components/Pagination";
import { adminApi, type RoomInput } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { won } from "@/lib/format";
import type { Page, Room, RoomSummary } from "@/types/api";
import RoomPhotos from "./RoomPhotos";

// 객실 등급: 객실 상품 검토안 v1.9 요금표(비수기 · 시티·마운틴뷰 기준가)와 시연 데이터 40실의 값.
// 화면에서 고르기만 하고, 백엔드는 지금처럼 자유 글자로 받는다(예전 STANDARD 등도 그대로 수정 가능).
// bed · area · extra · intro 는 [예시 넣기] 설명용 (검토안 등급사양 · 시연 데이터 설명과 같은 문장)
const GRADES = [
  { name: "디럭스", price: 550_000, maxGuest: 2, bed: "퀸", area: 40, extra: "", intro: "리버·시티·마운틴 전망의 40㎡ 기본 객실. 퀸 또는 트윈" },
  { name: "프리미어", price: 700_000, maxGuest: 3, bed: "킹", area: 55, extra: "", intro: "휴식 공간을 갖춘 55㎡ 상위 객실. 킹 또는 트윈" },
  { name: "이그제큐티브 스위트", price: 1_200_000, maxGuest: 3, bed: "킹", area: 80, extra: "조식 · 라운지 포함", intro: "독립 거실이 있는 80㎡ 1베드룸 스위트. 조식·라운지 포함" },
  { name: "로얄 스위트", price: 4_000_000, maxGuest: 6, bed: "킹1 + 퀸2", area: 200, extra: "조식 · 라운지 포함", intro: "두 개의 침실과 독립 거실을 갖춘 200㎡ 최상위 스위트. 최대 6명, 조식·라운지 포함" },
];
const RIVER_VIEW_RATE = 1.1; // 리버뷰 +10%

const EMPTY: RoomInput = { roomName: "", roomType: "", maxGuest: 0, price: 0, description: "" };

// 객실명 = 호실 번호(층 2자리 + 위치 2자리) + "호" (객실 상품 검토안 OP-15). 칸에는 숫자 3~4자리만 적는다.
// 703 → 0703호, 1601 → 1601호. 이미 저장된 이름(101호 · 오션뷰 등)은 칸을 건드리지 않으면 그대로 둔다.
const ROOM_NO = /^\d{3,4}$/;
const toRoomName = (no: string) => `${no.padStart(4, "0")}호`;
const roomNoOf = (name: string) => name.match(/^(\d{3,4})호$/)?.[1] ?? "";

// [예시 넣기]: "12층 · (전망) · 킹 · 55㎡. 등급 소개" — 층은 호실 번호 앞 두 자리, 전망은 방마다 달라 직접 고친다
const VIEW_SLOT = "(전망)";
function descTemplate(g: (typeof GRADES)[number], roomNo: string) {
  const floor = ROOM_NO.test(roomNo) ? `${Number(roomNo.padStart(4, "0").slice(0, 2))}층` : "(층)";
  return [floor, VIEW_SLOT, g.bed, `${g.area}㎡`, g.extra].filter(Boolean).join(" · ") + `. ${g.intro}`;
}

type Editing = { id: number | null; form: RoomInput; roomNo: string };

export default function RoomManager() {
  const [keyword, setKeyword] = useState("");
  const [isActive, setIsActive] = useState<"" | "Y" | "N">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Room> | null>(null);
  const [summary, setSummary] = useState<RoomSummary | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [photoRoom, setPhotoRoom] = useState<Room | null>(null); // 사진 관리 중인 객실
  const [error, setError] = useState("");

  // 저장·승인 뒤 다시 불러올 때 reloadKey 를 올린다
  const [reloadKey, setReloadKey] = useState(0);
  const load = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let ignore = false; // 늦게 도착한 이전 요청의 응답은 버린다
    adminApi.rooms({ keyword, isActive: isActive || undefined, page })
      .then((d) => { if (!ignore) setData(d); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [keyword, isActive, page, reloadKey]);

  // 요약 카드: 검색 · 필터와 상관없이 전체 기준. 저장 · 활성화 뒤 다시 불러온다
  useEffect(() => {
    let ignore = false;
    adminApi.roomSummary()
      .then((s) => { if (!ignore) setSummary(s); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [reloadKey]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setError("");
    if (nameChanged && !ROOM_NO.test(editing.roomNo)) {
      setError("객실명은 숫자 3~4자리로 적어 주세요. (예: 703 → 0703호)");
      return;
    }
    const body = { ...editing.form, roomName: nameChanged ? toRoomName(editing.roomNo) : editing.form.roomName };
    try {
      if (editing.id) await adminApi.updateRoom(editing.id, body);
      else setPhotoRoom(await adminApi.createRoom(body)); // 새 객실은 바로 사진을 올릴 수 있게 사진 창을 연다
      setEditing(null);
      load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function toggle(room: Room) {
    const next = room.isActive === "Y" ? "N" : "Y";
    if (next === "N" && !confirm(`${room.roomName} 객실을 비활성화할까요?`)) return;
    await adminApi.setRoomActive(room.roomId, next);
    load();
  }

  const f = editing?.form;
  const setF = (patch: Partial<RoomInput>) => editing && setEditing({ ...editing, form: { ...editing.form, ...patch } });
  // 새 객실이거나, 수정에서 번호 칸을 원래와 다르게 바꿨을 때만 새 규칙으로 이름을 만든다
  const nameChanged = !!editing && (editing.id === null || editing.roomNo !== roomNoOf(editing.form.roomName));
  const startEdit = (r?: Room) => {
    setError("");
    setEditing(r
      ? { id: r.roomId, roomNo: roomNoOf(r.roomName), form: { roomName: r.roomName, roomType: r.roomType, maxGuest: r.maxGuest, price: r.price, description: r.description } }
      : { id: null, roomNo: "", form: EMPTY });
  };
  const grade = GRADES.find((g) => g.name === f?.roomType);
  const riverPrice = grade && Math.round(grade.price * RIVER_VIEW_RATE);
  // 설명이 아직 자동으로 채운 예시 그대로인지 (직접 고쳤으면 false → 덮어쓰지 않는다)
  const isAutoDesc = (roomNo: string) => !!grade && f?.description === descTemplate(grade, roomNo);

  // 등급을 고르면 기준 요금 · 최대 인원, 그리고 설명이 비었거나 자동 예시 그대로면 설명까지 채운다
  function pickGrade(name: string) {
    if (!editing) return;
    const g = GRADES.find((x) => x.name === name);
    if (!g) return setF({ roomType: name });
    const fillDesc = !editing.form.description?.trim() || isAutoDesc(editing.roomNo);
    setF({ roomType: g.name, price: g.price, maxGuest: g.maxGuest, ...(fillDesc ? { description: descTemplate(g, editing.roomNo) } : {}) });
  }

  // 호실 번호를 바꾸면, 설명이 자동 예시 그대로일 때 층도 따라 바꾼다 (905 → 9층)
  function changeRoomNo(value: string) {
    if (!editing) return;
    const roomNo = value.replace(/\D/g, "").slice(0, 4);
    const form = grade && isAutoDesc(editing.roomNo) ? { ...editing.form, description: descTemplate(grade, roomNo) } : editing.form;
    setEditing({ ...editing, roomNo, form });
  }

  // 설명 칸에 등급 예시를 진짜 글자로 채우고, "(전망)" 을 골라 둬서 바로 덮어쓸 수 있게 한다
  const descRef = useRef<HTMLTextAreaElement>(null);
  function fillDescription() {
    if (!editing || !grade) return;
    if (f?.description?.trim() && !confirm("설명을 예시로 바꿀까요? 지금 적힌 내용은 지워져요.")) return;
    const text = descTemplate(grade, editing.roomNo);
    setF({ description: text });
    requestAnimationFrame(() => {
      const at = text.indexOf(VIEW_SLOT);
      descRef.current?.focus();
      descRef.current?.setSelectionRange(at, at + VIEW_SLOT.length);
    });
  }

  const closedToday = new Set(summary?.closedTodayRoomIds);
  const closedSoon = new Set(summary?.closedSoonRoomIds);

  return (
    <div className="space-y-4">
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <SummaryCard label="전체 객실" value={summary.total} />
          <SummaryCard label="판매 중" value={summary.onSale} tone="text-emerald-700" hint="오늘 손님이 예약할 수 있는 객실" />
          <SummaryCard label="오늘 휴무" value={summary.closedToday} tone="text-red-600" hint="예약 일자 관리에서 지정" />
          <SummaryCard label="휴무 예정" value={summary.closedSoon} tone="text-amber-700" hint="오늘 이후 휴무가 잡힌 객실" />
          <SummaryCard label="비활성" value={summary.inactive} tone="text-slate-500" />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <input className="input max-w-60" placeholder="객실명 검색" value={keyword} onChange={(e) => { setKeyword(e.target.value); setPage(1); }} />
        <select className="input max-w-36" value={isActive} onChange={(e) => { setIsActive(e.target.value as "" | "Y" | "N"); setPage(1); }}>
          <option value="">전체</option>
          <option value="Y">사용</option>
          <option value="N">비활성</option>
        </select>
        <button className="btn-primary ml-auto" onClick={() => startEdit()}>+ 객실 추가</button>
      </div>
      {/* 등록 · 수정 칸이 열려 있으면 오류는 칸 안 [수정] 버튼 위에 보여 준다 */}
      {error && !editing && <p className="text-sm text-red-600">{error}</p>}

      {editing && f && (
        <form onSubmit={save} className="card grid gap-3 sm:grid-cols-2">
          <Field
            label="객실명 (호실 번호)"
            required
            hint={
              nameChanged && ROOM_NO.test(editing.roomNo) ? <>저장될 이름: <b className="text-slate-700">{toRoomName(editing.roomNo)}</b></>
              : !nameChanged ? <>현재 이름: <b className="text-slate-700">{f.roomName}</b>{!editing.roomNo && " (숫자를 넣으면 바뀌어요)"}</>
              : "숫자 3~4자리 · 층 2자리 + 위치 2자리 (703 → 0703호)"
            }
          >
            <Unit unit="호">
              <input
                className="input min-w-0 flex-1" inputMode="numeric" placeholder="예: 703 또는 1601" maxLength={4}
                required={nameChanged} value={editing.roomNo}
                onChange={(e) => changeRoomNo(e.target.value)}
              />
            </Unit>
          </Field>
          <Field label="객실 종류" required hint={grade ? undefined : "등급을 고르면 기준 요금과 최대 인원이 채워져요"}>
            <select className="input" required value={f.roomType} onChange={(e) => pickGrade(e.target.value)}>
              <option value="">등급을 고르세요</option>
              {GRADES.map((g) => <option key={g.name} value={g.name}>{g.name}</option>)}
              {f.roomType && !grade && <option value={f.roomType}>{f.roomType} (예전 종류)</option>}
            </select>
          </Field>
          <Field label="최대 인원" required hint={grade && `${grade.name} 기준 ${grade.maxGuest}명`}>
            <Unit unit="명">
              <input className="input min-w-0 flex-1" type="number" min={1} required value={f.maxGuest || ""} onChange={(e) => setF({ maxGuest: Number(e.target.value) })} />
            </Unit>
          </Field>
          <Field
            label="1박 요금"
            required
            hint={
              <>
                {f.price > 0 && <b className="text-slate-700">{won(f.price)}</b>}
                {grade && riverPrice && (
                  <>
                    {" "}· 눌러서 넣기:{" "}
                    <PriceButton active={f.price === grade.price} onClick={() => setF({ price: grade.price })}>기준 {won(grade.price)}</PriceButton>
                    {" · "}
                    <PriceButton active={f.price === riverPrice} onClick={() => setF({ price: riverPrice })}>리버뷰 {won(riverPrice)}</PriceButton>
                  </>
                )}
              </>
            }
          >
            <Unit unit="원">
              <input className="input min-w-0 flex-1" type="number" min={1} required value={f.price || ""} onChange={(e) => setF({ price: Number(e.target.value) })} />
            </Unit>
          </Field>
          <Field
            label="설명"
            className="sm:col-span-2"
            hint={
              <>
                {grade && <button type="button" className="btn-outline mr-2 px-2 py-0.5 text-xs" onClick={fillDescription}>{grade.name} 예시 다시 넣기</button>}
                {f.description?.includes(VIEW_SLOT) && <b className="text-amber-700">{VIEW_SLOT} 자리를 리버뷰 · 시티뷰 · 마운틴뷰로 고쳐 주세요. </b>}
                손님 추천 카드에 앞 2줄이 보여요. (선택, 최대 1000자)
              </>
            }
          >
            <textarea ref={descRef} className="input" maxLength={1000} placeholder="객실 종류를 고르면 등급 설명이 자동으로 채워져요" value={f.description ?? ""} onChange={(e) => setF({ description: e.target.value })} />
          </Field>
          {error && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2">{error}</p>
          )}
          <div className="flex gap-2 sm:col-span-2">
            <button className="btn-primary">{editing.id ? "수정" : "등록"}</button>
            <button type="button" className="btn-outline" onClick={() => { setEditing(null); setError(""); }}>취소</button>
          </div>
        </form>
      )}

      {photoRoom && <RoomPhotos key={photoRoom.roomId} room={photoRoom} onClose={() => setPhotoRoom(null)} />}

      <table className="w-full overflow-hidden rounded-xl bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr><th className="p-3">번호</th><th>객실명</th><th>종류</th><th>인원</th><th>요금</th><th>조회수</th><th>상태</th><th></th></tr>
        </thead>
        <tbody>
          {data?.items.map((r) => (
            <tr key={r.roomId} className="border-t border-slate-100">
              <td className="p-3">{r.roomId}</td><td>{r.roomName}</td><td>{r.roomType}</td><td>{r.maxGuest}</td>
              <td>{won(r.price)}</td><td>{r.viewCount}</td>
              <td>
                {r.isActive === "Y" ? "사용" : <span className="text-slate-400">비활성</span>}
                {r.isActive === "Y" && closedToday.has(r.roomId) && <Badge className="bg-red-100 text-red-700">오늘 휴무</Badge>}
                {r.isActive === "Y" && closedSoon.has(r.roomId) && <Badge className="bg-amber-100 text-amber-800">휴무 예정</Badge>}
              </td>
              <td className="space-x-1 pr-3 text-right">
                <button className="btn-outline px-2 py-1" onClick={() => startEdit(r)}>수정</button>
                <button className="btn-outline px-2 py-1" onClick={() => setPhotoRoom(r)}>사진</button>
                <button className="btn-outline px-2 py-1" onClick={() => toggle(r)}>{r.isActive === "Y" ? "비활성화" : "활성화"}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
    </div>
  );
}

function SummaryCard({ label, value, tone = "text-slate-900", hint }: { label: string; value: number; tone?: string; hint?: string }) {
  return (
    <div className="card p-4" title={hint}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${tone}`}>{value}<span className="ml-1 text-sm font-normal text-slate-400">실</span></p>
    </div>
  );
}

// 입력 칸 + 위쪽 이름표 + 아래쪽 안내
function Field({ label, required, hint, className = "", children }: {
  label: string; required?: boolean; hint?: React.ReactNode; className?: string; children: React.ReactNode;
}) {
  return (
    <label className={`block space-y-1 ${className}`}>
      <span className="block text-sm font-medium text-slate-700">
        {label}{required && <span className="ml-0.5 text-red-500">*</span>}
      </span>
      {children}
      {hint && <span className="block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

// 요금 넣기 버튼: 지금 요금과 같으면 ✓ 표시
function PriceButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className={active ? "font-semibold text-slate-700" : "text-blue-600 underline"}>
      {active && "✓ "}{children}
    </button>
  );
}

// 숫자 칸 오른쪽에 단위(명 · 원)
function Unit({ unit, children }: { unit: string; children: React.ReactNode }) {
  return (
    <span className="flex items-center gap-2">
      {children}
      <span className="text-sm text-slate-500">{unit}</span>
    </span>
  );
}

function Badge({ className, children }: { className: string; children: React.ReactNode }) {
  return <span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${className}`}>{children}</span>;
}
