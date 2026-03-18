const API_BASE_URL = "http://127.0.0.1:8000";

const state = {
  show: {
    id: "show-2026-midnight-signal",
    title: "Midnight Signal Tour",
    description: "A one-night performance mixing neon city atmosphere, heavy drums, and live visual staging.",
    venue: "Jungle Arena",
    date: "2026-04-08 19:30",
  },
  serverOnline: false,
  seats: [],
  selectedSeatId: null,
  diagnostics: {
    conflictFailures: 0,
    manualWins: 0,
    simulatorWins: 0,
    backendErrors: 0,
  },
  simulation: {
    running: false,
    rpm: 60,
    workers: 3,
    strategy: "random",
    cancelRatio: 15,
    timers: [],
    stats: {
      total: 0,
      success: 0,
      failed: 0,
    },
  },
  logs: [],
};

const ui = {
  serverStatusText: document.getElementById("serverStatusText"),
  heroStatus: document.querySelector(".hero-status"),
  showTitle: document.getElementById("showTitle"),
  showDescription: document.getElementById("showDescription"),
  showDate: document.getElementById("showDate"),
  showVenue: document.getElementById("showVenue"),
  totalSeatsMetric: document.getElementById("totalSeatsMetric"),
  remainingSeatsMetric: document.getElementById("remainingSeatsMetric"),
  bookedSeatsMetric: document.getElementById("bookedSeatsMetric"),
  selectedSeatLabel: document.getElementById("selectedSeatLabel"),
  bookingFeedback: document.getElementById("bookingFeedback"),
  seatMap: document.getElementById("seatMap"),
  logStream: document.getElementById("logStream"),
  totalRequestsMetric: document.getElementById("totalRequestsMetric"),
  successRequestsMetric: document.getElementById("successRequestsMetric"),
  failedRequestsMetric: document.getElementById("failedRequestsMetric"),
  conflictMetric: document.getElementById("conflictMetric"),
  manualWinsMetric: document.getElementById("manualWinsMetric"),
  simWinsMetric: document.getElementById("simWinsMetric"),
  successRateMetric: document.getElementById("successRateMetric"),
  simStatusPill: document.getElementById("simStatusPill"),
  snapshotSummary: document.getElementById("snapshotSummary"),
  conflictSummary: document.getElementById("conflictSummary"),
  integritySummary: document.getElementById("integritySummary"),
  rpmInput: document.getElementById("rpmInput"),
  workerInput: document.getElementById("workerInput"),
  strategySelect: document.getElementById("strategySelect"),
  cancelRatioInput: document.getElementById("cancelRatioInput"),
  refreshButton: document.getElementById("refreshButton"),
  bookButton: document.getElementById("bookButton"),
  cancelButton: document.getElementById("cancelButton"),
  startSimulationButton: document.getElementById("startSimulationButton"),
  stopSimulationButton: document.getElementById("stopSimulationButton"),
  clearLogButton: document.getElementById("clearLogButton"),
};

function buildInitialSeats() {
  const rows = ["A", "B", "C", "D", "E", "F"];
  const seats = [];
  rows.forEach((row, rowIndex) => {
    for (let number = 1; number <= 8; number += 1) {
      seats.push({
        id: `${row}-${String(number).padStart(2, "0")}`,
        row,
        number,
        order: rowIndex * 8 + number,
        status: "available",
        owner: null,
      });
    }
  });
  return seats;
}

function initialize() {
  state.seats = buildInitialSeats();
  renderAll();
  bindEvents();
  addLog("system", "The front-end simulation panel is ready.", "info");
  refreshFromBackend();
}

function bindEvents() {
  ui.refreshButton.addEventListener("click", refreshFromBackend);
  ui.bookButton.addEventListener("click", () => runManualAction("book"));
  ui.cancelButton.addEventListener("click", () => runManualAction("cancel"));
  ui.startSimulationButton.addEventListener("click", startSimulation);
  ui.stopSimulationButton.addEventListener("click", stopSimulation);
  ui.clearLogButton.addEventListener("click", clearLogs);
}

