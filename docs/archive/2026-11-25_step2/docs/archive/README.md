# 과거 자료 (기획 · 설계 단계)

해커톤 1일차(11-19)~2일차(11-23)에 만든 설계 자료입니다. **기록으로만 남기고, 지금 기준은 아닙니다.**
지금 기준 문서는 [`../../DevelopDoc/`](../../DevelopDoc/)와 [`../ARCHITECTURE.md`](../ARCHITECTURE.md), 테이블 정의는 [`../hotel_reservation_ddl.sql`](../hotel_reservation_ddl.sql)입니다.

| 파일 | 내용 | 만든 때 |
|---|---|---|
| [`설계서_1-5번_11-23.md`](설계서_1-5번_11-23.md) | 1~5번 파트 DB 설계(ERD) · 화면 설계서 | 11-23 |
| [`images/`](images/) | 화면 설계서 그림 6장 (위 설계서가 씀) | 11-23 |
| [`1번부터5번ERD/`](1번부터5번ERD/) | 전체 ERD 그림 · 설계서 HTML 판 | 11-20 |

## 지금과 달라진 점

| 설계 때 | 지금 |
|---|---|
| DB: MariaDB · MSSQL 후보 | **Supabase(PostgreSQL)** 팀 프로젝트 하나, 스키마로 나눔(공용 `hotel`, 각자 `hotel_<이름>`) |
| 백엔드 폴더 여러 개(`backend_v1` 등) | `backend/` 하나 (FastAPI + SQLAlchemy) |
| 객실별 '판매 중지' 따로 관리 | 예약 일자 관리의 **객실별 휴무**(`closed_date.room_id`)로 흡수 |
| 휴무는 오늘부터만 지정 | 지난 날짜도 지정 · 해제 가능(그날 묵은 예약이 있으면 불가) |
| 객실 사진 업로드 501(준비 중) | 구현(jpg · png, 객실당 5장, `backend/uploads/`) |
| 시각은 UTC | DB 시간대 `Asia/Seoul` (11-24부터. 그전 기록은 UTC) |
