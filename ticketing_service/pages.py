from __future__ import annotations

import html
import json

from ticketing_service.service import TicketingConfig


BASE_STYLE = """
:root {
  --bg: #f5efe4;
  --panel: rgba(255, 251, 244, 0.95);
  --line: #decfbf;
  --ink: #191715;
  --muted: #6b6258;
  --brand: #b33a1f;
  --brand-dark: #892813;
  --success: #1e7a52;
  --warning: #b46b17;
  --shadow: 0 18px 40px rgba(63, 42, 19, 0.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  font-family: "Noto Sans KR", "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(255, 216, 156, 0.48), transparent 25%),
    radial-gradient(circle at top right, rgba(179, 58, 31, 0.18), transparent 22%),
    linear-gradient(180deg, #f7f0e4 0%, #ede4d5 100%);
}
a { color: inherit; text-decoration: none; }
button, input { font: inherit; }
.shell { max-width: 1280px; margin: 0 auto; padding: 28px 20px 64px; }
.topbar { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:20px; }
.brand { display:inline-flex; align-items:center; gap:10px; font-weight:900; }
.brand-mark {
  width: 38px; height: 38px; border-radius: 14px; color: white;
  display:inline-flex; align-items:center; justify-content:center;
  background: linear-gradient(180deg, var(--brand), var(--brand-dark));
  box-shadow: 0 10px 20px rgba(179, 58, 31, 0.24);
}
.nav { display:inline-flex; gap:10px; flex-wrap:wrap; }
.nav a, .nav button {
  border-radius: 999px; border: 1px solid var(--line); background: rgba(255,255,255,0.75);
  padding: 10px 14px; cursor: pointer;
}
.grid-hero, .grid-two, .grid-three { display:grid; gap:18px; }
.grid-hero { grid-template-columns: 320px 1fr 300px; }
.grid-two { grid-template-columns: 1.15fr 0.85fr; }
.grid-three { grid-template-columns: repeat(3, 1fr); }
.panel, .poster {
  border-radius: 28px; overflow:hidden; border:1px solid rgba(219,205,189,0.95);
  background: var(--panel); box-shadow: var(--shadow);
}
.panel-body { padding: 24px; }
.poster {
  min-height: 360px; padding: 28px; color:white;
  background:
    linear-gradient(180deg, rgba(0,0,0,0.1), rgba(0,0,0,0.35)),
    radial-gradient(circle at 50% 15%, rgba(255, 225, 182, 0.94), rgba(253, 180, 92, 0.3) 32%, transparent 54%),
    linear-gradient(180deg, #4a3422 0%, #1f1814 72%, #180f09 100%);
}
.poster h1 {
  margin: 38px 0 12px; max-width: 220px; font-size: 44px; line-height: 1.02;
  font-family: Georgia, "Times New Roman", serif;
}
.poster p { margin: 0; color: rgba(255,255,255,0.82); line-height: 1.6; }
.badge {
  display:inline-flex; border-radius:999px; padding:6px 12px; font-size:12px; font-weight:900;
  letter-spacing:0.08em; background: rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.25);
}
.flag {
  display:inline-flex; border-radius:999px; padding:6px 12px; font-size:12px; font-weight:900;
  letter-spacing:0.08em; background: rgba(179,58,31,0.1); color: var(--brand-dark); margin-bottom: 12px;
}
.title { margin:0; font-size:34px; line-height:1.18; }
.lead, .copy { color: var(--muted); line-height: 1.7; }
.cards { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; }
.card {
  border-radius:18px; padding:16px; border:1px solid var(--line); background: rgba(255,255,255,0.75);
}
.card small { display:block; margin-bottom:8px; color: var(--muted); }
.card strong { font-size:20px; }
.field { display:grid; gap:8px; margin-top: 16px; }
.field label { font-size:13px; font-weight:800; color: var(--muted); }
.field input {
  width:100%; border-radius:16px; border:1px solid #ccbda8; padding:14px 16px; background:white;
}
.button-row { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:16px; }
.button, .secondary, .ghost {
  border-radius:16px; padding:13px 16px; border:0; font-weight:900; cursor:pointer; text-align:center;
}
.button { color:white; background: linear-gradient(180deg, var(--brand), var(--brand-dark)); }
.secondary { background:#efe5d7; color:#4f463c; border:1px solid #d9cbb8; }
.ghost { background:transparent; color:var(--brand-dark); border:1px solid rgba(179,58,31,0.24); }
.status-box {
  display:flex; align-items:center; justify-content:space-between; gap:16px; padding:18px 20px;
  border-radius:22px; background: linear-gradient(90deg, rgba(179,58,31,0.1), rgba(199,152,71,0.16));
  border:1px solid rgba(179,58,31,0.14);
}
.status-box strong { display:block; margin-bottom:4px; font-size:20px; }
.pill {
  display:inline-flex; align-items:center; border-radius:999px; padding:7px 12px;
  font-size:12px; font-weight:900; letter-spacing:0.06em; text-transform:uppercase;
}
.pill.idle { background: rgba(91, 82, 71, 0.12); color: #5b5247; }
.pill.waiting { background: rgba(180,107,23,0.12); color: var(--warning); }
.pill.admitted { background: rgba(30,122,82,0.12); color: var(--success); }
.pill.holding, .pill.confirmed { background: rgba(179,58,31,0.12); color: var(--brand-dark); }
.pill.error, .pill.blocked { background: rgba(180,59,51,0.12); color: #b43b33; }
.list, .seat-grid, .logs { display:grid; gap:10px; }
.list-item {
  display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px;
  border-radius:16px; border:1px solid var(--line); background: rgba(255,255,255,0.72);
}
.list-item.me { border-color: rgba(179,58,31,0.36); background: rgba(179,58,31,0.08); }
.seat-stage {
  border-radius:22px; padding:18px; border:1px solid var(--line);
  background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(248,240,226,0.88));
}
.stage-label { text-align:center; margin-bottom:16px; color: var(--muted); font-weight:800; letter-spacing:0.12em; }
.screen {
  width:82%; margin:0 auto 22px; text-align:center; padding:12px; border-radius:999px;
  background: linear-gradient(180deg, #424242, #1f1f1f); color:white;
}
.seat-grid { grid-template-columns: repeat(2, 1fr); }
.seat {
  border-radius:18px; border:1px solid var(--line); background:white; padding:18px 14px;
  cursor:pointer; text-align:left;
}
.seat strong { display:block; font-size:19px; margin-bottom:6px; }
.seat.selected { border-color: var(--brand); background: rgba(179,58,31,0.08); }
.seat.mine { border-color: var(--success); background: rgba(30,122,82,0.08); }
.seat.taken { cursor:not-allowed; border-color:#c9b49e; background: rgba(157,137,116,0.14); }
.empty {
  padding:20px 12px; border-radius:16px; border:1px dashed var(--line);
  background: rgba(255,255,255,0.55); color:var(--muted); text-align:center;
}
.note {
  margin-top:12px; padding:14px 16px; border-radius:16px; background: rgba(255,255,255,0.78);
  border:1px solid var(--line); color: var(--muted); line-height:1.6;
}
@media (max-width: 1100px) {
  .grid-hero, .grid-two, .grid-three, .cards { grid-template-columns: 1fr; }
}
"""


