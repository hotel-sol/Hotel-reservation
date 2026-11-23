-- =========================================================
-- 호텔 예약 시스템 DDL (SQL Server 2016+)
-- 참고 저장소 docs/hotel_reservation_ddl.sql (MySQL) 을 MSSQL 로 옮긴 것.
-- 현재 개발 DB 에는 이미 만들어져 있음 → 새 DB 를 만들 때만 실행.
-- =========================================================

CREATE TABLE dbo.member (
    member_id   BIGINT        IDENTITY(1,1) NOT NULL,
    login_id    NVARCHAR(50)  NOT NULL,
    password    VARCHAR(255)  NOT NULL,             -- scrypt$salt$hash
    name        NVARCHAR(50)  NOT NULL,
    phone       VARCHAR(20)   NULL,
    email       VARCHAR(100)  NULL,
    role        VARCHAR(10)   NOT NULL DEFAULT ('USER'),
    created_at  DATETIME      NOT NULL DEFAULT (GETDATE()),
    CONSTRAINT pk_member PRIMARY KEY (member_id),
    CONSTRAINT uk_member_login_id UNIQUE (login_id),
    CONSTRAINT ck_member_role CHECK (role IN ('USER', 'ADMIN'))
);
-- email 은 NULL 허용 + 유일 → 필터 인덱스
CREATE UNIQUE INDEX uk_member_email ON dbo.member (email) WHERE email IS NOT NULL;

CREATE TABLE dbo.room (
    room_id      BIGINT          IDENTITY(1,1) NOT NULL,
    room_name    NVARCHAR(100)   NOT NULL,
    room_type    NVARCHAR(50)    NOT NULL,
    max_guest    INT             NOT NULL,
    price        INT             NOT NULL,
    description  NVARCHAR(1000)  NULL,
    view_count   INT             NOT NULL DEFAULT (0),
    is_active    CHAR(1)         NOT NULL DEFAULT ('Y'),
    created_at   DATETIME        NOT NULL DEFAULT (GETDATE()),
    CONSTRAINT pk_room PRIMARY KEY (room_id),
    CONSTRAINT uk_room_name UNIQUE (room_name),
    CONSTRAINT ck_room_max_guest CHECK (max_guest >= 1),
    CONSTRAINT ck_room_price CHECK (price > 0),
    CONSTRAINT ck_room_is_active CHECK (is_active IN ('Y', 'N'))
);

CREATE TABLE dbo.closed_date (
    closed_date_id  BIGINT         IDENTITY(1,1) NOT NULL,
    room_id         BIGINT         NULL,          -- NULL = 호텔 전체 휴무
    closed_date     DATE           NOT NULL,
    reason          NVARCHAR(200)  NULL,
    created_at      DATETIME       NOT NULL DEFAULT (GETDATE()),
    CONSTRAINT pk_closed_date PRIMARY KEY (closed_date_id),
    CONSTRAINT fk_closed_date_room FOREIGN KEY (room_id) REFERENCES dbo.room (room_id)
);
CREATE UNIQUE INDEX uk_closed_room_date ON dbo.closed_date (room_id, closed_date);
CREATE INDEX idx_closed_date ON dbo.closed_date (closed_date);

CREATE TABLE dbo.reservation (
    reservation_id  BIGINT         IDENTITY(1,1) NOT NULL,
    member_id       BIGINT         NOT NULL,
    room_id         BIGINT         NOT NULL,
    check_in_date   DATE           NOT NULL,
    check_out_date  DATE           NOT NULL,
    guest_count     INT            NOT NULL,
    total_price     INT            NOT NULL,
    status          VARCHAR(10)    NOT NULL DEFAULT ('PENDING'),
    request_memo    NVARCHAR(200)  NULL,
    created_at      DATETIME       NOT NULL DEFAULT (GETDATE()),
    updated_at      DATETIME       NOT NULL DEFAULT (GETDATE()),  -- 상태 변경 시 앱에서 갱신
    CONSTRAINT pk_reservation PRIMARY KEY (reservation_id),
    CONSTRAINT fk_reservation_member FOREIGN KEY (member_id) REFERENCES dbo.member (member_id),
    CONSTRAINT fk_reservation_room FOREIGN KEY (room_id) REFERENCES dbo.room (room_id),
    CONSTRAINT ck_reservation_dates CHECK (check_out_date > check_in_date),
    CONSTRAINT ck_reservation_guest CHECK (guest_count >= 1),
    CONSTRAINT ck_reservation_price CHECK (total_price >= 0),
    CONSTRAINT ck_reservation_status CHECK (status IN ('PENDING', 'APPROVED', 'CANCELED'))
);
CREATE INDEX idx_reservation_member ON dbo.reservation (member_id);
CREATE INDEX idx_reservation_room_dates ON dbo.reservation (room_id, check_in_date, check_out_date);
CREATE INDEX idx_reservation_status ON dbo.reservation (status);

CREATE TABLE dbo.attach_file (
    file_id        BIGINT         IDENTITY(1,1) NOT NULL,
    target_type    VARCHAR(30)    NOT NULL,       -- 예: ROOM
    target_id      BIGINT         NOT NULL,
    original_name  NVARCHAR(255)  NOT NULL,
    saved_path     NVARCHAR(500)  NOT NULL,
    file_size      BIGINT         NOT NULL,
    created_at     DATETIME       NOT NULL DEFAULT (GETDATE()),
    CONSTRAINT pk_attach_file PRIMARY KEY (file_id)
);
CREATE INDEX idx_attach_target ON dbo.attach_file (target_type, target_id);

CREATE TABLE dbo.menu (
    menu_id     BIGINT        IDENTITY(1,1) NOT NULL,
    parent_id   BIGINT        NULL,               -- NULL = 최상위 메뉴
    menu_name   NVARCHAR(50)  NOT NULL,
    menu_url    VARCHAR(200)  NULL,
    role        VARCHAR(10)   NOT NULL DEFAULT ('USER'),
    sort_order  INT           NOT NULL DEFAULT (0),
    is_used     CHAR(1)       NOT NULL DEFAULT ('Y'),
    CONSTRAINT pk_menu PRIMARY KEY (menu_id),
    CONSTRAINT fk_menu_parent FOREIGN KEY (parent_id) REFERENCES dbo.menu (menu_id),
    CONSTRAINT ck_menu_role CHECK (role IN ('USER', 'ADMIN')),
    CONSTRAINT ck_menu_is_used CHECK (is_used IN ('Y', 'N'))
);
