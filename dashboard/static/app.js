const overviewEl = document.getElementById("overview");
const gridEl = document.getElementById("bot-grid");
const updatedEl = document.getElementById("updated-at");

function fmtBool(value) {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "unknown";
}

function fmtMoney(value) {
  if (value === null || value === undefined) return "unknown";
  return `${Number(value).toFixed(4)} USDT`;
}

function pill(text, state) {
  return `<span class="pill ${state}">${text}</span>`;
}

function statusPill(ok, unknownText = "unknown") {
  if (ok === true) return pill("online", "ok");
  if (ok === false) return pill("offline", "bad");
  return pill(unknownText, "warn");
}

function renderOverview(data) {
  const overview = data.overview;
  const metrics = [
    ["All bots", overview.bot_count],
    ["Online bots", overview.online_count],
    ["Dry-run all online", fmtBool(overview.dry_run_all_online)],
    ["Today simulated PnL", fmtMoney(overview.today_total_pnl)],
    ["Open trades", overview.total_open_trades],
    ["Risk triggered", fmtBool(overview.any_risk_triggered)],
    ["Any offline", fmtBool(overview.any_offline)],
    ["Any error", fmtBool(overview.any_error)],
  ];
  overviewEl.innerHTML = metrics
    .map(([label, value]) => `<article class="metric"><div class="label">${label}</div><div class="value">${value}</div></article>`)
    .join("");
  updatedEl.textContent = `Updated ${new Date(overview.updated_at * 1000).toLocaleString()}`;
}

function renderBot(bot) {
  const riskState = bot.risk_status === "ok" ? "ok" : bot.risk_status === "blocked" ? "bad" : "warn";
  const rows = [
    ["Dry-run", fmtBool(bot.dry_run)],
    ["Trading pair", bot.pair],
    ["Open trades", bot.open_trades],
    ["Current simulated PnL", fmtMoney(bot.current_pnl)],
    ["Today simulated PnL", fmtMoney(bot.today_pnl)],
    ["Recent trade", bot.recent_trade || "none"],
    ["Recent error", bot.recent_error || "none"],
    ["Risk status", pill(bot.risk_status, riskState)],
    ["Kill switch", bot.kill_switch_active ? pill("active", "bad") : pill("inactive", "ok")],
  ];

  if (bot.key === "xaut") {
    const validation = bot.xaut_validation || {};
    rows.push(
      ["XAUT futures validation", validation.futures_exists ? pill("passed", "ok") : pill("not passed", "warn")],
      ["XAUT bot started", fmtBool(bot.xaut_started)],
      ["Exchange template", validation.exchange || "unknown"],
      ["XAUT not-started reason", bot.xaut_not_started_reason || validation.reason || "none"],
    );
  }

  return `
    <article class="card">
      <div class="card-head">
        <div class="asset">
          <div class="symbol">${bot.label.slice(0, 2)}</div>
          <div>
            <h2>${bot.label}</h2>
            <div class="pair">Local UI 127.0.0.1:${bot.local_port}</div>
          </div>
        </div>
        ${statusPill(bot.online)}
      </div>
      <div class="rows">
        ${rows
          .map(([name, value]) => `<div class="row"><div class="name">${name}</div><div class="data">${value}</div></div>`)
          .join("")}
      </div>
    </article>
  `;
}

async function loadSummary() {
  try {
    const response = await fetch("/api/summary", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderOverview(data);
    gridEl.innerHTML = data.bots.map(renderBot).join("");
  } catch (error) {
    updatedEl.textContent = "Dashboard API unavailable";
    overviewEl.innerHTML = "";
    gridEl.innerHTML = `<div class="empty">Unable to load dashboard data: ${error.message}</div>`;
  }
}

loadSummary();
setInterval(loadSummary, 15000);
