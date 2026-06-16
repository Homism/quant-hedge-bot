const overviewEl = document.getElementById("overview");
const gridEl = document.getElementById("bot-grid");
const updatedEl = document.getElementById("updated-at");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmtBool(value) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "未知";
}

function fmtEmpty(value) {
  if (value === null || value === undefined || value === "" || value === "none") return "无";
  return escapeHtml(value);
}

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "暂无数据";
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtPrice(value) {
  return value === null || value === undefined ? "暂无数据" : `${fmtNumber(value, 4)} USDT`;
}

function fmtMoney(value) {
  return value === null || value === undefined ? "暂无数据" : `${fmtNumber(value, 4)} USDT`;
}

function fmtPct(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "暂无数据";
  return `${fmtNumber(value, digits)}%`;
}

function fmtFunding(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "暂无数据";
  return `${fmtNumber(Number(value) * 100, 4)}%`;
}

function fmtDate(value) {
  if (!value) return "暂无数据";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fmtEmpty(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function pill(text, state) {
  return `<span class="pill ${state}">${escapeHtml(text)}</span>`;
}

function statusPill(ok, unknownText = "未知") {
  if (ok === true) return pill("在线", "ok");
  if (ok === false) return pill("离线", "bad");
  return pill(unknownText, "warn");
}

function yesNoPill(value) {
  if (value === true) return pill("满足", "ok");
  if (value === false) return pill("不满足", "warn");
  return pill("未知", "warn");
}

function fmtRiskStatus(value) {
  const labels = {
    ok: "正常",
    blocked: "已阻止",
    attention: "需要注意",
  };
  return labels[value] || "未知";
}

function fmtReason(value) {
  const reasons = {
    futures_pair_missing: "未找到合约交易对",
    validation_failed: "市场验证未通过",
    not_started: "未启动",
  };
  return reasons[value] || fmtEmpty(value);
}

function fmtExchange(value) {
  const exchanges = {
    binance: "币安",
    okx: "OKX",
  };
  return exchanges[value] || fmtEmpty(value);
}

function fmtSide(value) {
  const sides = {
    short: "做空",
    long: "做多",
  };
  return sides[value] || fmtEmpty(value);
}

function fmtExitReason(value) {
  const reasons = {
    stale_trade_timeout: "持仓超时退出",
    kill_switch_exit: "紧急停止退出",
    stop_loss: "止损",
    stoploss: "止损",
    roi: "达到收益目标",
  };
  return reasons[value] || fmtEmpty(value);
}

function metric(label, value, tone = "") {
  return `<article class="metric ${tone}"><div class="label">${label}</div><div class="value">${value}</div></article>`;
}

function tradeSummary(trade) {
  if (!trade) return "暂无数据";
  return `${fmtEmpty(trade.pair)} / ${fmtMoney(trade.simulated_pnl)}`;
}

function renderOverview(data) {
  const overview = data.overview;
  const metrics = [
    ["机器人总数", overview.bot_count],
    ["在线机器人", overview.online_count],
    ["全部为模拟盘", fmtBool(overview.dry_run_all_online)],
    ["总模拟盈亏", fmtMoney(overview.total_simulated_pnl)],
    ["今日总模拟盈亏", fmtMoney(overview.today_total_pnl)],
    ["当前总持仓", overview.total_open_trades],
    ["今日平仓数", overview.total_closed_trades_today],
    ["最佳模拟交易", tradeSummary(overview.best_simulated_trade)],
    ["最差模拟交易", tradeSummary(overview.worst_simulated_trade)],
    ["最大回撤", overview.max_drawdown === null || overview.max_drawdown === undefined ? "暂无数据" : fmtNumber(overview.max_drawdown, 4)],
    ["触发风控", fmtBool(overview.any_risk_triggered)],
    ["机器人离线", fmtBool(overview.any_offline)],
  ];
  overviewEl.innerHTML = metrics.map(([label, value]) => metric(label, value)).join("");
  updatedEl.textContent = `更新于 ${new Date(overview.updated_at * 1000).toLocaleString("zh-CN", { hour12: false })}`;
}

function kv(label, value) {
  return `<div class="kv"><div class="name">${label}</div><div class="data">${value}</div></div>`;
}

function section(title, body, extraClass = "") {
  return `<section class="card-section ${extraClass}"><h3>${title}</h3>${body}</section>`;
}

function renderMarket(bot) {
  const market = bot.market || {};
  return section(
    "实时行情",
    `<div class="mini-grid">
      ${kv("当前价格", fmtPrice(market.current_price))}
      ${kv("24 小时涨跌", fmtPct(market.change_24h_pct))}
      ${kv("24 小时成交量", fmtNumber(market.volume_24h, 2))}
      ${kv("资金费率", fmtFunding(market.funding_rate))}
      ${kv("最近 K 线时间", fmtDate(market.last_candle_time))}
    </div>
    ${market.error ? `<div class="notice warn">行情读取提示：${fmtEmpty(market.error)}</div>` : ""}`,
  );
}

function renderStrategy(bot) {
  const indicators = bot.strategy_indicators || {};
  const decision = bot.strategy_decision || {};
  return section(
    "策略指标",
    `<div class="mini-grid">
      ${kv("EMA20", fmtNumber(indicators.ema20, 4))}
      ${kv("EMA50", fmtNumber(indicators.ema50, 4))}
      ${kv("RSI", fmtNumber(indicators.rsi, 2))}
      ${kv("20 根成交量均值", fmtNumber(indicators.volume_average, 2))}
      ${kv("满足做空入场", yesNoPill(decision.short_entry_met))}
      ${kv("满足退出条件", yesNoPill(decision.exit_met))}
    </div>`,
  );
}

function renderDecision(bot) {
  const decision = bot.strategy_decision || {};
  const title = decision.short_entry_met ? "为什么开仓" : "为什么不开仓";
  const blockers = decision.entry_blockers || [];
  const reasons = decision.entry_reasons || [];
  const exitReasons = decision.exit_reasons || [];
  return section(
    "策略判断",
    `<div class="decision">
      <div class="decision-title">${title}</div>
      <p>${fmtEmpty(decision.entry_explanation)}</p>
      <div class="tag-row">
        ${reasons.map((item) => pill(item, "ok")).join("")}
        ${blockers.map((item) => pill(item, "warn")).join("")}
      </div>
      <div class="decision-title">退出判断</div>
      <p>${fmtEmpty(decision.exit_explanation)}</p>
      <div class="tag-row">${exitReasons.length ? exitReasons.map((item) => pill(item, "warn")).join("") : pill("暂无退出信号", "ok")}</div>
    </div>`,
  );
}

function renderTrades(bot) {
  const trades = bot.simulated_trades || [];
  if (!trades.length) {
    return section("模拟交易记录", `<div class="empty small">暂无模拟交易记录</div>`);
  }
  const rows = trades
    .map(
      (trade) => `
        <tr>
          <td>${fmtDate(trade.open_time)}</td>
          <td>${fmtDate(trade.close_time)}</td>
          <td>${fmtSide(trade.side)}</td>
          <td>${fmtPrice(trade.entry_price)}</td>
          <td>${fmtPrice(trade.exit_price)}</td>
          <td>${fmtMoney(trade.simulated_pnl)}</td>
          <td>${fmtExitReason(trade.exit_reason)}</td>
        </tr>
      `,
    )
    .join("");
  return section(
    "模拟交易记录",
    `<div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>开仓时间</th>
            <th>平仓时间</th>
            <th>方向</th>
            <th>开仓价</th>
            <th>平仓价</th>
            <th>模拟盈亏</th>
            <th>退出原因</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`,
  );
}

function renderRisk(bot) {
  const risk = bot.risk || {};
  const riskState = risk.risk_status === "ok" ? "ok" : risk.risk_status === "blocked" ? "bad" : "warn";
  return section(
    "风控详情",
    `<div class="mini-grid">
      ${kv("最大杠杆", `${fmtNumber(risk.max_leverage, 0)}x`)}
      ${kv("最大仓位", `${fmtNumber(risk.max_position_size_pct, 0)}%`)}
      ${kv("日亏损上限", `${fmtNumber(risk.daily_loss_limit_pct, 0)}%`)}
      ${kv("当前日模拟亏损", fmtMoney(risk.current_daily_simulated_loss))}
      ${kv("连续亏损", `${risk.consecutive_losses ?? 0} / ${risk.consecutive_loss_limit ?? 3}`)}
      ${kv("紧急停止", risk.kill_switch_active ? pill("已启用", "bad") : pill("未启用", "ok"))}
      ${kv("风控状态", pill(fmtRiskStatus(risk.risk_status), riskState))}
    </div>`,
  );
}

function renderXaut(bot) {
  if (bot.key !== "xaut") return "";
  const validation = bot.xaut_validation || {};
  const xautMarket = bot.xaut_market || {};
  return section(
    "XAUT 验证与价差监控占位",
    `<div class="mini-grid">
      ${kv("合约验证", validation.futures_exists ? pill("通过", "ok") : pill("未通过", "warn"))}
      ${kv("机器人已启动", fmtBool(bot.xaut_started))}
      ${kv("交易所模板", fmtExchange(validation.exchange))}
      ${kv("未启动原因", fmtReason(bot.xaut_not_started_reason || validation.reason))}
      ${kv("币安 XAUT 价格", fmtPrice(xautMarket.binance_price))}
      ${kv("OKX XAUT 价格", fmtPrice(xautMarket.okx_price))}
      ${kv("价差百分比", xautMarket.spread_pct === null || xautMarket.spread_pct === undefined ? "待价差监控使用" : fmtPct(xautMarket.spread_pct, 4))}
    </div>
    ${xautMarket.error ? `<div class="notice warn">XAUT 价格读取提示：${fmtEmpty(xautMarket.error)}</div>` : ""}`,
  );
}

function renderBot(bot) {
  const riskState = bot.risk_status === "ok" ? "ok" : bot.risk_status === "blocked" ? "bad" : "warn";
  return `
    <article class="card">
      <div class="card-head">
        <div class="asset">
          <div class="symbol">${escapeHtml(bot.label.slice(0, 2))}</div>
          <div>
            <h2>${escapeHtml(bot.label)}</h2>
            <div class="pair">${fmtEmpty(bot.pair)} · 本地界面 127.0.0.1:${bot.local_port}</div>
          </div>
        </div>
        <div class="status-stack">
          ${statusPill(bot.online)}
          ${bot.dry_run ? pill("模拟盘", "ok") : pill("非模拟盘", "bad")}
          ${pill(fmtRiskStatus(bot.risk_status), riskState)}
        </div>
      </div>
      <div class="section-grid">
        ${renderMarket(bot)}
        ${renderStrategy(bot)}
        ${renderDecision(bot)}
        ${renderRisk(bot)}
        ${renderXaut(bot)}
        ${renderTrades(bot)}
      </div>
      ${bot.recent_error ? `<div class="notice bad">最近错误：${fmtEmpty(bot.recent_error)}</div>` : ""}
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
    updatedEl.textContent = "仪表盘接口不可用";
    overviewEl.innerHTML = "";
    gridEl.innerHTML = `<div class="empty">无法加载仪表盘数据：${escapeHtml(error.message)}</div>`;
  }
}

loadSummary();
setInterval(loadSummary, 15000);