def _page(title: str, body: str, script: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{BASE_STYLE}</style>
</head>
<body>
  {body}
  <script>{script}</script>
</body>
</html>
"""


def render_entry_page(config: TicketingConfig) -> str:
    body = f"""
<div class="shell">
  <div class="topbar">
    <div class="brand"><span class="brand-mark">R</span><span>PyMiniRedis Ticketing Demo</span></div>
    <div class="nav"><a href="/">랜딩</a><a href="/ops">운영 보기</a></div>
  </div>
  <section class="grid-hero">
    <article class="poster">
      <span class="badge">EXCLUSIVE OPEN</span>
      <h1>GRAND HALL LIVE</h1>
      <p>Page A 수용 인원이 차면 Page B 대기실에서 기다리고, 자리가 나면 자동으로 예매실로 이동하는 티켓팅 데모입니다.</p>
    </article>
    <section class="panel"><div class="panel-body">
      <span class="flag">ENTRY</span>
      <h2 class="title">예매 시작 페이지</h2>
      <p class="lead">사용자 ID를 입력하면 서버가 바로 입장 가능한지 판단합니다. 입장 가능하면 Page A, 아니면 Page B로 보냅니다.</p>
      <div class="cards">
        <div class="card"><small>Page A 수용 인원</small><strong>{config.max_active_users}</strong></div>
        <div class="card"><small>등록 좌석 수</small><strong>{len(config.seat_ids)}</strong></div>
        <div class="card"><small>현재 대기열</small><strong id="queueSize">-</strong></div>
      </div>
      <div class="field">
        <label for="userId">회원 아이디</label>
        <input id="userId" value="user-a" placeholder="예: user-a">
      </div>
      <div class="button-row">
        <button class="button" onclick="startEntry()">예매 시작</button>
        <button class="secondary" onclick="refreshOverview()">현황 새로고침</button>
      </div>
      <div class="note" id="entryMessage">Page A 현재 입장자와 대기열 길이는 아래 상태에서 바로 확인할 수 있습니다.</div>
    </div></section>
    <aside class="panel"><div class="panel-body">
      <span class="flag">GUIDE</span>
      <div class="list">
        <div class="list-item"><strong>Page A</strong><span>실제 예매 진행</span></div>
        <div class="list-item"><strong>Page B</strong><span>대기열 전용 페이지</span></div>
        <div class="list-item"><strong>/ops</strong><span>입장 완료자 확인용</span></div>
      </div>
      <div class="note">운영용 테스트는 <strong>/ops</strong> 화면에서 현재 입장자, 대기열, 좌석 상태를 한 번에 볼 수 있습니다.</div>
    </div></aside>
  </section>
</div>
"""
    script = """
async function api(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

async function refreshOverview() {
  const state = await api("/api/state");
  document.getElementById("queueSize").textContent = String(state.queue_size ?? 0);
  const admitted = (state.admitted_users || []).join(", ") || "없음";
  document.getElementById("entryMessage").textContent = `현재 Page A 입장자: ${admitted}. 대기열: ${state.queue_size ?? 0}명`;
}

async function startEntry() {
  const userId = document.getElementById("userId").value.trim();
  if (!userId) {
    document.getElementById("entryMessage").textContent = "회원 아이디를 먼저 입력하세요.";
    return;
  }

  const result = await api("/api/enter", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });

  if (["admitted", "holding", "confirmed"].includes(result.status)) {
    window.location.assign(`/ticketing?user_id=${encodeURIComponent(userId)}`);
    return;
  }
  if (result.status === "waiting") {
    window.location.assign(`/waiting-room?user_id=${encodeURIComponent(userId)}`);
    return;
  }
  if (result.status === "blocked") {
    document.getElementById("entryMessage").textContent = `요청이 많아 ${result.reset_in}초 뒤 다시 시도할 수 있습니다.`;
    return;
  }
  document.getElementById("entryMessage").textContent = "입장 요청 처리에 실패했습니다.";
}

refreshOverview();
setInterval(refreshOverview, 4000);
"""
    return _page("PyMiniRedis Ticket Entry", body, script)


def render_waiting_room_page(user_id: str) -> str:
    safe_user = html.escape(user_id)
    script = """
const USER_ID = __USER_ID__;
let currentStatus = null;
let currentState = null;

async function api(path) {
  const response = await fetch(path);
  return response.json();
}

function renderUsers(targetId, users) {
  const target = document.getElementById(targetId);
  if (!users.length) {
    target.innerHTML = '<div class="empty">표시할 사용자가 없습니다.</div>';
    return;
  }
  target.innerHTML = users.map((user, index) => `
    <div class="list-item ${user === USER_ID ? "me" : ""}">
      <strong>${targetId === "queueList" ? index + 1 + "번" : "입장"}</strong>
      <span>${user === USER_ID ? user + " (나)" : user}</span>
    </div>
  `).join("");
}

function render() {
  const state = currentState || {};
  const status = currentStatus?.status || "waiting";
  const position = currentStatus?.queue_position || "-";
  document.getElementById("waitingPill").className = `pill ${status}`;
  document.getElementById("waitingPill").textContent = status.toUpperCase();
  document.getElementById("queuePosition").textContent = String(position);
  document.getElementById("aheadCount").textContent = position === "-" ? "-" : String(Math.max(Number(position) - 1, 0));

  if (status === "waiting") {
    document.getElementById("waitingTitle").textContent = `${USER_ID} 님은 현재 Page B 대기실에 있습니다`;
    document.getElementById("waitingText").textContent = `${position}번 순서입니다. Page A 자리가 나면 자동 이동합니다.`;
  } else {
    document.getElementById("waitingTitle").textContent = "입장 가능 상태입니다";
    document.getElementById("waitingText").textContent = "예매 페이지로 이동합니다.";
  }

  renderUsers("admittedUsers", state.admitted_users || []);
  renderUsers("queueList", state.waiting_users || []);
}

async function pollNow() {
  currentStatus = await api(`/api/status?user_id=${encodeURIComponent(USER_ID)}`);
  currentState = currentStatus.state || await api("/api/state");
  render();

  if (["admitted", "holding", "confirmed"].includes(currentStatus.status)) {
    window.location.replace(`/ticketing?user_id=${encodeURIComponent(USER_ID)}`);
  }
}

pollNow();
setInterval(pollNow, 2000);
""".replace("__USER_ID__", json.dumps(user_id))
    body = f"""
<div class="shell">
  <div class="topbar">
    <div class="brand"><span class="brand-mark">B</span><span>Page B Waiting Room</span></div>
    <div class="nav"><a href="/">처음으로</a><a href="/ops">운영 보기</a></div>
  </div>
  <section class="grid-two">
    <section class="panel"><div class="panel-body">
      <span class="flag">PAGE B</span>
      <div class="status-box">
        <div>
          <strong id="waitingTitle">대기열 정보를 확인하는 중입니다</strong>
          <div class="lead" id="waitingText">입장 가능 상태가 되면 Page A로 자동 이동합니다.</div>
        </div>
        <span id="waitingPill" class="pill waiting">WAITING</span>
      </div>
      <div class="cards" style="margin-top:18px;">
        <div class="card"><small>내 아이디</small><strong>{safe_user or "-"}</strong></div>
        <div class="card"><small>현재 순번</small><strong id="queuePosition">-</strong></div>
        <div class="card"><small>앞에 남은 인원</small><strong id="aheadCount">-</strong></div>
      </div>
      <div class="note">현재는 Page B 대기실입니다. 운영자 또는 다른 사용자의 완료로 자리가 나면 자동으로 Page A 예매실로 이동합니다.</div>
    </div></section>
    <aside class="panel"><div class="panel-body">
      <h3 class="title" style="font-size:24px;">현재 Page A 입장자</h3>
      <div id="admittedUsers" class="list" style="margin-top:16px;"></div>
      <h3 class="title" style="font-size:24px; margin-top:18px;">전체 대기열</h3>
      <div id="queueList" class="list" style="margin-top:16px;"></div>
    </div></aside>
  </section>
</div>
"""
    return _page("PyMiniRedis Waiting Room", body, script)


def render_ticketing_page(user_id: str, seat_ids: tuple[str, ...]) -> str:
    safe_user = html.escape(user_id)
    script = """
const USER_ID = __USER_ID__;
const SEAT_IDS = __SEAT_IDS__;
let selectedSeat = SEAT_IDS[0] || "A1";
let currentStatus = null;
let currentState = null;
let logs = [];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

function pushLog(message) {
  const stamp = new Date().toLocaleTimeString("ko-KR", { hour12: false });
  logs.unshift({ stamp, message });
  logs = logs.slice(0, 6);
  renderLogs();
}

function currentReservation() {
  return currentState?.reservations?.[USER_ID] || currentStatus?.reservation || null;
}

function renderBanner() {
  const status = currentStatus?.status || "admitted";
  document.getElementById("ticketPill").className = `pill ${status}`;
  document.getElementById("ticketPill").textContent = status.toUpperCase();

  if (status === "admitted") {
    document.getElementById("ticketTitle").textContent = `${USER_ID} 님은 현재 Page A 예매실에 있습니다`;
    document.getElementById("ticketText").textContent = "좌석을 선택하고 홀드한 뒤 결제 확정 또는 취소를 진행할 수 있습니다.";
  } else if (status === "holding") {
    document.getElementById("ticketTitle").textContent = `${USER_ID} 님의 좌석이 임시 홀드되었습니다`;
    document.getElementById("ticketText").textContent = "결제 확정을 누르면 예매 완료 처리됩니다.";
  } else if (status === "confirmed") {
    document.getElementById("ticketTitle").textContent = `${USER_ID} 님의 예매가 완료되었습니다`;
    document.getElementById("ticketText").textContent = "예매 완료 상태를 유지합니다.";
  } else {
    document.getElementById("ticketTitle").textContent = "상태를 확인하는 중입니다";
    document.getElementById("ticketText").textContent = "필요 시 대기실로 다시 이동할 수 있습니다.";
  }
}

function renderSeats() {
  const seatMap = currentState?.seats || {};
  const target = document.getElementById("seatGrid");
  target.innerHTML = "";
  SEAT_IDS.forEach((seatId) => {
    const holder = seatMap[seatId];
    const mine = holder === USER_ID;
    const taken = Boolean(holder && holder !== USER_ID);
    const button = document.createElement("button");
    button.className = `seat ${selectedSeat === seatId ? "selected" : ""} ${mine ? "mine" : ""} ${taken ? "taken" : ""}`.trim();
    button.disabled = taken;
    button.innerHTML = `<strong>${seatId}</strong><span>${mine ? "내가 선점한 좌석" : taken ? "다른 사용자가 사용 중" : "예매 가능"}</span>`;
    button.onclick = () => {
      if (taken) return;
      selectedSeat = seatId;
      renderSeats();
      renderSummary();
    };
    target.appendChild(button);
  });
}

function renderSummary() {
  const state = currentState || {};
  const reservation = currentReservation();
  document.getElementById("summary").innerHTML = `
    <div class="list-item"><strong>현재 사용자</strong><span>${USER_ID}</span></div>
    <div class="list-item"><strong>예매 상태</strong><span>${currentStatus?.status || "-"}</span></div>
    <div class="list-item"><strong>선택 좌석</strong><span>${selectedSeat}</span></div>
    <div class="list-item"><strong>홀드/확정 좌석</strong><span>${reservation?.seat_id || "-"}</span></div>
    <div class="list-item"><strong>남은 좌석</strong><span>${state.stock ?? "-"}</span></div>
    <div class="list-item"><strong>현재 Page A 입장 수</strong><span>${state.active_count ?? "-"} / ${state.max_active_users ?? "-"}</span></div>
  `;

  const admitted = state.admitted_users || [];
  document.getElementById("admittedUsers").innerHTML = admitted.length
    ? admitted.map((user) => `<div class="list-item ${user === USER_ID ? "me" : ""}"><strong>${user === USER_ID ? "나" : "입장"}</strong><span>${user}</span></div>`).join("")
    : '<div class="empty">현재 입장한 사용자가 없습니다.</div>';
  document.getElementById("reserveButton").disabled = currentStatus?.status !== "admitted";
  document.getElementById("confirmButton").disabled = currentStatus?.status !== "holding";
  document.getElementById("cancelButton").disabled = !["holding", "confirmed"].includes(currentStatus?.status || "");
}

function renderLogs() {
  const target = document.getElementById("logs");
  target.innerHTML = logs.length
    ? logs.map((entry) => `<div class="list-item"><strong>${entry.stamp}</strong><span>${entry.message}</span></div>`).join("")
    : '<div class="empty">아직 동작 기록이 없습니다.</div>';
}

async function syncState() {
  currentStatus = await api(`/api/status?user_id=${encodeURIComponent(USER_ID)}`);
  currentState = currentStatus.state || await api("/api/state");

  if (currentStatus.status === "waiting") {
    window.location.replace(`/waiting-room?user_id=${encodeURIComponent(USER_ID)}`);
    return;
  }

  renderBanner();
  renderSeats();
  renderSummary();
  renderLogs();
}

async function reserveSeat() {
  const result = await api("/api/reserve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID, seat_id: selectedSeat }),
  });
  pushLog(result.status === "holding" ? `${selectedSeat} 좌석 홀드 성공` : `홀드 실패: ${result.reason || "unknown"}`);
  await syncState();
}

