-- 로컬 개발용 가상 데이터. 화면설계서(ADM-002)의 2026년 12월 예시와 맞춤.
-- 아래 두 계정은 비밀번호가 진짜 해시가 아니라 로그인할 수 없다(테스트용 자리).
-- 로그인할 관리자는 .env 의 ADMIN_PASSWORD 로 init_db 가 만드는 admin01 을 쓴다.

INSERT INTO member (login_id, password, name, phone, role) VALUES
  ('admin', 'not-a-real-hash', '관리자', '010-0000-0001', 'ADMIN'),
  ('guest1', 'not-a-real-hash', '손님1', '010-1000-0001', 'USER');

INSERT INTO room (room_name, room_type, max_guest, price, description, is_active) VALUES
  ('101호', 'STANDARD', 2, 80000, '시티뷰', 'Y'),
  ('102호', 'STANDARD', 2, 80000, '시티뷰', 'Y'),
  ('201호', 'DELUXE', 2, 120000, '오션뷰', 'Y'),
  ('301호', 'FAMILY', 4, 160000, '가든뷰', 'Y'),
  ('401호', 'SUITE', 2, 250000, '오션뷰', 'N');

-- 화면 예시: 15 · 16 · 17일 예약 1, 24 · 25일 예약 1
-- price_per_night(4-A3) · canceled_at(4-A4)는 ③단계 제약에 맞게 처음부터 채운다
INSERT INTO reservation (member_id, room_id, check_in_date, check_out_date, guest_count, total_price, status,
                         price_per_night, canceled_at) VALUES
  (2, 1, '2026-12-15', '2026-12-18', 2, 240000, 'APPROVED', 80000, NULL),
  (2, 3, '2026-12-24', '2026-12-26', 2, 240000, 'PENDING', 120000, NULL),
  (2, 2, '2026-12-20', '2026-12-21', 1, 80000, 'CANCELED', 80000, '2026-11-20 10:00');

-- 휴무일은 비워 둔다. 화면 예시의 12/31 휴무는 관리자가 직접 지정하는 시나리오다
-- (31일 클릭 → ③에 사유 입력 → 지정 → ④ 목록에 생김).

INSERT INTO menu (parent_id, menu_name, menu_url, role, sort_order) VALUES
  (NULL, '객실 관리', '/admin/rooms', 'ADMIN', 1),
  (NULL, '예약 일자 관리', '/admin/closed-dates', 'ADMIN', 2),
  (NULL, '예약 관리', '/admin/reservations', 'ADMIN', 3),
  (NULL, '객실 추천', '/rooms', 'USER', 1),
  (NULL, '내 예약', '/reservation/list', 'USER', 2),
  (NULL, '마이페이지', '/mypage', 'USER', 3);  -- 1번 요청(11-25): 헤더에 마이페이지 링크
