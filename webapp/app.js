const state = {
  eventId: "concert-demo",
  selectedSeatId: "",
  logs: [],
  payload: null,
};

const ui = {
  serverStatus: document.getElementById("serverStatus"),
  refreshButton: document.getElementById("refreshButton"),
  eventTitle: document.getElementById("eventTitle"),
  eventSubtitle: document.getElementById("eventSubtitle"),
  selectedSeatInfo: document.getElementById("selectedSeatInfo"),
  metricActive: document.getElementById("metricActive"),
  metricWaiting: document.getElementById("metricWaiting"),
  metricAvailable: document.getElementById("metricAvailable"),
  metricHeld: document.getElementById("metricHeld"),
  metricSold: document.getElementById("metricSold"),
  storeStats: document.getElementById("storeStats"),
  seatBoard: document.getElementById("seatBoard"),
  admittedList: document.getElementById("admittedList"),
  waitingList: document.getElementById("waitingList"),
  eventIdInput: document.getElementById("eventIdInput"),
  activeLimitInput: document.getElementById("activeLimitInput"),
  holdTtlInput: document.getElementById("holdTtlInput"),
  seatsCsvInput: document.getElementById("seatsCsvInput"),
  userIdInput: document.getElementById("userIdInput"),
  userState: document.getElementById("userState"),
  simulationResult: document.getElementById("simulationResult"),
  simUsersInput: document.getElementById("simUsersInput"),
  simScenarioSelect: document.getElementById("simScenarioSelect"),
  initButton: document.getElementById("initButton"),
  resetButton: document.getElementById("resetButton"),
  enterButton: document.getElementById("enterButton"),
  statusButton: document.getElementById("statusButton"),
  holdButton: document.getElementById("holdButton"),
  confirmButton: document.getElementById("confirmButton"),
  cancelButton: document.getElementById("cancelButton"),
  exitButton: document.getElementById("exitButton"),
  simulateButton: document.getElementById("simulateButton"),
  logStream: document.getElementById("logStream"),
  queueOverlay: document.getElementById("queueOverlay"),
  queuePosition: document.getElementById("queuePosition"),
};

function addLog(message, tone = "info") {
  const time = new Date().toLocaleTimeString("ko-KR", { hour12: false });
  state.logs.unshift({ time, message, tone });
  state.logs = state.logs.slice(0, 80);
  renderLogs();
}

function renderLogs() {
  ui.logStream.innerHTML = "";
  state.logs.forEach((entry) => {
    const item = document.createElement("article");
    item.className = "log-item";
    item.innerHTML = `<strong>${entry.time}</strong> ${entry.message}`;
    ui.logStream.appendChild(item);
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.reason || payload.message || "request failed");
  }
  return payload;
}

function renderState(payload) {
  state.payload = payload;
  state.eventId = payload.event_id;

  ui.serverStatus.textContent = "online";
  ui.eventTitle.textContent = payload.event_id;
  ui.eventSubtitle.textContent = `active limit ${payload.active_limit} / hold ttl ${payload.hold_seconds}s`;
  ui.metricActive.textContent = String(payload.active_count);
  ui.metricWaiting.textContent = String(payload.queue_size);
  ui.metricAvailable.textContent = String(payload.metrics.available);
  ui.metricHeld.textContent = String(payload.metrics.held);
  ui.metricSold.textContent = String(payload.metrics.sold);
  ui.storeStats.textContent = `keys=${payload.store_stats.total_keys} / expiring=${payload.store_stats.expiring_keys} / invalidated=${payload.store_stats.invalidated_keys}`;

  renderSeatBoard(payload.seats);
  renderList(ui.admittedList, payload.admitted_users, (userId) => userId);
  renderList(ui.waitingList, payload.waiting_users, (item) => `${item.position}. ${item.user_id}`);

  const currentUser = currentUserId();
  const waitingUser = payload.waiting_users.find(u => u.user_id === currentUser);
  if (waitingUser) {
    ui.queuePosition.textContent = waitingUser.position;
    ui.queueOverlay.classList.remove("hidden");
  } else {
    ui.queueOverlay.classList.add("hidden");
  }
}

function renderList(target, items, formatter) {
  target.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = "없음";
    target.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = formatter(item);
    target.appendChild(li);
  });
}

