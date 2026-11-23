"use client";

import { useEffect, useRef, useState } from "react";
import { adminApi } from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import { fileUrl } from "@/lib/format";
import type { AttachFile, Room } from "@/types/api";

const MAX = 5; // 객실당 최대 사진 수 (백엔드 files.py 와 같음)

/** 객실 사진 관리: 목록 · 올리기(jpg·png, 여러 장) · 삭제. 첫 장이 추천 카드 대표 사진. */
export default function RoomPhotos({ room, onClose }: { room: Room; onClose: () => void }) {
  const [photos, setPhotos] = useState<AttachFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let ignore = false;
    adminApi.roomPhotos(room.roomId)
      .then((d) => { if (!ignore) setPhotos(d); })
      .catch((e: ApiError) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [room.roomId, reloadKey]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setError("");
    const left = MAX - photos.length;
    const picked = Array.from(files);
    if (picked.length > left) {
      setError(`사진은 ${MAX}장까지예요. ${left}장만 더 올릴 수 있습니다.`);
      return;
    }
    setBusy(true);
    try {
      for (const f of picked) await adminApi.uploadRoomPhoto(room.roomId, f); // 순서대로 (첫 장 = 대표 사진)
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
      setReloadKey((k) => k + 1);
    }
  }

  async function remove(p: AttachFile) {
    if (!confirm(`${p.originalName} 사진을 삭제할까요?`)) return;
    try {
      await adminApi.deleteFile(p.fileId);
    } catch (err) {
      setError((err as ApiError).message);
    }
    setReloadKey((k) => k + 1);
  }

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="font-semibold">{room.roomName} 사진</h3>
        <span className="text-sm text-slate-500">{photos.length} / {MAX}장 · 첫 장이 대표 사진</span>
        <button type="button" className="btn-outline ml-auto px-2 py-1" onClick={onClose}>닫기</button>
      </div>

      {photos.length === 0 && <p className="text-sm text-slate-500">아직 사진이 없습니다.</p>}
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {photos.map((p, i) => (
          <li key={p.fileId} className="space-y-1">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={fileUrl(p.savedPath)} alt={p.originalName} className="aspect-[4/3] w-full rounded-lg object-cover" />
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span className="truncate">{i === 0 ? "★ 대표 · " : ""}{p.originalName}</span>
              <button type="button" className="text-red-600" onClick={() => remove(p)}>삭제</button>
            </div>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center gap-2">
        {/* 기본 파일 입력은 스타일 초기화로 글자만 보여서, 숨기고 버튼 모양 label 로 연다 */}
        <label
          className={`btn-primary ${busy || photos.length >= MAX ? "pointer-events-none opacity-50" : "cursor-pointer"}`}
        >
          + 사진 올리기 (jpg·png, 여러 장 선택 가능)
          <input
            ref={inputRef}
            type="file"
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            multiple
            disabled={busy || photos.length >= MAX}
            onChange={(e) => upload(e.target.files)}
            className="hidden"
          />
        </label>
        {busy && <span className="text-sm text-slate-500">올리는 중…</span>}
        {photos.length >= MAX && <span className="text-sm text-slate-500">최대 {MAX}장을 모두 올렸습니다. 바꾸려면 먼저 삭제하세요.</span>}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
