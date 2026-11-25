"use client";

import { useEffect, useRef, useState } from "react";
import Pagination from "@/components/Pagination";
import { adminApi, type RoomInput } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { won } from "@/lib/format";
import type { Page, Room, RoomGrade, RoomSummary, ViewType } from "@/types/api";
import RoomPhotos from "./RoomPhotos";

// 객실 등급은 DB 등급표(room_grade, GET /api/room-grades)에서 읽는다 (2-A1).
// 등급을 고르면 서버가 객실 종류(roomType)를 등급 이름으로 맞춘다. 예전 객실(STANDARD 등, 등급 없음)도 그대로 수정 가능.
// 전망 배율: 리버뷰 +10% (요금 = 등급 기준가 × 배율)
const VIEWS: { value: ViewType; label: string; rate: number }[] = [
  { value: "RIVER", label: "리버뷰", rate: 1.1 },
  { value: "CITY", label: "시티뷰", rate: 1 },
  { value: "MOUNTAIN", label: "마운틴뷰", rate: 1 },
];
const BEDS = ["킹", "퀸", "트윈", "킹1 + 퀸2"]; // 침대 칸 고르기 목록 (직접 적어도 됨)
// 입력 상한 (#69, 백엔드 schemas/room.py 와 같음) — 30박 총액이 DB INT 한도를 넘지 않게
const MAX_PRICE = 10_000_000;
const MAX_GUEST = 20;
const viewOf = (v: ViewType | null | undefined) => VIEWS.find((x) => x.value === v);
// 등급 기준가 × 전망 배율. 전망을 아직 안 골랐으면 기준가
const autoPrice = (g: RoomGrade, view: ViewType | null) => Math.round(g.basePrice * (viewOf(view)?.rate ?? 1));

const EMPTY: RoomInput = {
  roomName: "", roomType: "", maxGuest: 0, price: 0, description: "", gradeId: null, viewType: null, bedType: null,
};

// 객실명 = 호실 번호(층 2자리 + 위치 2자리) + "호" (객실 상품 검토안 OP-15). 칸에는 숫자 3~4자리만 적는다.
// 703 → 0703호, 1601 → 1601호. 이미 저장된 이름(101호 · 오션뷰 등)은 칸을 건드리지 않으면 그대로 둔다.
const ROOM_NO = /^\d{3,4}$/;
const toRoomName = (no: string) => `${no.padStart(4, "0")}호`;
const roomNoOf = (name: string) => name.match(/^(\d{3,4})호$/)?.[1] ?? "";