function renderAll() {
  renderShowInfo();
  renderSeatMap();
  renderMetrics();
  renderSimulationStats();
  renderLogs();
  renderDiagnostics();
}

function renderShowInfo() {
  ui.showTitle.textContent = state.show.title;
  ui.showDescription.textContent = state.show.description;
  ui.showDate.textContent = state.show.date;
  ui.showVenue.textContent = state.show.venue;
  ui.serverStatusText.textContent = state.serverOnline ? "Back-end connected" : "Back-end offline";
  ui.heroStatus.classList.toggle("online", Boolean(state.serverOnline));
}

function renderSeatMap() {
  ui.seatMap.innerHTML = "";
  state.seats.forEach((seat) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `seat ${seat.status}${state.selectedSeatId === seat.id ? " selected" : ""}`;
    button.textContent = seat.id;
    button.dataset.seatId = seat.id;
    button.disabled = seat.status === "held";
    if (seat.status === "booked") {
      button.disabled = false;
    }
    button.addEventListener("click", () => selectSeat(seat.id));
    ui.seatMap.appendChild(button);
  });
}

function renderMetrics() {
  const total = state.seats.length;
  const remaining = state.seats.filter((seat) => seat.status === "available").length;
  const booked = state.seats.filter((seat) => seat.status === "booked").length;
  ui.totalSeatsMetric.textContent = String(total);
  ui.remainingSeatsMetric.textContent = String(remaining);
  ui.bookedSeatsMetric.textContent = String(booked);
  ui.selectedSeatLabel.textContent = state.selectedSeatId ?? "None";
}

function renderSimulationStats() {
  ui.totalRequestsMetric.textContent = String(state.simulation.stats.total);
  ui.successRequestsMetric.textContent = String(state.simulation.stats.success);
  ui.failedRequestsMetric.textContent = String(state.simulation.stats.failed);
  ui.conflictMetric.textContent = String(state.diagnostics.conflictFailures);
  ui.manualWinsMetric.textContent = String(state.diagnostics.manualWins);
  ui.simWinsMetric.textContent = String(state.diagnostics.simulatorWins);
  const total = state.simulation.stats.total || 0;
  const rate = total === 0 ? 0 : Math.round((state.simulation.stats.success / total) * 100);
  ui.successRateMetric.textContent = `${rate}%`;
  ui.simStatusPill.textContent = state.simulation.running ? "Running" : "Stopped";
}

function renderLogs() {
  ui.logStream.innerHTML = "";
  const logsToRender = state.logs.slice(0, 60);
  logsToRender.forEach((entry) => {
    const item = document.createElement("article");
    item.className = `log-item ${entry.variant}`;
    item.innerHTML = `
      <div class="log-meta">
        <span>${entry.time}</span>
        <span>${entry.source}</span>
      </div>
      <div class="log-message">${entry.message}</div>
    `;
    ui.logStream.appendChild(item);
  });
}

