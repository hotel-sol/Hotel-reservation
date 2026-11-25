# 시연용 객실 사진 (room-photos)

객실 종류별 시연용 사진 36장입니다. 종류마다 9장씩 있습니다.

| 폴더 | 객실 종류 | 파일 |
|---|---|---|
| `standard/` | STANDARD | `standard_01.jpg` ~ `standard_09.jpg` |
| `deluxe/` | DELUXE | `deluxe_01.jpg` ~ `deluxe_09.jpg` |
| `family/` | FAMILY | `family_01.jpg` ~ `family_09.jpg` |
| `suite/` | SUITE | `suite_01.jpg` ~ `suite_09.jpg` |

- **AI로 만든 사진입니다.** Stable Diffusion XL을 로컬 GPU에서 돌려 만들었고, 실제 호텔 사진이 아닙니다. 사람과 글자는 넣지 않았습니다. 발표 자료에 "객실 사진은 AI로 생성"이라고 적어 주세요.
- 1152×864(4:3) jpg이고, 한 장에 약 100~200KB입니다.
- `frontend/public/` 아래에 있으므로 배포(Vercel 등)하면 코드와 함께 올라가고, `/room-photos/<종류>/<파일>` 주소로 열립니다.

## 시드 데이터에서 쓰는 법

`attach_file.saved_path`에 `room-photos/...` 경로를 넣으면 됩니다. 화면의 `fileUrl()`이 앞에 `/`를 붙여 이 폴더의 사진을 엽니다. 첫 번째 파일이 추천 카드의 대표 사진입니다.

```sql
INSERT INTO attach_file (target_type, target_id, original_name, saved_path, file_size)
VALUES ('ROOM', 1, 'standard_01.jpg', 'room-photos/standard/standard_01.jpg', 125468);
```

관리 화면에서 직접 올린 사진은 `uploads/rooms/...`에 저장되며 이 폴더와는 별개입니다.