async function confirmReservation() {
  const result = await api("/api/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID }),
  });
  pushLog(result.status === "confirmed" ? "결제 확정 완료" : `확정 실패: ${result.reason || "unknown"}`);
  await syncState();
}

async function cancelReservation() {
  const result = await api("/api/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID }),
  });
  pushLog(result.status === "cancelled" ? "예약 취소 완료" : `취소 실패: ${result.reason || "unknown"}`);
  await syncState();
}

pushLog("Page A 예매실에 진입했습니다.");
syncState();
setInterval(syncState, 2500);
""".replace("__USER_ID__", json.dumps(user_id)).replace("__SEAT_IDS__", json.dumps(list(seat_ids), ensure_ascii=False))
    body = f"""
<div class="shell">
  <div class="topbar">
    <div class="brand"><span class="brand-mark">A</span><span>Page A Ticketing Room</span></div>
    <div class="nav"><a href="/">처음으로</a><a href="/waiting-room?user_id={safe_user}">대기실</a><a href="/ops">운영 보기</a></div>
  </div>
  <section class="grid-two">
    <section class="panel"><div class="panel-body">
      <span class="flag">PAGE A</span>
      <div class="status-box">
        <div>
          <strong id="ticketTitle">예매실 상태를 확인하는 중입니다</strong>
          <div class="lead" id="ticketText">좌석 상태를 불러오고 있습니다.</div>
        </div>
        <span id="ticketPill" class="pill admitted">ADMITTED</span>
      </div>
      <div class="seat-stage" style="margin-top:18px;">
        <div class="stage-label">SEAT MAP</div>
        <div class="screen">STAGE</div>
        <div id="seatGrid" class="seat-grid"></div>
        <div class="button-row">
          <button id="reserveButton" class="button" onclick="reserveSeat()">선택 좌석 홀드</button>
          <button id="confirmButton" class="button" onclick="confirmReservation()">결제 확정</button>
        </div>
        <div class="button-row">
          <button id="cancelButton" class="secondary" onclick="cancelReservation()">예약 취소</button>
          <button class="secondary" onclick="syncState()">상태 새로고침</button>
        </div>
      </div>
    </div></section>
    <aside class="panel"><div class="panel-body">
      <h3 class="title" style="font-size:24px;">내 예매 요약</h3>
      <div id="summary" class="list" style="margin-top:16px;"></div>
      <h3 class="title" style="font-size:24px; margin-top:18px;">현재 Page A 입장자</h3>
      <div id="admittedUsers" class="list" style="margin-top:16px;"></div>
      <h3 class="title" style="font-size:24px; margin-top:18px;">최근 동작</h3>
      <div id="logs" class="logs" style="margin-top:16px;"></div>
    </div></aside>
  </section>