function renderDiagnostics() {
  const remaining = state.seats.filter((seat) => seat.status === "available").length;
  const booked = state.seats.filter((seat) => seat.status === "booked").length;
  const unknownStatusCount = state.seats.filter((seat) => !["available", "booked", "held"].includes(seat.status)).length;
  const selectedExists = state.selectedSeatId ? Boolean(getSeatById(state.selectedSeatId)) : true;
  const simulatorOwned = state.seats.filter((seat) => String(seat.owner || "").startsWith("simulator")).length;
  const manualOwned = state.seats.filter((seat) => seat.owner === "manual").length;
  const total = state.seats.length;

  setSummaryList(ui.snapshotSummary, [
    summaryItem(`Back-end status: ${state.serverOnline ? "online" : "offline"}`, state.serverOnline ? "good" : "bad"),
    summaryItem(`Remaining seats: ${remaining} / ${total}`, "good"),
    summaryItem(`Booked seats: ${booked}`, "warn"),
    summaryItem(`Current selection: ${state.selectedSeatId || "None"}`, selectedExists ? "good" : "bad"),
  ]);

  setSummaryList(ui.conflictSummary, [
    summaryItem(`Conflict failures recorded: ${state.diagnostics.conflictFailures}`, state.diagnostics.conflictFailures > 0 ? "warn" : "good"),
    summaryItem(`Manual wins recorded: ${state.diagnostics.manualWins}`, "good"),
    summaryItem(`Simulator wins recorded: ${state.diagnostics.simulatorWins}`, "good"),
    summaryItem(`Back-end request errors: ${state.diagnostics.backendErrors}`, state.diagnostics.backendErrors > 0 ? "bad" : "good"),
  ]);

  setSummaryList(ui.integritySummary, [
    summaryItem(`Seat totals consistent: ${remaining + booked <= total ? "yes" : "no"}`, remaining + booked <= total ? "good" : "bad"),
    summaryItem(`Unknown seat statuses: ${unknownStatusCount}`, unknownStatusCount === 0 ? "good" : "bad"),
    summaryItem(`Seats booked by manual flow: ${manualOwned}`, "good"),
    summaryItem(`Seats booked by simulator flow: ${simulatorOwned}`, "warn"),
  ]);
}

function setSummaryList(target, items) {
  target.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = item.tone;
    li.textContent = item.label;
    target.appendChild(li);
  });
}

function summaryItem(label, tone) {
  return { label, tone };
}

function selectSeat(seatId) {
  state.selectedSeatId = state.selectedSeatId === seatId ? null : seatId;
  const seat = getSeatById(state.selectedSeatId);
  if (!seat) {
    ui.bookingFeedback.textContent = "Choose a seat, then book it or cancel it.";
  } else if (seat.status === "booked") {
    ui.bookingFeedback.textContent = `${seat.id} is already booked. You can cancel it to reopen the seat.`;
  } else if (seat.status === "held") {
    ui.bookingFeedback.textContent = `${seat.id} is temporarily held by the simulator.`;
  } else {
    ui.bookingFeedback.textContent = `${seat.id} is selected and ready to book.`;
  }
  renderSeatMap();
  renderMetrics();
}

async function runManualAction(action) {
  const seat = getSeatById(state.selectedSeatId);
  if (!seat) {
    ui.bookingFeedback.textContent = "Select a seat first.";
    return;
  }

  try {
    let payload;
    if (action === "book") {
      payload = await postJson("/api/book", { seatId: seat.id, actor: "manual" });
    } else {
      payload = await postJson("/api/cancel", { seatId: seat.id, actor: "manual" });
    }

    applyStatePayload(payload.state);
    state.simulation.stats.total += 1;
    if (payload.ok) {
      state.simulation.stats.success += 1;
      state.diagnostics.manualWins += action === "book" ? 1 : 0;
      ui.bookingFeedback.textContent = payload.message;
      addLog("manual", payload.message, "success");
    } else {
      state.simulation.stats.failed += 1;
      if (payload.message.includes("not available") || payload.message.includes("cannot be canceled")) {
        state.diagnostics.conflictFailures += 1;
      }
      ui.bookingFeedback.textContent = payload.message;
      addLog("manual", payload.message, "fail");
    }
  } catch (error) {
    state.serverOnline = false;
    state.simulation.stats.total += 1;
    state.simulation.stats.failed += 1;
    state.diagnostics.backendErrors += 1;
    ui.bookingFeedback.textContent = `Request failed: ${error.message}`;
    addLog("manual", `Request failed: ${error.message}`, "fail");
  }

  renderAll();
}

async function refreshFromBackend() {
  try {
    const payload = await getJson("/api/status");
    applyStatePayload(payload);
    state.serverOnline = true;
    ui.bookingFeedback.textContent = "State refreshed from the back-end API.";
    addLog("system", "State refreshed from the back-end API.", "info");
    renderAll();
  } catch (error) {
    state.serverOnline = false;
    state.diagnostics.backendErrors += 1;
    ui.bookingFeedback.textContent = `Back-end refresh failed: ${error.message}`;
    addLog("system", `Back-end refresh failed: ${error.message}`, "fail");
    renderAll();
  }
}

