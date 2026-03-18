from __future__ import annotations


DEMO_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mini Redis Ticketing Demo</title>
  <style>
    :root {
      --bg: #f4efe6;
      --panel: rgba(255, 252, 247, 0.86);
      --panel-strong: #fffaf1;
      --ink: #1f2a22;
      --muted: #5b675f;
      --line: rgba(31, 42, 34, 0.12);
      --accent: #1f6f5f;
      --accent-soft: #dff4ee;
      --warn: #c85f3d;
      --warn-soft: #fde6db;
      --gold: #c79c45;
      --shadow: 0 20px 45px rgba(58, 47, 30, 0.12);
      --radius: 22px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "Avenir Next", "Pretendard", "Apple SD Gothic Neo", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(31, 111, 95, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(199, 156, 69, 0.18), transparent 24%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 55%, #efe7db 100%);
      min-height: 100vh;
    }

    .shell {
      max-width: 1320px;
      margin: 0 auto;
      padding: 40px 24px 56px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
      animation: rise 420ms ease-out;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }

    .hero-main {
      padding: 30px 30px 26px;
      position: relative;
      overflow: hidden;
    }

    .hero-main::after {
      content: "";
      position: absolute;
      inset: auto -70px -70px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(31, 111, 95, 0.18), transparent 68%);
      pointer-events: none;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(31, 111, 95, 0.1);
      color: var(--accent);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    h1 {
      margin: 16px 0 12px;
      font-size: clamp(32px, 6vw, 54px);
      line-height: 1.02;
      letter-spacing: -0.04em;
      max-width: 12ch;
    }

    .lead {
      margin: 0 0 22px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.7;
      max-width: 62ch;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .hero-stat {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.66);
      border: 1px solid rgba(31, 42, 34, 0.08);
    }

    .hero-stat strong {
      display: block;
      margin-top: 10px;
      font-size: 23px;
      line-height: 1;
    }

    .hero-side {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;
      animation: rise 520ms ease-out;
    }

    .stack {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .pill {
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 13px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
    }

    .layout {
      display: grid;
      grid-template-columns: 1.25fr 1fr;
      gap: 24px;
    }

    .column {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .section {
      padding: 24px;
      animation: rise 600ms ease-out;
    }

    .section h2 {
      margin: 0 0 10px;
      font-size: 24px;
      letter-spacing: -0.03em;
    }

    .section p {
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.6;
    }

    .subgrid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .form-card,
    .scenario-card,
    .status-card,
    .tip-card {
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(31, 42, 34, 0.08);
      border-radius: 18px;
      padding: 16px;
    }

    .form-card h3,
    .scenario-card h3,
    .status-card h3,
    .tip-card h3 {
      margin: 0 0 8px;
      font-size: 16px;
    }

    .scenario-card p,
    .status-card p,
    .tip-card p {
      margin: 0 0 14px;
      font-size: 14px;
      color: var(--muted);
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 8px;
      color: #314238;
    }

    input,
    textarea,
    select {
      width: 100%;
      border-radius: 14px;
      border: 1px solid rgba(31, 42, 34, 0.14);
      background: rgba(255, 255, 255, 0.92);
      padding: 12px 13px;
      font: inherit;
      color: var(--ink);
    }

    textarea {
      min-height: 104px;
      resize: vertical;
    }

    .field-group {
      margin-bottom: 12px;
    }

    .row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .row-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }

    button,
    .link-button {
      border: 0;
      border-radius: 999px;
      padding: 11px 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform 140ms ease, box-shadow 140ms ease, opacity 140ms ease;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    button:hover,
    .link-button:hover {
      transform: translateY(-1px);
      box-shadow: 0 12px 24px rgba(31, 42, 34, 0.12);
    }

    button:disabled {
      opacity: 0.6;
      cursor: wait;
      transform: none;
      box-shadow: none;
    }

    .primary {
      background: var(--accent);
      color: white;
    }

    .secondary {
      background: #ffffff;
      color: var(--ink);
      border: 1px solid rgba(31, 42, 34, 0.14);
    }

    .danger {
      background: var(--warn);
      color: white;
    }

    .status-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }

    .status-value {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.74);
      border: 1px solid rgba(31, 42, 34, 0.08);
    }

    .status-value span {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
    }

    .status-value strong {
      font-size: 28px;
      line-height: 1;
    }

    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }

    .badge {
      padding: 9px 12px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
      border: 1px solid transparent;
    }

    .badge.ok {
      background: var(--accent-soft);
      color: var(--accent);
      border-color: rgba(31, 111, 95, 0.18);
    }

    .badge.warn {
      background: var(--warn-soft);
      color: var(--warn);
      border-color: rgba(200, 95, 61, 0.2);
    }

    .table-wrap {
      overflow: auto;
      border-radius: 18px;
      border: 1px solid rgba(31, 42, 34, 0.08);
      background: rgba(255, 255, 255, 0.8);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 520px;
    }

    th,
    td {
      padding: 13px 14px;
      text-align: left;
      border-bottom: 1px solid rgba(31, 42, 34, 0.08);
      font-size: 14px;
    }

    th {
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.84);
    }

    .seat-chip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 88px;
      padding: 7px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }

    .seat-chip.AVAILABLE {
      background: rgba(31, 111, 95, 0.12);
      color: var(--accent);
    }

    .seat-chip.HELD {
      background: rgba(199, 156, 69, 0.18);
      color: #7d5f1f;
    }

    .seat-chip.SOLD {
      background: rgba(200, 95, 61, 0.13);
      color: var(--warn);
    }

    pre {
      margin: 0;
      padding: 18px;
      border-radius: 18px;
      background: #172018;
      color: #f0f7f2;
      font: 13px/1.6 "SFMono-Regular", "Menlo", monospace;
      overflow: auto;
      min-height: 160px;
    }

    .log-box {
      background: #fffdf9;
      border-radius: 18px;
      border: 1px dashed rgba(31, 42, 34, 0.16);
      padding: 16px;
      max-height: 280px;
      overflow: auto;
      font: 13px/1.65 "SFMono-Regular", "Menlo", monospace;
      white-space: pre-wrap;
    }

    .hint-list {
      display: grid;
      gap: 12px;
    }

    .hint {
      padding: 14px 16px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(31, 42, 34, 0.08);
    }

    .hint strong {
      display: block;
      margin-bottom: 6px;
    }

    .footer-note {
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
    }

    @keyframes rise {
      from {
        opacity: 0;
        transform: translateY(14px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @media (max-width: 1080px) {
      .hero,
      .layout,
      .subgrid,
      .row,
      .row-3,
      .status-strip {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="panel hero-main">
        <div class="eyebrow">Ticketing Control Room</div>
        <h1>브라우저에서 바로 보는 좌석 홀드 데모</h1>
        <p class="lead">
          `curl` 없이 이벤트 생성, 좌석 임시 점유, 확정, 취소, 상태 조회, 시나리오 실행까지 한 화면에서 확인할 수 있습니다.
          `hold`는 임시 점유 요청이고 `HELD`는 현재 임시 점유된 상태를 뜻합니다.
        </p>
        <div class="hero-grid">
          <div class="hero-stat">
            <div>기본 TTL</div>
            <strong id="heroTtl">__DEFAULT_HOLD_TTL__초</strong>
          </div>
          <div class="hero-stat">
            <div>접속 주소</div>
            <strong>127.0.0.1</strong>
          </div>
          <div class="hero-stat">
            <div>핵심 검증</div>
            <strong>중복 예매 0</strong>
          </div>
        </div>
      </div>
      <aside class="panel hero-side">
        <div>
          <h2 style="margin:0 0 10px;font-size:22px;">바로가기</h2>
          <div class="stack">
            <a class="link-button secondary" href="/docs" target="_blank" rel="noreferrer">FastAPI Docs</a>
            <a class="link-button secondary" href="/health" target="_blank" rel="noreferrer">/health</a>
            <button id="healthButton" class="primary" type="button">서버 상태 확인</button>
          </div>
        </div>
        <div class="status-card">
          <h3>연결 상태</h3>
          <p>API와 Mini Redis 둘 다 살아 있는지 확인합니다.</p>
          <div class="badge-row" id="healthBadges">
            <span class="badge warn">아직 확인 안 함</span>
          </div>
        </div>
        <div class="tip-card">
          <h3>용어 빠르게 보기</h3>
          <p><strong>hold</strong>는 좌석을 잠시 잡는 행동, <strong>HELD</strong>는 지금 잡혀 있는 상태입니다.</p>
        </div>
      </aside>
    </section>

    <div class="layout">
      <div class="column">
        <section class="panel section">
          <h2>시나리오 실행</h2>
          <p>CLI 대신 브라우저에서 바로 대표 시나리오를 실행합니다. 결과는 오른쪽 패널과 하단 로그에 반영됩니다.</p>
          <div class="subgrid">
            <div class="scenario-card">
              <h3>같은 좌석 동시 요청</h3>
              <p>한 좌석에 여러 요청을 몰아 넣어 한 명만 hold 되는지 확인합니다.</p>
              <div class="field-group">
                <label for="sameSeatConcurrency">동시 요청 수</label>
                <input id="sameSeatConcurrency" type="number" min="1" value="1000" />
              </div>
              <div class="actions">
                <button id="sameSeatButton" class="primary" type="button">same-seat 실행</button>
              </div>
            </div>
            <div class="scenario-card">
              <h3>랜덤 좌석 요청</h3>
              <p>좌석 수보다 많은 사용자가 랜덤 좌석을 요청해도 판매 완료가 좌석 수를 넘지 않는지 봅니다.</p>
              <div class="row">
                <div class="field-group">
                  <label for="randomRequests">요청 수</label>
                  <input id="randomRequests" type="number" min="1" value="500" />
                </div>
                <div class="field-group">
                  <label for="randomSeatCount">좌석 수</label>
                  <input id="randomSeatCount" type="number" min="1" value="30" />
                </div>
              </div>
              <div class="actions">
                <button id="randomSeatButton" class="primary" type="button">random-seats 실행</button>
              </div>
            </div>
            <div class="scenario-card">
              <h3>TTL 만료 후 재점유</h3>
              <p>한 번 hold 된 좌석이 TTL 후 자동으로 풀리고 다른 사용자가 다시 잡을 수 있는지 확인합니다.</p>
              <div class="actions">
                <button id="expiryButton" class="primary" type="button">expiry 실행</button>
              </div>
            </div>
            <div class="scenario-card">
              <h3>현재 이벤트 새로고침</h3>
              <p>현재 선택된 이벤트의 요약 상태와 좌석 목록을 다시 읽습니다.</p>
              <div class="actions">
                <button id="refreshEventButton" class="secondary" type="button">상태 새로고침</button>
              </div>
            </div>
          </div>
          <div class="footer-note">
            브라우저에서도 시나리오를 돌릴 수 있지만, 가장 강한 부하 측정은 여전히 CLI load test가 더 적합합니다.
          </div>
        </section>

        <section class="panel section">
          <h2>수동 조작 워크벤치</h2>
          <p>직접 이벤트를 만들고, 특정 좌석을 hold / confirm / cancel 해보면서 상태 변화를 확인할 수 있습니다.</p>
          <div class="subgrid">
            <div class="form-card">
              <h3>이벤트 생성</h3>
              <div class="field-group">
                <label for="eventIdInput">이벤트 ID</label>
                <input id="eventIdInput" type="text" placeholder="concert-001" />
              </div>
              <div class="field-group">
                <label for="titleInput">제목</label>
                <input id="titleInput" type="text" placeholder="Jungle Live" />
              </div>
              <div class="field-group">
                <label for="seatsInput">좌석 목록</label>
                <textarea id="seatsInput" placeholder="A1, A2, A3, A4"></textarea>
              </div>
              <div class="actions">
                <button id="createEventButton" class="primary" type="button">이벤트 생성</button>
                <button id="sampleEventButton" class="secondary" type="button">샘플 값 넣기</button>
              </div>
            </div>
            <div class="form-card">
              <h3>좌석 액션</h3>
              <div class="field-group">
                <label for="currentEventIdInput">현재 이벤트 ID</label>
                <input id="currentEventIdInput" type="text" placeholder="same-seat-xxxx" />
              </div>
              <div class="row">
                <div class="field-group">
                  <label for="seatIdInput">좌석 ID</label>
                  <input id="seatIdInput" type="text" placeholder="A1" />
                </div>
                <div class="field-group">
                  <label for="userIdInput">사용자 ID</label>
                  <input id="userIdInput" type="text" placeholder="user-01" />
                </div>
              </div>
              <div class="actions">
                <button id="holdButton" class="primary" type="button">hold</button>
                <button id="confirmButton" class="secondary" type="button">confirm</button>
                <button id="cancelButton" class="danger" type="button">cancel</button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="column">
        <section class="panel section">
          <h2>현재 상태</h2>
          <p>현재 이벤트의 좌석 통계와 마지막 실행 결과를 요약해서 보여줍니다.</p>
          <div class="status-strip">
            <div class="status-value">
              <span>이벤트</span>
              <strong id="statEvent">-</strong>
            </div>
            <div class="status-value">
              <span>AVAILABLE</span>
              <strong id="statAvailable">0</strong>
            </div>
            <div class="status-value">
              <span>HELD</span>
              <strong id="statHeld">0</strong>
            </div>
            <div class="status-value">
              <span>SOLD</span>
              <strong id="statSold">0</strong>
            </div>
          </div>
          <div class="badge-row" id="summaryBadges">
            <span class="badge warn">아직 시나리오를 실행하지 않았습니다</span>
          </div>
        </section>

        <section class="panel section">
          <h2>좌석 상세</h2>
          <p>각 좌석의 상태와 보유 사용자, 남은 TTL을 확인합니다.</p>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Seat</th>
                  <th>Status</th>
                  <th>User</th>
                  <th>TTL</th>
                </tr>
              </thead>
              <tbody id="seatTableBody">
                <tr>
                  <td colspan="4">아직 불러온 좌석 정보가 없습니다.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="panel section">
          <h2>로그 & 원시 응답</h2>
          <p>브라우저에서 실행한 요청 흐름과 마지막 JSON 응답을 함께 확인합니다.</p>
          <div class="log-box" id="logBox">[준비됨] 브라우저 데모가 로드되었습니다.</div>
          <div style="margin-top:16px;"></div>
          <pre id="rawOutput">{
  "message": "아직 실행 결과가 없습니다."
}</pre>
        </section>

        <section class="panel section">
          <h2>해석 가이드</h2>
          <div class="hint-list">
            <div class="hint">
              <strong>`held = 1`</strong>
              지금 임시 점유 중인 좌석이 1개 있다는 뜻입니다.
            </div>
            <div class="hint">
              <strong>`sold = 30`</strong>
              좌석 30개가 최종 예매 완료되었다는 뜻입니다.
            </div>
            <div class="hint">
              <strong>`AVAILABLE`로 복귀</strong>
              hold 후 확정하지 않아서 TTL 만료로 다시 비게 되었다는 뜻입니다.
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>

  <script>
    const DEFAULT_HOLD_TTL = __DEFAULT_HOLD_TTL__;
    const state = {
      currentEventId: "",
    };

    const elements = {
      heroTtl: document.getElementById("heroTtl"),
      healthButton: document.getElementById("healthButton"),
      healthBadges: document.getElementById("healthBadges"),
      sameSeatButton: document.getElementById("sameSeatButton"),
      randomSeatButton: document.getElementById("randomSeatButton"),
      expiryButton: document.getElementById("expiryButton"),
      refreshEventButton: document.getElementById("refreshEventButton"),
      sameSeatConcurrency: document.getElementById("sameSeatConcurrency"),
      randomRequests: document.getElementById("randomRequests"),
      randomSeatCount: document.getElementById("randomSeatCount"),
      createEventButton: document.getElementById("createEventButton"),
      sampleEventButton: document.getElementById("sampleEventButton"),
      eventIdInput: document.getElementById("eventIdInput"),
      titleInput: document.getElementById("titleInput"),
      seatsInput: document.getElementById("seatsInput"),
      currentEventIdInput: document.getElementById("currentEventIdInput"),
      seatIdInput: document.getElementById("seatIdInput"),
      userIdInput: document.getElementById("userIdInput"),
      holdButton: document.getElementById("holdButton"),
      confirmButton: document.getElementById("confirmButton"),
      cancelButton: document.getElementById("cancelButton"),
      statEvent: document.getElementById("statEvent"),
      statAvailable: document.getElementById("statAvailable"),
      statHeld: document.getElementById("statHeld"),
      statSold: document.getElementById("statSold"),
      summaryBadges: document.getElementById("summaryBadges"),
      seatTableBody: document.getElementById("seatTableBody"),
      logBox: document.getElementById("logBox"),
      rawOutput: document.getElementById("rawOutput"),
    };

    elements.heroTtl.textContent = `${DEFAULT_HOLD_TTL}초`;

    function timestamp() {
      return new Date().toLocaleTimeString("ko-KR", { hour12: false });
    }

    function log(message) {
      elements.logBox.textContent = `[${timestamp()}] ${message}\n` + elements.logBox.textContent;
    }

    function randomId(prefix) {
      return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
    }

    function sleep(ms) {
      return new Promise((resolve) => window.setTimeout(resolve, ms));
    }

    function setCurrentEventId(eventId) {
      state.currentEventId = eventId;
      elements.currentEventIdInput.value = eventId;
      elements.statEvent.textContent = eventId || "-";
    }

    function renderBadges(items) {
      elements.summaryBadges.innerHTML = items
        .map((item) => `<span class="badge ${item.type}">${item.label}</span>`)
        .join("");
    }

    function renderHealth(data) {
      const badges = [];
      badges.push({
        type: data.api ? "ok" : "warn",
        label: data.api ? "API 정상" : "API 오류",
      });
      badges.push({
        type: data.redis ? "ok" : "warn",
        label: data.redis ? `Mini Redis 정상 (${data.redisReply || "PONG"})` : "Mini Redis 연결 실패",
      });
      if (data.holdTtlSeconds) {
        badges.push({
          type: "ok",
          label: `기본 TTL ${data.holdTtlSeconds}초`,
        });
      }
      elements.healthBadges.innerHTML = badges
        .map((item) => `<span class="badge ${item.type}">${item.label}</span>`)
        .join("");
    }

    function renderStatus(status) {
      elements.statEvent.textContent = status?.eventId || state.currentEventId || "-";
      elements.statAvailable.textContent = String(status?.available ?? 0);
      elements.statHeld.textContent = String(status?.held ?? 0);
      elements.statSold.textContent = String(status?.sold ?? 0);
    }

    function renderSeats(seats) {
      if (!seats || seats.length === 0) {
        elements.seatTableBody.innerHTML = '<tr><td colspan="4">좌석 정보가 없습니다.</td></tr>';
        return;
      }
      elements.seatTableBody.innerHTML = seats
        .map((seat) => `
          <tr>
            <td>${seat.seatId}</td>
            <td><span class="seat-chip ${seat.status}">${seat.status}</span></td>
            <td>${seat.userId ?? "-"}</td>
            <td>${seat.ttl ?? "-"}</td>
          </tr>
        `)
        .join("");
    }

    function renderRaw(data) {
      elements.rawOutput.textContent = JSON.stringify(data, null, 2);
    }

    async function requestJson(path, options = {}) {
      const response = await fetch(path, {
        method: options.method || "GET",
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
      });

      const text = await response.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = text;
      }

      return {
        ok: response.ok,
        status: response.status,
        data,
      };
    }

    async function checkHealth() {
      elements.healthButton.disabled = true;
      try {
        const result = await requestJson("/health/full");
        renderHealth(result.data);
        renderRaw(result.data);
        log(result.ok ? "API와 Mini Redis 상태 확인 완료" : "상태 확인 실패");
      } catch (error) {
        renderHealth({ api: true, redis: false });
        renderRaw({ error: String(error) });
        log(`상태 확인 중 오류: ${error}`);
      } finally {
        elements.healthButton.disabled = false;
      }
    }

    function buildSeats(seatCount) {
      return Array.from({ length: seatCount }, (_, index) => `A${index + 1}`);
    }

    async function refreshCurrentEvent() {
      const eventId = elements.currentEventIdInput.value.trim();
      if (!eventId) {
        log("현재 이벤트 ID를 먼저 입력하세요.");
        return;
      }
      const [statusResult, seatsResult] = await Promise.all([
        requestJson(`/events/${eventId}/status`),
        requestJson(`/events/${eventId}/seats`),
      ]);

      if (!statusResult.ok || !seatsResult.ok) {
        renderRaw({ status: statusResult, seats: seatsResult });
        log(`이벤트 ${eventId} 조회 실패`);
        return;
      }

      setCurrentEventId(eventId);
      renderStatus(statusResult.data);
      renderSeats(seatsResult.data.seats);
      renderBadges([
        { type: "ok", label: `이벤트 ${eventId}` },
        { type: "ok", label: `AVAILABLE ${statusResult.data.available}` },
        { type: "ok", label: `HELD ${statusResult.data.held}` },
        { type: "ok", label: `SOLD ${statusResult.data.sold}` },
      ]);
      renderRaw({ status: statusResult.data, seats: seatsResult.data });
      log(`이벤트 ${eventId} 상태를 새로고침했습니다.`);
    }

    async function createManualEvent() {
      const eventId = elements.eventIdInput.value.trim();
      const title = elements.titleInput.value.trim();
      const seats = elements.seatsInput.value
        .split(",")
        .map((seat) => seat.trim())
        .filter(Boolean);

      if (!eventId || !title || seats.length === 0) {
        log("이벤트 ID, 제목, 좌석 목록을 모두 입력하세요.");
        return;
      }

      elements.createEventButton.disabled = true;
      try {
        const result = await requestJson("/events", {
          method: "POST",
          body: { eventId, title, seats },
        });
        renderRaw(result.data);
        if (!result.ok) {
          log(`이벤트 생성 실패: ${result.data?.reason ?? result.status}`);
          return;
        }
        setCurrentEventId(eventId);
        elements.seatIdInput.value = seats[0] || "";
        renderBadges([
          { type: "ok", label: `이벤트 생성 완료` },
          { type: "ok", label: `좌석 ${seats.length}개` },
        ]);
        log(`이벤트 ${eventId} 생성 완료`);
        await refreshCurrentEvent();
      } finally {
        elements.createEventButton.disabled = false;
      }
    }

    function fillSampleEvent() {
      const eventId = randomId("browser-demo");
      elements.eventIdInput.value = eventId;
      elements.titleInput.value = "Browser Live Demo";
      elements.seatsInput.value = "A1, A2, A3, A4, A5";
      elements.currentEventIdInput.value = eventId;
      elements.seatIdInput.value = "A1";
      elements.userIdInput.value = "user-01";
      log("샘플 이벤트 값을 입력했습니다.");
    }

    async function runSeatAction(action) {
      const eventId = elements.currentEventIdInput.value.trim();
      const seatId = elements.seatIdInput.value.trim();
      const userId = elements.userIdInput.value.trim();

      if (!eventId || !seatId || !userId) {
        log("이벤트 ID, 좌석 ID, 사용자 ID를 모두 입력하세요.");
        return;
      }

      const buttonMap = {
        hold: elements.holdButton,
        confirm: elements.confirmButton,
        cancel: elements.cancelButton,
      };
      buttonMap[action].disabled = true;
      try {
        const result = await requestJson(`/events/${eventId}/seats/${seatId}/${action}`, {
          method: "POST",
          body: { userId },
        });
        renderRaw(result.data);
        if (!result.ok) {
          log(`${action} 실패: ${result.data?.reason ?? result.status}`);
          return;
        }
        setCurrentEventId(eventId);
        log(`${eventId} / ${seatId} / ${action} 성공`);
        await refreshCurrentEvent();
      } finally {
        buttonMap[action].disabled = false;
      }
    }

    async function runSameSeatScenario() {
      const concurrency = Number(elements.sameSeatConcurrency.value || "1000");
      const eventId = randomId("same-seat");
      const seatId = "A1";

      elements.sameSeatButton.disabled = true;
      try {
        log(`same-seat 시나리오 시작: ${concurrency}개 요청`);
        const createResult = await requestJson("/events", {
          method: "POST",
          body: {
            eventId,
            title: "Browser Same Seat Battle",
            seats: [seatId],
          },
        });
        if (!createResult.ok) {
          renderRaw(createResult.data);
          log(`same-seat 이벤트 생성 실패: ${createResult.data?.reason ?? createResult.status}`);
          return;
        }

        const responses = await Promise.all(
          Array.from({ length: concurrency }, (_, index) =>
            requestJson(`/events/${eventId}/seats/${seatId}/hold`, {
              method: "POST",
              body: { userId: `browser-user-${index}` },
            })
          )
        );

        const success = responses.filter((item) => item.status === 200).length;
        const failure = responses.filter((item) => item.status === 409).length;
        const [statusResult, seatsResult] = await Promise.all([
          requestJson(`/events/${eventId}/status`),
          requestJson(`/events/${eventId}/seats`),
        ]);

        setCurrentEventId(eventId);
        renderStatus(statusResult.data);
        renderSeats(seatsResult.data.seats);
        renderBadges([
          { type: success === 1 ? "ok" : "warn", label: `성공 ${success}` },
          { type: failure === concurrency - 1 ? "ok" : "warn", label: `실패 ${failure}` },
          { type: "ok", label: `이벤트 ${eventId}` },
        ]);
        renderRaw({
          scenario: "same-seat",
          eventId,
          concurrency,
          success,
          failure,
          status: statusResult.data,
          seats: seatsResult.data,
        });
        log(`same-seat 완료: 성공 ${success}, 실패 ${failure}`);
      } finally {
        elements.sameSeatButton.disabled = false;
      }
    }

    async function runRandomSeatScenario() {
      const requestCount = Number(elements.randomRequests.value || "500");
      const seatCount = Number(elements.randomSeatCount.value || "30");
      const eventId = randomId("random-seats");
      const seats = buildSeats(seatCount);

      elements.randomSeatButton.disabled = true;
      try {
        log(`random-seats 시나리오 시작: 요청 ${requestCount}, 좌석 ${seatCount}`);
        const createResult = await requestJson("/events", {
          method: "POST",
          body: {
            eventId,
            title: "Browser Random Seat Rush",
            seats,
          },
        });
        if (!createResult.ok) {
          renderRaw(createResult.data);
          log(`random-seats 이벤트 생성 실패: ${createResult.data?.reason ?? createResult.status}`);
          return;
        }

        const holdResponses = await Promise.all(
          Array.from({ length: requestCount }, (_, index) => {
            const seatId = seats[Math.floor(Math.random() * seats.length)];
            const userId = `browser-user-${index}`;
            return requestJson(`/events/${eventId}/seats/${seatId}/hold`, {
              method: "POST",
              body: { userId },
            }).then((result) => ({ seatId, userId, result }));
          })
        );

        const winners = holdResponses
          .filter((item) => item.result.status === 200)
          .map((item) => ({ seatId: item.seatId, userId: item.userId }));

        const confirmResponses = await Promise.all(
          winners.map((winner) =>
            requestJson(`/events/${eventId}/seats/${winner.seatId}/confirm`, {
              method: "POST",
              body: { userId: winner.userId },
            })
          )
        );

        const confirmed = confirmResponses.filter((item) => item.status === 200).length;
        const [statusResult, seatsResult] = await Promise.all([
          requestJson(`/events/${eventId}/status`),
          requestJson(`/events/${eventId}/seats`),
        ]);

        setCurrentEventId(eventId);
        renderStatus(statusResult.data);
        renderSeats(seatsResult.data.seats);
        renderBadges([
          { type: "ok", label: `hold 성공 ${winners.length}` },
          { type: "ok", label: `confirm 성공 ${confirmed}` },
          { type: confirmed <= seatCount ? "ok" : "warn", label: `좌석 수 ${seatCount}` },
        ]);
        renderRaw({
          scenario: "random-seats",
          eventId,
          requestCount,
          seatCount,
          holdSuccess: winners.length,
          confirmed,
          status: statusResult.data,
          seats: seatsResult.data,
        });
        log(`random-seats 완료: hold ${winners.length}, confirm ${confirmed}`);
      } finally {
        elements.randomSeatButton.disabled = false;
      }
    }

    async function runExpiryScenario() {
      const eventId = randomId("expiry");
      const seatId = "A1";

      elements.expiryButton.disabled = true;
      try {
        log("expiry 시나리오 시작");
        const createResult = await requestJson("/events", {
          method: "POST",
          body: {
            eventId,
            title: "Browser Expiry Flow",
            seats: [seatId],
          },
        });
        if (!createResult.ok) {
          renderRaw(createResult.data);
          log(`expiry 이벤트 생성 실패: ${createResult.data?.reason ?? createResult.status}`);
          return;
        }

        const firstHold = await requestJson(`/events/${eventId}/seats/${seatId}/hold`, {
          method: "POST",
          body: { userId: "browser-first" },
        });
        const seatsAfterHold = await requestJson(`/events/${eventId}/seats`);
        const ttl = seatsAfterHold.data?.seats?.[0]?.ttl ?? DEFAULT_HOLD_TTL;

        log(`첫 hold 성공, TTL ${ttl}초 대기`);
        await sleep((ttl + 1) * 1000);

        const secondHold = await requestJson(`/events/${eventId}/seats/${seatId}/hold`, {
          method: "POST",
          body: { userId: "browser-second" },
        });
        const [statusResult, seatsResult] = await Promise.all([
          requestJson(`/events/${eventId}/status`),
          requestJson(`/events/${eventId}/seats`),
        ]);

        setCurrentEventId(eventId);
        renderStatus(statusResult.data);
        renderSeats(seatsResult.data.seats);
        renderBadges([
          { type: firstHold.status === 200 ? "ok" : "warn", label: `첫 hold ${firstHold.status}` },
          { type: secondHold.status === 200 ? "ok" : "warn", label: `두 번째 hold ${secondHold.status}` },
          { type: "ok", label: `TTL ${ttl}초 대기 완료` },
        ]);
        renderRaw({
          scenario: "expiry",
          eventId,
          firstHold,
          secondHold,
          status: statusResult.data,
          seats: seatsResult.data,
        });
        log(`expiry 완료: 첫 hold ${firstHold.status}, 두 번째 hold ${secondHold.status}`);
      } finally {
        elements.expiryButton.disabled = false;
      }
    }

    elements.healthButton.addEventListener("click", checkHealth);
    elements.refreshEventButton.addEventListener("click", refreshCurrentEvent);
    elements.createEventButton.addEventListener("click", createManualEvent);
    elements.sampleEventButton.addEventListener("click", fillSampleEvent);
    elements.holdButton.addEventListener("click", () => runSeatAction("hold"));
    elements.confirmButton.addEventListener("click", () => runSeatAction("confirm"));
    elements.cancelButton.addEventListener("click", () => runSeatAction("cancel"));
    elements.sameSeatButton.addEventListener("click", runSameSeatScenario);
    elements.randomSeatButton.addEventListener("click", runRandomSeatScenario);
    elements.expiryButton.addEventListener("click", runExpiryScenario);

    fillSampleEvent();
    checkHealth();
  </script>
</body>
</html>
"""


def render_demo_page(default_hold_ttl: int) -> str:
    return DEMO_PAGE.replace("__DEFAULT_HOLD_TTL__", str(default_hold_ttl))