function renderSeatBoard(seats) {
  ui.seatBoard.innerHTML = "";
  const grouped = groupSeatsBySection(seats);

  Array.from(grouped.entries()).forEach(([sectionLabel, rows]) => {
    const section = document.createElement("section");
    section.className = "seat-section";

    const title = document.createElement("div");
    title.className = "section-title";
    title.textContent = sectionLabel;
    section.appendChild(title);

    Array.from(rows.entries()).forEach(([rowLabel, rowSeats]) => {
      rowSeats.sort((a, b) => a.meta.number - b.meta.number);

      const row = document.createElement("div");
      row.className = "seat-row";

      const label = document.createElement("div");
      label.className = "row-label";
      label.textContent = rowLabel;
      row.appendChild(label);

      const container = document.createElement("div");
      container.className = "row-seats";

      let previousNumber = rowSeats[0]?.meta.number ?? 0;
      rowSeats.forEach((seat, index) => {
        if (index > 0) {
          const gap = seat.meta.number - previousNumber;
          if (gap > 1) {
            for (let count = 1; count < gap; count += 1) {
              const aisle = document.createElement("div");
              aisle.className = "seat-gap";
              container.appendChild(aisle);
            }
          }
        }

        const button = document.createElement("button");
        button.className = `seat-button ${seat.status.toLowerCase()}${state.selectedSeatId === seat.seat_id ? " selected" : ""}`;
        button.type = "button";
        button.innerHTML = `<span>${seat.meta.display}</span>`;
        if (seat.status === "HELD" && seat.ttl !== null) {
          button.innerHTML += `<small>${seat.ttl}s</small>`;
        } else if (seat.user_id) {
          button.innerHTML += `<small>${seat.user_id}</small>`;
        }
        button.addEventListener("click", () => selectSeat(seat));
        container.appendChild(button);
        previousNumber = seat.meta.number;
      });

      row.appendChild(container);
      section.appendChild(row);
    });

    ui.seatBoard.appendChild(section);
  });
}

function parseSeatMeta(seatId) {
  if (seatId.includes("-")) {
    const [section, rawRow] = seatId.split("-", 2);
    const row = rawRow.replace(/[0-9]/g, "") || rawRow;
    const number = Number(rawRow.match(/\d+/)?.[0] || 0);
    return {
      section,
      row,
      number,
      display: String(number),
    };
  }

  const row = seatId.replace(/[0-9]/g, "") || "ROW";
  const number = Number(seatId.match(/\d+/)?.[0] || 0);
  return {
    section: "FLOOR",
    row,
    number,
    display: number ? String(number) : seatId,
  };
}

function groupSeatsBySection(seats) {
  const grouped = new Map();
  seats.forEach((seat) => {
    const meta = parseSeatMeta(seat.seat_id);
    const seatWithMeta = { ...seat, meta };
    if (!grouped.has(meta.section)) grouped.set(meta.section, new Map());
    const sectionRows = grouped.get(meta.section);
    if (!sectionRows.has(meta.row)) sectionRows.set(meta.row, []);
    sectionRows.get(meta.row).push(seatWithMeta);
  });
  return grouped;
}

function selectSeat(seat) {
  state.selectedSeatId = seat.seat_id;
  ui.selectedSeatInfo.textContent = `${seat.seat_id} / ${seat.status}${seat.user_id ? ` / ${seat.user_id}` : ""}`;
  if (state.payload) {
    renderSeatBoard(state.payload.seats);
  }
}

async function refreshState() {
  try {
    const payload = await api(`/api/state?event_id=${encodeURIComponent(ui.eventIdInput.value.trim() || state.eventId)}`);
    renderState(payload);
  } catch (error) {
    ui.serverStatus.textContent = "offline";
    addLog(error.message, "error");
  }
}

function formatUserState(payload) {
  if (!payload) return "상태: 알 수 없음";
  if (payload.ok === false) return `<span style="color:var(--primary); font-weight:bold;">오류: ${payload.reason || "알 수 없음"}</span>`;
  
  switch (payload.status) {
    case "NONE": return `<span style="color:var(--muted)">대기 중 (NONE)</span>`;
    case "ADMITTED": return `상태: <strong style="color:var(--primary)">입장 완료</strong>`;
    case "WAITING": return `상태: 대기 중 (내 순서: <strong style="color:var(--primary)">${payload.position}</strong>번째)`;
    case "HELD": return `상태: 좌석 <strong style="color:#fadb14">HOLD</strong> (${payload.seat_id || payload.seatId})`;
    case "CONFIRMED": return `상태: 🎉 <strong style="color:var(--primary)">예매 확정</strong> (${payload.seat_id || payload.seatId})`;
    case "CANCELLED": return `상태: <span style="color:var(--muted)">예약 취소됨</span>`;
    case "EXITED": return `상태: <span style="color:var(--muted)">예매 이탈함</span>`;
    case "REMOVED_FROM_QUEUE": return `상태: <span style="color:var(--muted)">대기열에서 이탈함</span>`;
    default: return `상태: ${payload.status || "완료"}`;
  }
}

