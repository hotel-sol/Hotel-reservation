/* 공통 상단 메뉴(페이지 분할). 화면설계서 ADM-001~003, ROOM-001의 "HOTEL" 머리줄.
 *
 * 로그인한 사람의 member.role로 메뉴를 고른다.
 *   ADMIN      → HOTEL 관리자 · 객실 관리 · 예약 일자 관리 · 예약 관리 · OOO님 · 로그아웃
 *   USER       → HOTEL · 객실 추천 · 내 예약 · OOO님 · 로그아웃   (OOO님 → 내 정보 /mypage)
 *   로그인 안 함 → HOTEL · 객실 추천 · 로그인 · 회원가입
 *
 * 쓰는 법: 페이지 맨 위에 두 줄.
 *   <header data-hotel-header></header>          (관리자 전용 화면은 data-hotel-header="admin")
 *   <script src="/layout/layout.js"></script>
 * "admin" 화면에 관리자가 아닌 사람이 오면 로그인 화면으로 보낸다. 진짜 막는 건 API(401/403)다.
 */
(() => {
  // 회원 기능(backend/member, 자체 회원가입)의 주소. /members/me는 로그인 상태면 200 {memberId, loginId, name, role}, 아니면 401.
  const ME_URL = "/members/me";
  const LOGIN_URL = "/login";
  const SIGNUP_URL = "/signup";
  const MYPAGE_URL = "/mypage";
  const LOGOUT_URL = "/logout";

  // ponytail: 메뉴를 코드에 고정. MENU 테이블(공통, role 칸)과 같은 내용이고, 메뉴 API가 생기면 거기서 받아 온다.
  const MENUS = {
    ADMIN: {
      sub: "관리자",
      items: [
        { name: "객실 관리", url: "/admin/rooms/page" },             // ADM-001
        { name: "예약 일자 관리", url: "/admin/closed-dates/page" }, // ADM-002
        { name: "예약 관리", url: "/admin/reservations/page" },      // ADM-003
      ],
    },
    USER: {
      sub: "",
      items: [
        { name: "객실 추천", url: "/rooms/page" },        // ROOM-001
        { name: "내 예약", url: "/reservations/page" },
      ],
    },
    GUEST: {
      sub: "",
      items: [{ name: "객실 추천", url: "/rooms/page" }],
    },
  };

  const style = document.createElement("style");
  style.textContent = `
    .hotel-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
      min-height: 26px; padding: 20px 28px; border-bottom: 1px solid #e5e7eb; background: #fff;
      font-family: system-ui, "Malgun Gothic", sans-serif; }
    .hotel-header .logo { font-size: 18px; font-weight: 700; letter-spacing: 3px; color: #1f2937; text-decoration: none; }
    .hotel-header .logo small { font-size: 12px; font-weight: 400; letter-spacing: 0; color: #6b7280; margin-left: 6px; }
    .hotel-header nav { display: flex; gap: 22px; flex-wrap: wrap; }
    .hotel-header nav a { font-size: 14px; color: #6b7280; text-decoration: none; }
    .hotel-header nav a:hover { color: #1f2937; }
    .hotel-header nav a[aria-current="page"] { color: #111827; font-weight: 700; }
  `;
  document.head.append(style);

  const GUEST = { role: "GUEST", name: "" };

  async function currentMember() {
    try {
      const res = await fetch(ME_URL, { credentials: "same-origin" });
      if (!res.ok) return GUEST;                   // 401 = 로그인 안 함
      const me = await res.json();
      return { role: me.role === "ADMIN" ? "ADMIN" : "USER", name: me.name };
    } catch {
      return GUEST;                                // 서버에 못 닿으면 로그인 안 한 것으로 본다
    }
  }

  const link = (text, href, current) => {
    const a = document.createElement("a");
    a.textContent = text;
    a.href = href;
    if (current) a.setAttribute("aria-current", "page");
    return a;
  };

  function render(header, { role, name }) {
    const menu = MENUS[role];
    header.className = "hotel-header";

    const logo = link("HOTEL", menu.items[0].url, false);
    logo.className = "logo";
    if (menu.sub) logo.append(Object.assign(document.createElement("small"), { textContent: menu.sub }));

    const nav = document.createElement("nav");
    nav.setAttribute("aria-label", "주 메뉴");
    for (const item of menu.items) nav.append(link(item.name, item.url, location.pathname === item.url));
    if (role === "GUEST") {
      nav.append(link("로그인", LOGIN_URL, location.pathname === LOGIN_URL),
                 link("회원가입", SIGNUP_URL, location.pathname === SIGNUP_URL));
    } else {
      nav.append(link(`${name}님`, MYPAGE_URL, location.pathname === MYPAGE_URL),   // 내 정보
                 link("로그아웃", LOGOUT_URL, false));
    }
    header.replaceChildren(logo, nav);
  }

  (async () => {
    const headers = document.querySelectorAll("[data-hotel-header]");
    if (!headers.length) return;
    const member = await currentMember();
    const adminOnly = [...headers].some((h) => h.dataset.hotelHeader === "admin");
    if (adminOnly && member.role !== "ADMIN") {
      location.replace(`${LOGIN_URL}?next=${encodeURIComponent(location.pathname)}`);
      return;
    }
    headers.forEach((h) => render(h, member));
  })();
})();
