from __future__ import annotations

import html
import json

from ticketing_service.service import TicketingConfig


BASE_STYLE = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

:root {
  --bg: #F4F6F9;
  --surface: #FFFFFF;
  --text-main: #111111;
  --text-sub: #777777;
  --border: #E8ECEF;
  --red-main: #EB002C;
  --red-dark: #C9001D;
  --red-light: #FDE8EA;
  --success: #00A651;
  --shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
}
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh;
  background-color: var(--bg);
  color: var(--text-main);
  font-family: 'Pretendard', -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}
a { text-decoration: none; color: inherit; }
button, input { font-family: inherit; }

/* 헤더 GNB */
.header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 18px 40px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.02);}
.header-logo { font-size: 24px; font-weight: 800; color: var(--red-main); letter-spacing: -0.5px; display: flex; align-items: center; gap: 8px;}
.header-logo span { background: var(--text-main); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 14px;}
.header-nav { display: flex; gap: 24px; font-size: 15px; font-weight: 600; color: var(--text-main); }
.header-nav a:hover { color: var(--red-main); }

/* 컨테이너 */
.container { max-width: 1100px; margin: 40px auto; padding: 0 20px; }
.grid-hero { display: grid; grid-template-columns: 360px 1fr; gap: 24px; }
.grid-half { display: grid; grid-template-columns: 6.5fr 3.5fr; gap: 24px; }
.grid-three { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }

/* 공통 박스 */
.box { background: var(--surface); border-radius: 12px; box-shadow: var(--shadow); border: 1px solid var(--border); overflow: hidden; }
.box-p { padding: 36px; }

