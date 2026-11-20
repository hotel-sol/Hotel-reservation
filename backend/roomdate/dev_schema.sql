-- =========================================================
-- 호텔 예약 시스템 DDL (MySQL 8.0 이상)
-- 작성자: 조준엽 / 작성일: 2026-11-20
-- 테이블 6개: member, room, reservation, closed_date, attach_file, menu
-- (팀 공유 DDL 원문. 테스트 DB 생성용으로만 복사, 수정하지 않음)
-- =========================================================

DROP TABLE IF EXISTS reservation;
DROP TABLE IF EXISTS closed_date;
DROP TABLE IF EXISTS attach_file;
DROP TABLE IF EXISTS menu;
DROP TABLE IF EXISTS room;
DROP TABLE IF EXISTS member;

CREATE TABLE member (
    member_id   BIGINT       NOT NULL AUTO_INCREMENT          COMMENT '회원 번호',
    login_id    VARCHAR(50)  NOT NULL                         COMMENT '로그인 아이디',
    password    VARCHAR(255) NOT NULL                         COMMENT '비밀번호 (암호화해서 저장)',
    name        VARCHAR(50)  NOT NULL                         COMMENT '이름',
    phone       VARCHAR(20)                                   COMMENT '전화번호',
    email       VARCHAR(100)                                  COMMENT '이메일',
    role        VARCHAR(10)  NOT NULL DEFAULT 'USER'          COMMENT 'USER(손님) / ADMIN(관리자)',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '가입한 시각',
    PRIMARY KEY (member_id),
    UNIQUE KEY uk_member_login_id (login_id),
    UNIQUE KEY uk_member_email (email),
    CONSTRAINT ck_member_role CHECK (role IN ('USER', 'ADMIN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='회원';

CREATE TABLE room (
    room_id      BIGINT        NOT NULL AUTO_INCREMENT          COMMENT '객실 번호',
    room_name    VARCHAR(100)  NOT NULL                         COMMENT '객실 이름',
    room_type    VARCHAR(50)   NOT NULL                         COMMENT '객실 종류',
    max_guest    INT           NOT NULL                         COMMENT '최대 인원',
    price        INT           NOT NULL                         COMMENT '1박 요금',
    description  VARCHAR(1000)                                  COMMENT '객실 설명',
    view_count   INT           NOT NULL DEFAULT 0               COMMENT '조회수 (추천 점수에 사용)',
    is_active    CHAR(1)       NOT NULL DEFAULT 'Y'             COMMENT '사용 여부 Y / N (N = 비활성화)',
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록한 시각',
    PRIMARY KEY (room_id),
    UNIQUE KEY uk_room_name (room_name),
    CONSTRAINT ck_room_max_guest CHECK (max_guest >= 1),
    CONSTRAINT ck_room_price     CHECK (price > 0),
    CONSTRAINT ck_room_is_active CHECK (is_active IN ('Y', 'N'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='객실';

CREATE TABLE closed_date (
    closed_date_id  BIGINT        NOT NULL AUTO_INCREMENT          COMMENT '휴무 번호',
    room_id         BIGINT                                         COMMENT '객실 번호 (NULL = 호텔 전체 휴무)',
    closed_date     DATE          NOT NULL                         COMMENT '쉬는 날짜',
    reason          VARCHAR(200)                                   COMMENT '사유',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록한 시각',
    PRIMARY KEY (closed_date_id),
    UNIQUE KEY uk_closed_room_date (room_id, closed_date),
    KEY idx_closed_date (closed_date),
    CONSTRAINT fk_closed_date_room FOREIGN KEY (room_id) REFERENCES room (room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='예약 일자 (휴무일)';

CREATE TABLE reservation (
    reservation_id  BIGINT       NOT NULL AUTO_INCREMENT          COMMENT '예약 번호',
    member_id       BIGINT       NOT NULL                         COMMENT '예약한 회원',
    room_id         BIGINT       NOT NULL                         COMMENT '예약한 객실',
    check_in_date   DATE         NOT NULL                         COMMENT '입실 날짜',
    check_out_date  DATE         NOT NULL                         COMMENT '퇴실 날짜',
    guest_count     INT          NOT NULL                         COMMENT '인원',
    total_price     INT          NOT NULL                         COMMENT '총 금액',
    status          VARCHAR(10)  NOT NULL DEFAULT 'PENDING'       COMMENT 'PENDING(대기) / APPROVED(승인) / CANCELED(취소)',
    request_memo    VARCHAR(200)                                  COMMENT '요청 사항 (최대 200자)',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '예약한 시각',
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '상태 바뀐 시각',
    PRIMARY KEY (reservation_id),
    KEY idx_reservation_member (member_id),
    KEY idx_reservation_room_dates (room_id, check_in_date, check_out_date),
    KEY idx_reservation_status (status),
    CONSTRAINT fk_reservation_member FOREIGN KEY (member_id) REFERENCES member (member_id),
    CONSTRAINT fk_reservation_room   FOREIGN KEY (room_id)   REFERENCES room (room_id),
    CONSTRAINT ck_reservation_dates  CHECK (check_out_date > check_in_date),
    CONSTRAINT ck_reservation_guest  CHECK (guest_count >= 1),
    CONSTRAINT ck_reservation_price  CHECK (total_price >= 0),
    CONSTRAINT ck_reservation_status CHECK (status IN ('PENDING', 'APPROVED', 'CANCELED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='객실 예약';

CREATE TABLE attach_file (
    file_id        BIGINT        NOT NULL AUTO_INCREMENT          COMMENT '파일 번호',
    target_type    VARCHAR(30)   NOT NULL                         COMMENT '어디 파일인지 (예: ROOM)',
    target_id      BIGINT        NOT NULL                         COMMENT '그 대상의 번호',
    original_name  VARCHAR(255)  NOT NULL                         COMMENT '원래 파일 이름',
    saved_path     VARCHAR(500)  NOT NULL                         COMMENT '저장된 위치',
    file_size      BIGINT        NOT NULL                         COMMENT '파일 크기 (byte)',
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '올린 시각',
    PRIMARY KEY (file_id),
    KEY idx_attach_target (target_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='첨부파일 (공통)';

CREATE TABLE menu (
    menu_id     BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '메뉴 번호',
    parent_id   BIGINT                                 COMMENT '상위 메뉴 번호 (NULL = 맨 위 메뉴)',
    menu_name   VARCHAR(50)   NOT NULL                 COMMENT '메뉴 이름',
    menu_url    VARCHAR(200)                           COMMENT '이동할 주소',
    role        VARCHAR(10)   NOT NULL DEFAULT 'USER'  COMMENT '보이는 사람 USER / ADMIN',
    sort_order  INT           NOT NULL DEFAULT 0       COMMENT '순서',
    is_used     CHAR(1)       NOT NULL DEFAULT 'Y'     COMMENT '사용 여부 Y / N',
    PRIMARY KEY (menu_id),
    KEY idx_menu_parent (parent_id),
    CONSTRAINT fk_menu_parent  FOREIGN KEY (parent_id) REFERENCES menu (menu_id),
    CONSTRAINT ck_menu_role    CHECK (role IN ('USER', 'ADMIN')),
    CONSTRAINT ck_menu_is_used CHECK (is_used IN ('Y', 'N'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='메뉴 (공통)';