</div>
"""
    return _page("PyMiniRedis Ticketing Room", body, script)


def render_ops_page(config: TicketingConfig) -> str:
    body = f"""
<div class="shell">
  <div class="topbar">
    <div class="brand"><span class="brand-mark">O</span><span>Operator View</span></div>
    <div class="nav"><a href="/">랜딩</a><a href="/waiting-room?user_id=user-b">대기실 예시</a></div>
  </div>
  <section class="panel"><div class="panel-body">
    <span class="flag">OPS</span>
    <h2 class="title">운영자 상태 확인 화면</h2>
    <p class="lead">현재 입장 완료자, 대기열, 좌석 점유 상태를 바로 볼 수 있게 만들어 테스트를 쉽게 하는 페이지입니다.</p>
    <div class="cards">
      <div class="card"><small>Page A 수용 인원</small><strong>{config.max_active_users}</strong></div>
      <div class="card"><small>등록 좌석 수</small><strong>{len(config.seat_ids)}</strong></div>
      <div class="card"><small>홀드 유지 시간</small><strong>{config.hold_seconds}s</strong></div>
    </div>
    <div class="button-row">
      <button class="secondary" onclick="advanceQueue()">대기열 1명 입장</button>
      <button class="secondary" onclick="resetDemo()">데모 초기화</button>
    </div>
  </div></section>
  <section class="grid-three" style="margin-top:18px;">
    <section class="panel"><div class="panel-body"><h3 class="title" style="font-size:24px;">현재 Page A 입장자</h3><div id="admittedUsers" class="list" style="margin-top:16px;"></div></div></section>
    <section class="panel"><div class="panel-body"><h3 class="title" style="font-size:24px;">대기열</h3><div id="waitingUsers" class="list" style="margin-top:16px;"></div></div></section>
    <section class="panel"><div class="panel-body"><h3 class="title" style="font-size:24px;">좌석 상태</h3><div id="seatState" class="list" style="margin-top:16px;"></div></div></section>
  </section>