/* 포스터 영역 (메인 배너) */
.poster {
  background: #111; color: #fff; min-height: 500px; position: relative; padding: 40px; 
  display: flex; flex-direction: column; justify-content: flex-end; border-radius: 12px;
  background-image: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.1) 100%), url('https://images.unsplash.com/photo-1540039155732-68473638cbb3?auto=format&fit=crop&w=800&q=80'); 
  background-size: cover; background-position: center; box-shadow: 0 10px 30px rgba(235, 0, 44, 0.2);
}
.poster-tag { background: var(--red-main); color: #fff; display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: 700; font-size: 13px; margin-bottom: 12px; letter-spacing: 1px; align-self: flex-start;}
.poster-title { font-size: 42px; font-weight: 800; margin: 0 0 16px 0; line-height: 1.25; letter-spacing: -1px;}
.poster-desc { font-size: 15px; color: #ccc; margin: 0; line-height: 1.6; }

/* 텍스트 UI */
.title-lg { font-size: 26px; font-weight: 700; margin: 0 0 10px 0; letter-spacing: -0.5px; }
.desc { color: var(--text-sub); font-size: 15px; margin-bottom: 28px; line-height: 1.6; }

/* 인포 카드 (요약 지표) */
.info-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 32px; }
.info-card { background: #F8F9FA; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid var(--border); }
.info-card span { display: block; font-size: 13px; color: var(--text-sub); margin-bottom: 6px; font-weight: 600;}
.info-card strong { font-size: 26px; font-weight: 800; color: var(--red-main); }

/* 폼 요소 */
.input-group { margin-bottom: 24px; }
.input-group label { display: block; font-size: 14px; font-weight: 600; color: var(--text-main); margin-bottom: 8px; }
.input-group input { width: 100%; padding: 16px; border: 1px solid #CCC; border-radius: 8px; font-size: 16px; transition: border 0.2s; }
.input-group input:focus { outline: none; border-color: var(--text-main); }

/* 버튼 */
.btn { width: 100%; padding: 16px; border-radius: 8px; border: none; font-size: 16px; font-weight: 700; cursor: pointer; text-align: center; transition: 0.2s; }
.btn-red { background: var(--red-main); color: #fff; }
.btn-red:hover:not(:disabled) { background: var(--red-dark); }
.btn-outline { background: #fff; color: var(--text-main); border: 1px solid #CCC; }
.btn-outline:hover { background: #F8F9FA; border-color: #999; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 20px;}

/* 알림 박스 */
.notice { padding: 18px; border-radius: 8px; background: #F8F9FA; color: var(--text-sub); font-size: 14px; text-align: center; margin-top: 24px; border: 1px solid var(--border); word-break: keep-all;}

/* 대기열 특화 (Waiting Room) */
.queue-box { text-align: center; padding: 70px 20px; }
.queue-box h2 { font-size: 26px; margin-bottom: 12px; font-weight: 700;}
.queue-box p { color: var(--text-sub); margin-bottom: 40px; font-size: 16px;}
.spinner { margin: 0 auto 30px; width: 60px; height: 60px; border: 4px solid var(--red-light); border-top: 4px solid var(--red-main); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.queue-number-wrap { margin: 30px 0; }
.queue-number { font-size: 90px; font-weight: 800; color: var(--red-main); line-height: 1; letter-spacing: -3px; }
.queue-label { font-size: 18px; color: var(--text-main); font-weight: 600; margin-top: 8px; }

/* 상태 구간 분리 (Pill/Badge) */
.pill-wrap { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 30px; border-bottom: 2px solid var(--text-main); padding-bottom: 20px; }
.badge { padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: 700; text-transform: uppercase; }
.badge.waiting { background: #FFF3CD; color: #B46B17; }
.badge.admitted { background: #D1E7DD; color: #0F5132; }
.badge.holding { background: var(--red-light); color: var(--red-dark); }
.badge.confirmed { background: var(--text-main); color: #fff; }

/* 리스트 */
.list { display: flex; flex-direction: column; gap: 8px; }
.list-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; background: #F8F9FA; border-radius: 8px; font-size: 15px; border: 1px solid transparent; }
.list-item.me { background: var(--red-light); border-color: rgba(235,0,44,0.2); color: var(--red-dark); font-weight: 600; }
.list-item strong { color: var(--text-sub); font-weight: 600; font-size: 14px;}
.empty-state { text-align: center; padding: 40px 20px; color: var(--text-sub); background: #F8F9FA; border-radius: 8px; font-size: 14px; }

/* 좌석 예매도 (Seat Component) */
.stage { background: #E8ECEF; text-align: center; padding: 16px; border-radius: 8px; font-weight: 700; color: #999; margin-bottom: 30px; letter-spacing: 5px; }
.seat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 30px; }
.seat { aspect-ratio: 1; border-radius: 8px; border: 2px solid var(--border); background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 700; color: var(--text-main); transition: 0.2s; position: relative;}
.seat:hover:not(:disabled) { border-color: var(--text-main); color: var(--text-main); }
.seat.selected { background: var(--red-main); border-color: var(--red-main); color: #fff; }
.seat.mine { background: var(--success); border-color: var(--success); color: #fff; }
.seat.taken { background: #E8ECEF; border-color: #E8ECEF; color: #AAA; cursor: not-allowed; }
.seat-sub { position: absolute; font-size: 10px; bottom: 6px; font-weight: 500; opacity: 0.8;}

@media (max-width: 900px) {
  .grid-hero, .grid-half, .grid-three { grid-template-columns: 1fr; }
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
<div class="header">
  <div class="header-logo"><span>PMR</span> REDIS_PROJECT</div>
  <div class="header-nav"><a href="/">예매홈</a><a href="/ops">운영센터</a></div>
</div>

<div class="container">
  <div class="grid-hero">
    <div class="poster">
      <div class="poster-tag">단독판매</div>
      <h1 class="poster-title">GRAND HALL<br>LIVE 2026</h1>
      <p class="poster-desc">초당 19,000건의 트래픽을 방어하는<br>PyMiniRedis 티켓팅 실전 데모입니다.</p>
    </div>
    
    <div class="box box-p">
      <h2 class="title-lg">단독 예매하기</h2>
      <p class="desc">Redis 대기열(ZSET) 기반으로 보호되는 안전한 예매 페이지입니다. 원하는 ID를 입력해 예매 대기열에 진입하세요.</p>
      
      <div class="info-cards">
        <div class="info-card"><span>수용 한도</span><strong>{config.max_active_users}</strong></div>
        <div class="info-card"><span>총 좌석 수</span><strong>{len(config.seat_ids)}</strong></div>
        <div class="info-card"><span>대기열 밀집도</span><strong id="queueSize">-</strong></div>
      </div>
      
      <div class="input-group">
        <label for="userId">REDIS_PROJECT 회원 아이디 (자유 입력)</label>
        <input id="userId" value="user-a" placeholder="user-abc">
      </div>
      
      <div class="btn-row" style="margin-bottom: 20px;">
        <button class="btn btn-red" onclick="startEntry()">예매 진입하기</button>
        <button class="btn btn-outline" onclick="refreshOverview()">서버 현황고침</button>
      </div>
      
      <div class="notice" id="entryMessage">실시간 서버 상황 (대기열/입장자) 을 연결 중입니다...</div>
    </div>
  </div>
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
  const admitted = (state.admitted_users || []).join(", ") || "내부 접속자 없음";
  document.getElementById("entryMessage").textContent = `현재 예매실 점유자: [ ${admitted} ] / 총 대기 유저: ${state.queue_size ?? 0}명`;
}

async function startEntry() {
  const userId = document.getElementById("userId").value.trim();
  if (!userId) {
    document.getElementById("entryMessage").textContent = "아이디를 먼저 입력해주세요!";
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
    document.getElementById("entryMessage").textContent = `[RATE LIMIT] 어뷰징 감지: ${result.reset_in}초 뒤 다시 시도해주세요.`;
    return;
  }
  document.getElementById("entryMessage").textContent = "서버 통신 실패.";
}

refreshOverview();
setInterval(refreshOverview, 4000);
"""
    return _page("PyMiniRedis REDIS_PROJECT - Entry", body, script)


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

function renderUsers(targetId, users, isQueue) {
  const target = document.getElementById(targetId);
  if (!users.length) {
    target.innerHTML = '<div class="empty-state">해당 인원이 없습니다.</div>';
    return;
  }
  target.innerHTML = users.map((user, index) => `
    <div class="list-item ${user === USER_ID ? "me" : ""}">
      <strong>${isQueue ? (index + 1) + "번대" : "예매 중"}</strong>
      <span>${user === USER_ID ? user + " (나)" : user}</span>
    </div>
  `).join("");
}

function render() {
  const state = currentState || {};
  const status = currentStatus?.status || "waiting";
  const position = currentStatus?.queue_position || "-";
  
  document.getElementById("waitingPill").className = `badge ${status}`;
  document.getElementById("waitingPill").textContent = status.toUpperCase();
  document.getElementById("queuePosition").textContent = String(position);
  document.getElementById("aheadCount").textContent = position === "-" ? "-" : String(Math.max(Number(position) - 1, 0));

  if (status === "waiting") {
    document.getElementById("waitingTitle").textContent = "고객님 앞에 접속한 대기자가 있습니다.";
    document.getElementById("waitingText").textContent = "잠시만 대기해 주시면 예매 페이지로 자동 접속됩니다.";
  } else {
    document.getElementById("waitingTitle").textContent = "예매실 입장 준비 완료!";
    document.getElementById("waitingText").textContent = "곧 좌석 페이지로 자동 이동합니다...";
  }

  renderUsers("admittedUsers", state.admitted_users || [], false);
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
<div class="header">
  <div class="header-logo"><span>PMR</span> REDIS_PROJECT</div>
</div>

<div class="container">
  <div class="grid-half">
    <!-- 왼쪽 큐 뷰 -->
    <div class="box queue-box">
      <div class="pill-wrap">
        <div style="text-align:left;">
          <h2 id="waitingTitle" style="margin:0; font-size:22px;">대기열 통신 연결 중...</h2>
          <div id="waitingText" style="color:var(--text-sub); font-size:14px; margin-top:4px;">잠시만 기다려주세요.</div>
        </div>
        <span id="waitingPill" class="badge waiting">WAITING</span>
      </div>
      
      <div class="spinner"></div>
      <h3>현재 나의 대기 순서</h3>
      
      <div class="queue-number-wrap">
        <div class="queue-number" id="queuePosition">-</div>
        <div class="queue-label">번째</div>
      </div>
      
      <p style="background:#F8F9FA; padding:16px; border-radius:8px; border:1px solid var(--border);">
        나보다 늦게 접속한 사람들 앞에는 <b style="color:var(--text-main);" id="aheadCount">-</b>명의 대기자가 있습니다.<br>
        새로고침 시 순번이 뒤로 밀릴 수 있습니다.
      </p>
    </div>
    
    <!-- 오른쪽 현황 -->
    <div class="box box-p">
      <h3 class="title-lg" style="font-size:20px;">내 접속 브라우저 ID</h3>
      <div class="notice" style="margin: 10px 0 30px; font-weight: 700; color:var(--red-dark); font-size: 16px;">{safe_user or "-"}</div>
      
      <h3 class="title-lg" style="font-size:20px;">현재 실제 예매 중인 사람</h3>
      <p class="desc" style="margin-bottom: 12px;">이분들의 결제가 끝나거나 도망가면 순번이 줄어듭니다.</p>
      <div id="admittedUsers" class="list"></div>
      
      <div class="btn-row" style="margin-top: 30px;">
        <button class="btn btn-outline" onclick="window.location.href='/'">포기하고 나가기</button>
      </div>
    </div>
  </div>
</div>
"""
    return _page("PyMiniRedis - Waiting Room", body, script)


def render_ticketing_page(user_id: str, seat_ids: tuple[str, ...]) -> str:
    safe_user = html.escape(user_id)
    script = """
const USER_ID = __USER_ID__;
const SEAT_IDS = __SEAT_IDS__;
let selectedSeat = SEAT_IDS[0] || "A1";
let currentStatus = null;
let currentState = null;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

function currentReservation() {
  return currentState?.reservations?.[USER_ID] || currentStatus?.reservation || null;
}

function renderBanner() {
  const status = currentStatus?.status || "admitted";
  document.getElementById("ticketPill").className = `badge ${status}`;
  document.getElementById("ticketPill").textContent = status.toUpperCase();

  if (status === "admitted") {
    document.getElementById("ticketTitle").textContent = `좌석 선택하기`;
    document.getElementById("ticketText").textContent = "원하시는 구역의 좌석을 빨리 선점(홀드) 하세요!";
  } else if (status === "holding") {
    document.getElementById("ticketTitle").textContent = `좌석 홀드 완료! 결제를 진행하세요.`;
    document.getElementById("ticketText").textContent = "지금 방어 중입니다. 지정시간 내에 결제 확정을 완료해주세요.";
  } else if (status === "confirmed") {
    document.getElementById("ticketTitle").textContent = `예매 완료`;
    document.getElementById("ticketText").textContent = "예매가 안전하게 확정되었습니다.";
  } else {
    document.getElementById("ticketTitle").textContent = "동기화 중...";
    document.getElementById("ticketText").textContent = "데이터를 불러옵니다.";
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
    
    let sub = mine ? "보유좌석" : (taken ? "결제중" : "선택");
    
    const button = document.createElement("button");
    button.className = `seat ${selectedSeat === seatId ? "selected" : ""} ${mine ? "mine" : ""} ${taken ? "taken" : ""}`.trim();
    button.disabled = taken;
    button.innerHTML = `${seatId} <div class="seat-sub">${sub}</div>`;
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
  
  document.getElementById("sum-id").textContent = USER_ID;
  document.getElementById("sum-selected").textContent = selectedSeat;
  document.getElementById("sum-hold").textContent = reservation?.seat_id || "-";
  document.getElementById("sum-stock").textContent = state.stock ?? "-";

  document.getElementById("reserveButton").disabled = currentStatus?.status !== "admitted";
  document.getElementById("confirmButton").disabled = currentStatus?.status !== "holding";
  document.getElementById("cancelButton").disabled = !["holding", "confirmed"].includes(currentStatus?.status || "");
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
}

async function reserveSeat() {
  const result = await api("/api/reserve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID, seat_id: selectedSeat }),
  });
  if (result.status === "holding") { alert(`${selectedSeat} 좌석 선점에 성공했습니다! 결제를 진행하세요.`); }
  else { alert(`홀드 실패 (누군가 먼저 낚아챘습니다)`); }
  await syncState();
}

async function confirmReservation() {
  const result = await api("/api/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID }),
  });
  if (result.status === "confirmed") { alert(`결제가 확정되었습니다. 예매 완료!`); }
  await syncState();
}

async function cancelReservation() {
  if (!confirm("정말 취소하시겠습니까? 대기열로 돌아가거나 서버 밖으로 나갑니다.")) return;
  await api("/api/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: USER_ID }),
  });
  window.location.replace('/');
}

syncState();
setInterval(syncState, 2000);
""".replace("__USER_ID__", json.dumps(user_id)).replace("__SEAT_IDS__", json.dumps(list(seat_ids), ensure_ascii=False))
    
    body = f"""
<div class="header">
  <div class="header-logo"><span>PMR</span> Ticketlink</div>
  <div class="header-nav"><a href="/ops" target="_blank">운영자 센터</a></div>
</div>

<div class="container">
  <div class="pill-wrap" style="border-bottom: 3px solid #111;">
    <div style="text-align:left;">
      <h2 id="ticketTitle" style="margin:0 0 8px 0; font-size:28px;">GRAND HALL LIVE - 좌석 선택</h2>
      <div id="ticketText" style="color:var(--text-sub); font-size:15px;">서버와 통신 중입니다.</div>
    </div>
    <span id="ticketPill" class="badge admitted">ADMITTED</span>
  </div>

  <div class="grid-half">
    <div class="box box-p" style="background: #FAFAFA;">
      <div class="stage">STAGE (무대)</div>
      <div id="seatGrid" class="seat-grid"></div>
    </div>
    
    <div class="box box-p">
      <h3 class="title-lg" style="font-size:22px;">예매 정보 요약</h3>
      <div class="list" style="margin: 20px 0;">
        <div class="list-item"><strong>예매자 ID</strong><span id="sum-id">-</span></div>
        <div class="list-item" style="border:1px solid #111;"><strong>내가 클릭한 좌석</strong><span id="sum-selected" style="color:var(--red-main); font-weight:700;">-</span></div>
        <div class="list-item" style="background:#E8ECEF;"><strong>현재 내가 홀드한 좌석</strong><span id="sum-hold">-</span></div>
        <div class="list-item"><strong>남은 총 잔여석</strong><span id="sum-stock">-</span></div>
      </div>
      
      <div style="display:flex; flex-direction:column; gap:12px; margin-top:30px;">
        <button id="reserveButton" class="btn btn-outline" style="border:2px solid var(--text-main);" onclick="reserveSeat()">선택한 좌석 홀드 (선점하기)</button>
        <button id="confirmButton" class="btn btn-red" onclick="confirmReservation()">홀드 완료 -> 즉시 결제하기</button>
        <button id="cancelButton" class="btn btn-outline" style="margin-top:20px; border-color:#E8ECEF; color:#AAA;" onclick="cancelReservation()">예매 취소 / 나가기</button>
      </div>
    </div>
  </div>
</div>
"""
    return _page("PyMiniRedis Ticketlink - Booking", body, script)


def render_ops_page(config: TicketingConfig) -> str:
    body = f"""
<div class="header" style="background: #111;">
  <div class="header-logo" style="color:#fff;"><span style="background:var(--red-main);">OPS</span> Ticketlink Admin</div>
  <div class="header-nav"><a href="/" style="color:#999;">유저 메인화면</a></div>
</div>

<div class="container">
  <div class="box box-p">
    <h2 class="title-lg">운영자 관제 대시보드 (Admin)</h2>
    <p class="desc">실시간으로 In-memory Redis 위에서 움직이는 예매 현황, 대기열, 좌석 점유를 관제합니다.</p>
    
    <div class="info-cards">
      <div class="info-card"><span>동시 입장 한도 (Page A)</span><strong>{config.max_active_users}</strong></div>
      <div class="info-card"><span>총 좌석 재고 (Stock)</span><strong>{len(config.seat_ids)}</strong></div>
      <div class="info-card"><span>좌석 선점 TTL(초)</span><strong>{config.hold_seconds}s</strong></div>
    </div>
    
    <div class="btn-row" style="max-width: 500px; margin: 0 auto;">
      <button class="btn btn-outline" onclick="advanceQueue()">대기열 1명 밀어넣기 (Advance)</button>
      <button class="btn btn-outline" style="color:var(--red-dark);" onclick="resetDemo()">DB 초기화 (Reset)</button>
    </div>
  </div>

  <div class="grid-three" style="margin-top: 24px;">
    <div class="box box-p">
      <h3 class="title-lg" style="font-size:20px;">현장 예매자 (Page A)</h3>
      <div id="admittedUsers" class="list" style="margin-top:16px;"></div>
    </div>
    <div class="box box-p">
      <h3 class="title-lg" style="font-size:20px;">대기열 (ZSET 큐)</h3>
      <div id="waitingUsers" class="list" style="margin-top:16px;"></div>
    </div>
    <div class="box box-p">
      <h3 class="title-lg" style="font-size:20px;">좌석 보존 현황</h3>
      <div id="seatState" class="list" style="margin-top:16px;"></div>
    </div>
  </div>
</div>
"""
    script = """
async function api(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

function renderList(targetId, items, formatter, emptyText) {
  const target = document.getElementById(targetId);
  target.innerHTML = items.length ? items.map(formatter).join("") : `<div class="empty-state">${emptyText}</div>`;
}

async function refreshOps() {
  const state = await api("/api/state");
  renderList("admittedUsers", state.admitted_users || [], (user) => `<div class="list-item"><strong>입장함</strong><span>${user}</span></div>`, "현재 방어중인 입장자가 없습니다.");
  renderList("waitingUsers", state.waiting_users || [], (user, index) => `<div class="list-item"><strong>${index + 1}번째 대기</strong><span>${user}</span></div>`, "대기열 큐가 깨끗합니다.");
  const seatItems = Object.entries(state.seats || {}).map(([seatId, holder]) => ({ seatId, holder }));
  renderList("seatState", seatItems, (entry) => `<div class="list-item"><strong>${entry.seatId}번 좌석</strong><span>${entry.holder || "비어 있음 (판매중)"}</span></div>`, "판매 좌석 정보가 없습니다.");
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
    return _page("PyMiniRedis Ticketlink - Admin", body, script)