// 설명 예시: "12층 · 리버뷰 · 킹 · 55㎡. 등급 소개" — 층은 호실 번호 앞 두 자리, 전망 · 침대는 고른 값 (전망을 안 골랐으면 "(전망)")
const VIEW_SLOT = "(전망)";
function descTemplate(g: RoomGrade, roomNo: string, view: ViewType | null, bed: string | null) {
  const floor = ROOM_NO.test(roomNo) ? `${Number(roomNo.padStart(4, "0").slice(0, 2))}층` : "(층)";
  const head = [floor, viewOf(view)?.label ?? VIEW_SLOT, bed?.trim() || g.bedType, `${g.areaM2}㎡`].filter(Boolean).join(" · ");
  return g.intro ? `${head}. ${g.intro}` : head;
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
  const [listError, setListError] = useState(""); // 목록의 비활성화 · 활성화 버튼 실패 안내 (#76-5)
  const [saving, setSaving] = useState(false); // 저장 중 버튼 잠금 — 두 번 눌러 같은 객실이 두 번 저장되지 않게 (#76-4)
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [grades, setGrades] = useState<RoomGrade[]>([]);

  // 등급 4개: 한 번만 불러온다
  useEffect(() => {
    let ignore = false;
    adminApi.roomGrades()
      .then((g) => { if (!ignore) setGrades(g); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, []);

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
    if (!editing || saving) return;
    setError("");
    if (nameChanged && !ROOM_NO.test(editing.roomNo)) {
      setError("객실명은 숫자 3~4자리로 적어 주세요. (예: 703 → 0703호)");
      return;
    }
    const body = {
      ...editing.form,
      roomName: nameChanged ? toRoomName(editing.roomNo) : editing.form.roomName,
      bedType: editing.form.bedType?.trim() || null,
    };
    setSaving(true);
    try {
      if (editing.id) await adminApi.updateRoom(editing.id, body);
      else setPhotoRoom(await adminApi.createRoom(body)); // 새 객실은 바로 사진을 올릴 수 있게 사진 창을 연다
      setEditing(null);
      load();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  async function toggle(room: Room) {
    if (togglingId !== null) return;
    const next = room.isActive === "Y" ? "N" : "Y";
    if (next === "N" && !confirm(`${room.roomName} 객실을 비활성화할까요?`)) return;
    setListError("");
    setTogglingId(room.roomId);
    try {
      await adminApi.setRoomActive(room.roomId, next);
      load();
    } catch (err) {
      // 예: 앞으로 묵을 예약이 있으면 서버가 409 + "예약을 먼저 취소해 주세요" (#76-3)
      setListError(`${room.roomName}: ${(err as ApiError).message}`);
    } finally {
      setTogglingId(null);
    }
  }

  const f = editing?.form;
  const setF = (patch: Partial<RoomInput>) => editing && setEditing({ ...editing, form: { ...editing.form, ...patch } });
  // 새 객실이거나, 수정에서 번호 칸을 원래와 다르게 바꿨을 때만 새 규칙으로 이름을 만든다
  const nameChanged = !!editing && (editing.id === null || editing.roomNo !== roomNoOf(editing.form.roomName));
  const startEdit = (r?: Room) => {
    setError("");
    setEditing(r
      ? {
          id: r.roomId,
          roomNo: roomNoOf(r.roomName),
          form: {
            roomName: r.roomName, roomType: r.roomType, maxGuest: r.maxGuest, price: r.price, description: r.description,
            gradeId: r.gradeId, viewType: r.viewType, bedType: r.bedType,
          },
        }
      : { id: null, roomNo: "", form: EMPTY });
  };
  const gradeOf = (id: number | null | undefined) => grades.find((g) => g.gradeId === id);
  const grade = gradeOf(f?.gradeId);
  const gradePrice = grade && f ? autoPrice(grade, f.viewType) : 0;

  // 등급 · 전망 · 침대 · 호실 번호가 바뀔 때 쓰는 공통 함수.
  // 요금 · 설명이 "자동으로 채운 값 그대로"(또는 비어 있음)일 때만 새 값으로 다시 채운다 — 직접 고친 값은 덮어쓰지 않는다
  function change(patch: Partial<RoomInput>, roomNo = editing?.roomNo ?? "") {
    if (!editing) return;
    const before = editing.form;
    const next = { ...before, ...patch };
    const gBefore = gradeOf(before.gradeId);
    const gNext = gradeOf(next.gradeId);
    if (gNext) {
      const priceWasAuto = !before.price || (!!gBefore && before.price === autoPrice(gBefore, before.viewType));
      if (!("price" in patch) && priceWasAuto) next.price = autoPrice(gNext, next.viewType);
      const descWasAuto = !before.description?.trim()
        || (!!gBefore && before.description === descTemplate(gBefore, editing.roomNo, before.viewType, before.bedType));
      if (descWasAuto) next.description = descTemplate(gNext, roomNo, next.viewType, next.bedType);
    }
    setEditing({ ...editing, roomNo, form: next });
  }

  // 등급을 고르면 종류 · 최대 인원 · 요금(기준가 × 전망)을 채우고, 침대가 비었거나 예전 등급 기본값이면 새 등급 기본 침대로
  function pickGrade(value: string) {
    if (!editing) return;
    const g = gradeOf(Number(value));
    if (!g) return change({ gradeId: null, roomType: "" });
    const bed = editing.form.bedType?.trim();
    const bedWasDefault = !bed || bed === gradeOf(editing.form.gradeId)?.bedType;
    change({
      gradeId: g.gradeId, roomType: g.gradeName, maxGuest: g.maxGuest, price: autoPrice(g, editing.form.viewType),
      ...(bedWasDefault ? { bedType: g.bedType } : {}),
    });
  }

  // 호실 번호를 바꾸면, 설명이 자동 예시 그대로일 때 층도 따라 바꾼다 (905 → 9층)
  const changeRoomNo = (value: string) => change({}, value.replace(/\D/g, "").slice(0, 4));

  // 설명 칸에 예시를 진짜 글자로 채운다. 전망을 아직 안 골랐으면 "(전망)" 을 골라 둬서 바로 덮어쓸 수 있게
  const descRef = useRef<HTMLTextAreaElement>(null);
  function fillDescription() {
    if (!editing || !grade || !f) return;
    if (f.description?.trim() && !confirm("설명을 예시로 바꿀까요? 지금 적힌 내용은 지워져요.")) return;
    const text = descTemplate(grade, editing.roomNo, f.viewType, f.bedType);
    setF({ description: text });
    const at = text.indexOf(VIEW_SLOT);
    if (at < 0) return;
    requestAnimationFrame(() => {
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
          <Field
            label="객실 종류 (등급)"
            required
            hint={grade ? `${grade.areaM2}㎡ · 기준가 ${won(grade.basePrice)}` : "등급을 고르면 요금 · 최대 인원 · 침대 · 설명이 채워져요"}
          >
            <select
              className="input" required
              value={f.gradeId ? String(f.gradeId) : f.roomType ? "legacy" : ""}
              onChange={(e) => e.target.value !== "legacy" && pickGrade(e.target.value)}
            >
              <option value="">등급을 고르세요</option>
              {grades.map((g) => <option key={g.gradeId} value={g.gradeId}>{g.gradeName}</option>)}
              {!f.gradeId && f.roomType && <option value="legacy">{f.roomType} (예전 종류)</option>}
            </select>
          </Field>
          <Field label="전망" hint={grade ? "리버뷰는 요금 +10%" : undefined}>
            <select
              className="input"
              value={f.viewType ?? ""}
              onChange={(e) => change({ viewType: (e.target.value || null) as ViewType | null })}
            >
              <option value="">전망을 고르세요</option>
              {VIEWS.map((v) => <option key={v.value} value={v.value}>{v.label}{v.rate > 1 ? " (+10%)" : ""}</option>)}
            </select>
          </Field>
          <Field label="침대" hint={grade?.bedType ? `${grade.gradeName} 기본: ${grade.bedType}` : "목록에서 고르거나 직접 적어요"}>
            <input
              className="input" list="bed-types" maxLength={30} placeholder="예: 킹, 트윈"
              value={f.bedType ?? ""} onChange={(e) => change({ bedType: e.target.value })}
            />
            <datalist id="bed-types">{BEDS.map((b) => <option key={b} value={b} />)}</datalist>
          </Field>
          <Field label="최대 인원" required hint={grade && `${grade.gradeName} 최대 ${grade.maxGuest}명`}>
            <Unit unit="명">
              <input className="input min-w-0 flex-1" type="number" min={1} max={MAX_GUEST} required value={f.maxGuest || ""} onChange={(e) => setF({ maxGuest: Number(e.target.value) })} />
            </Unit>
          </Field>
          <Field
            label="1박 요금"
            required
            hint={
              <>
                {f.price > 0 && <b className="text-slate-700">{won(f.price)}</b>}
                {grade && (
                  <>
                    {" "}· 등급 · 전망 기준:{" "}
                    <PriceButton active={f.price === gradePrice} onClick={() => setF({ price: gradePrice })}>
                      {won(gradePrice)}{f.viewType ? ` (${viewOf(f.viewType)?.label})` : ""}
                    </PriceButton>
                  </>
                )}
              </>
            }
          >
            <Unit unit="원">
              <input className="input min-w-0 flex-1" type="number" min={1} max={MAX_PRICE} required value={f.price || ""} onChange={(e) => setF({ price: Number(e.target.value) })} />
            </Unit>
          </Field>
          <Field
            label="설명"
            className="sm:col-span-2"
            hint={
              <>
                {grade && <button type="button" className="btn-outline mr-2 px-2 py-0.5 text-xs" onClick={fillDescription}>{grade.gradeName} 예시 다시 넣기</button>}
                {f.description?.includes(VIEW_SLOT) && <b className="text-amber-700">전망을 고르면 {VIEW_SLOT} 자리가 채워져요. </b>}
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
            <button className="btn-primary" disabled={saving}>{saving ? "저장 중…" : editing.id ? "수정" : "등록"}</button>
            <button type="button" className="btn-outline" onClick={() => { setEditing(null); setError(""); }}>취소</button>
          </div>
        </form>
      )}

      {photoRoom && <RoomPhotos key={photoRoom.roomId} room={photoRoom} onClose={() => setPhotoRoom(null)} />}

      {listError && (
        <p role="alert" className="flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          <span className="flex-1">{listError}</span>
          <button type="button" className="text-red-500" aria-label="안내 닫기" onClick={() => setListError("")}>✕</button>
        </p>
      )}

      <table className="w-full overflow-hidden rounded-xl bg-white text-sm shadow-sm">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr><th className="p-3">번호</th><th>객실명</th><th>종류</th><th>전망</th><th>인원</th><th>요금</th><th>조회수</th><th>상태</th><th></th></tr>
        </thead>
        <tbody>
          {data?.items.map((r) => (
            <tr key={r.roomId} className="border-t border-slate-100">
              <td className="p-3">{r.roomId}</td><td>{r.roomName}</td><td>{r.roomType}</td>
              <td>{viewOf(r.viewType)?.label ?? <span className="text-slate-400">-</span>}</td><td>{r.maxGuest}</td>
              <td>{won(r.price)}</td><td>{r.viewCount}</td>
              <td>
                {r.isActive === "Y" ? "사용" : <span className="text-slate-400">비활성</span>}
                {r.isActive === "Y" && closedToday.has(r.roomId) && <Badge className="bg-red-100 text-red-700">오늘 휴무</Badge>}
                {r.isActive === "Y" && closedSoon.has(r.roomId) && <Badge className="bg-amber-100 text-amber-800">휴무 예정</Badge>}
              </td>
              <td className="space-x-1 pr-3 text-right">
                <button className="btn-outline px-2 py-1" onClick={() => startEdit(r)}>수정</button>
                <button className="btn-outline px-2 py-1" onClick={() => setPhotoRoom(r)}>사진</button>
                <button className="btn-outline px-2 py-1" disabled={togglingId === r.roomId} onClick={() => toggle(r)}>{r.isActive === "Y" ? "비활성화" : "활성화"}</button>
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