function startSimulation() {
  if (state.simulation.running) {
    addLog("simulator", "The simulation is already running.", "info");
    return;
  }

  state.simulation.rpm = clampNumber(Number(ui.rpmInput.value), 1, 1200, 60);
  state.simulation.workers = clampNumber(Number(ui.workerInput.value), 1, 20, 3);
  state.simulation.strategy = ui.strategySelect.value;
  state.simulation.cancelRatio = clampNumber(Number(ui.cancelRatioInput.value), 0, 100, 15);
  state.simulation.running = true;
  state.simulation.timers = [];

  const interval = Math.max(120, Math.floor((60000 / state.simulation.rpm) * state.simulation.workers));
  for (let worker = 0; worker < state.simulation.workers; worker += 1) {
    const timerId = window.setInterval(() => {
      runSimulatorTick(worker + 1);
    }, interval);
    state.simulation.timers.push(timerId);
  }

  addLog(
    "simulator",
    `Simulation started: ${state.simulation.rpm} req/min, ${state.simulation.workers} workers, cancel ratio ${state.simulation.cancelRatio}%`,
    "info",
  );
  renderSimulationStats();
}

function stopSimulation() {
  state.simulation.timers.forEach((timerId) => window.clearInterval(timerId));
  state.simulation.timers = [];
  state.simulation.running = false;
  addLog("simulator", "Simulation stopped.", "info");
  renderSimulationStats();
}

function clearLogs() {
  state.logs = [];
  renderLogs();
}

async function runSimulatorTick(workerId) {
  const shouldCancel = Math.random() * 100 < state.simulation.cancelRatio;
  state.simulation.stats.total += 1;

  try {
    const payload = await postJson("/api/simulate-step", {
      strategy: state.simulation.strategy,
      cancel: shouldCancel,
      actor: `simulator-${workerId}`,
    });
    applyStatePayload(payload.state);
    state.serverOnline = true;

    if (payload.ok) {
      state.simulation.stats.success += 1;
      if (shouldCancel) {
        state.diagnostics.manualWins += 0;
      } else {
        state.diagnostics.simulatorWins += 1;
      }
      addLog("simulator", `worker-${workerId}: ${payload.message}`, "success");
      if (payload.seat && payload.seat.id === state.selectedSeatId) {
        ui.bookingFeedback.textContent = payload.message;
      }
    } else {
      state.simulation.stats.failed += 1;
      if (payload.message.includes("No seat is available") || payload.message.includes("not available")) {
        state.diagnostics.conflictFailures += 1;
      }
      addLog("simulator", `worker-${workerId}: ${payload.message}`, "fail");
    }
  } catch (error) {
    state.serverOnline = false;
    state.simulation.stats.failed += 1;
    state.diagnostics.backendErrors += 1;
    addLog("simulator", `worker-${workerId}: request failed: ${error.message}`, "fail");
  }

  renderAll();
}

function addLog(source, message, variant) {
  state.logs.unshift({
    source,
    message,
    variant,
    time: new Date().toLocaleTimeString("en-US", { hour12: false }),
  });
  state.logs = state.logs.slice(0, 120);
  renderLogs();
}

function getSeatById(seatId) {
  return state.seats.find((seat) => seat.id === seatId) ?? null;
}

function applyStatePayload(payload) {
  if (!payload) {
    return;
  }

  if (payload.show) {
    state.show = {
      ...state.show,
      ...payload.show,
    };
  }

  if (Array.isArray(payload.seats)) {
    state.seats = payload.seats.map((seat, index) => ({
      id: seat.id,
      status: seat.status || "available",
      owner: seat.owner || null,
      order: index + 1,
    }));
  }
}

async function getJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || `HTTP ${response.status}`);
  }
  return payload;
}

async function postJson(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    return payload;
  }
  return payload;
}

function clampNumber(value, min, max, fallback) {
  if (Number.isNaN(value)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, value));
}

initialize();