</div>
"""
    script = """
async function api(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

function renderList(targetId, items, formatter, emptyText) {
  const target = document.getElementById(targetId);
  target.innerHTML = items.length ? items.map(formatter).join("") : `<div class="empty">${emptyText}</div>`;
}

async function refreshOps() {
  const state = await api("/api/state");
  renderList("admittedUsers", state.admitted_users || [], (user) => `<div class="list-item"><strong>입장</strong><span>${user}</span></div>`, "현재 입장한 사용자가 없습니다.");
  renderList("waitingUsers", state.waiting_users || [], (user, index) => `<div class="list-item"><strong>${index + 1}번</strong><span>${user}</span></div>`, "현재 대기열이 비어 있습니다.");
  const seatItems = Object.entries(state.seats || {}).map(([seatId, holder]) => ({ seatId, holder }));
  renderList("seatState", seatItems, (entry) => `<div class="list-item"><strong>${entry.seatId}</strong><span>${entry.holder || "비어 있음"}</span></div>`, "좌석 정보가 없습니다.");
}

async function advanceQueue() {
  await api("/api/advance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ count: 1 }),
  });
  await refreshOps();
}

async function resetDemo() {
  await api("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  await refreshOps();
}

refreshOps();
setInterval(refreshOps, 2000);
"""
    return _page("PyMiniRedis Operator View", body, script)