async function postAndRefresh(path, body, successMessage) {
  try {
    const payload = await api(path, { method: "POST", body: JSON.stringify(body) });
    ui.userState.innerHTML = formatUserState(payload);
    addLog(successMessage || "상태 업데이트 완료");
    await refreshState();
  } catch (error) {
    ui.userState.innerHTML = `<span style="color:var(--primary); font-weight:bold;">오류: ${error.message}</span>`;
    addLog(error.message, "error");
  }
}

function currentEventId() {
  return ui.eventIdInput.value.trim() || state.eventId;
}

function currentUserId() {
  return ui.userIdInput.value.trim();
}

function bindEvents() {
  ui.refreshButton.addEventListener("click", refreshState);
  ui.initButton.addEventListener("click", () =>
    postAndRefresh(
      "/api/init",
      {
        eventId: currentEventId(),
        activeLimit: Number(ui.activeLimitInput.value),
        holdTtl: Number(ui.holdTtlInput.value),
        seatsCsv: ui.seatsCsvInput.value,
      },
      "이벤트를 초기화했습니다.",
    )
  );
  ui.resetButton.addEventListener("click", () =>
    postAndRefresh("/api/reset", { eventId: currentEventId() }, "대기열과 상태를 리셋했습니다.")
  );
  ui.enterButton.addEventListener("click", () =>
    postAndRefresh("/api/enter", { eventId: currentEventId(), userId: currentUserId() }, "사용자를 예매 플로우에 진입시켰습니다.")
  );
  ui.statusButton.addEventListener("click", () =>
    postAndRefresh("/api/status", { eventId: currentEventId(), userId: currentUserId() }, "사용자 상태를 조회했습니다.")
  );
  ui.holdButton.addEventListener("click", () => {
    if (!state.selectedSeatId) {
      addLog("좌석을 먼저 선택하세요.", "error");
      return;
    }
    postAndRefresh(
      "/api/hold",
      { eventId: currentEventId(), userId: currentUserId(), seatId: state.selectedSeatId },
      "선택 좌석 hold 요청을 보냈습니다.",
    );
  });
  ui.confirmButton.addEventListener("click", () =>
    postAndRefresh("/api/confirm", { eventId: currentEventId(), userId: currentUserId() }, "hold 좌석을 confirm 했습니다.")
  );
  ui.cancelButton.addEventListener("click", () =>
    postAndRefresh("/api/cancel", { eventId: currentEventId(), userId: currentUserId() }, "hold 좌석을 cancel 했습니다.")
  );
  ui.exitButton.addEventListener("click", () =>
    postAndRefresh("/api/exit", { eventId: currentEventId(), userId: currentUserId() }, "사용자를 예매 플로우에서 이탈시켰습니다.")
  );
  ui.simulateButton.addEventListener("click", async () => {
    ui.simulationResult.innerHTML = '<span class="sim-stat">시뮬레이션 실행 중... ⏳</span>';
    try {
      const payload = await api("/api/simulate", {
        method: "POST",
        body: JSON.stringify({
          eventId: currentEventId(),
          users: Number(ui.simUsersInput.value),
          scenario: ui.simScenarioSelect.value,
          selectedSeat: state.selectedSeatId,
        }),
      });
      ui.simulationResult.innerHTML = `
        <div class="sim-stat total">👥 투입: <b>${payload.users}</b>명</div>
        <div class="sim-stat success">🎟️ 예매 성공: <b>${payload.confirmed}</b>명</div>
        <div class="sim-stat fail">⚔️ 경쟁 실패: <b>${payload.hold_fail}</b>명</div>
        <div class="sim-stat cancel">❌ 취소 발생: <b>${payload.cancelled}</b>명</div>
        <div class="sim-stat timeout">⏱️ 시간 초과: <b>${payload.timed_out}</b>명</div>
      `;
      addLog(`시뮬레이션 완료 (성공: ${payload.confirmed}명)`);
      renderState(payload.final_state);
    } catch (error) {
      ui.simulationResult.textContent = error.message;
      addLog(error.message, "error");
    }
  });
}

async function initialize() {
  bindEvents();
  await refreshState();
  addLog("대시보드 준비 완료");
  setInterval(refreshState, 1000);
}

initialize();
