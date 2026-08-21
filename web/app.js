const API = (window.CONFIG && window.CONFIG.API_BASE) || "http://localhost:8000";
const CURRENCY = (window.CONFIG && window.CONFIG.CURRENCY) || "SAR";
const API_KEY = (window.CONFIG && window.CONFIG.API_KEY) || "";

const state = {
  categories: [],       // [{id,type,category,subcategory}]
  budget: [],           // [{id,type,category,subcategory,monthly_amount}]
  catMap: {},            // category -> [subcategories]
  catType: {},            // category -> type
  currentTab: "dashboard",
  currentMonth: new Date().getMonth() + 1,
  year: new Date().getFullYear(),
  detailType: "income",
};

function fmt(n) {
  const v = Number(n || 0);
  return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " " + CURRENCY;
}
function fmtInt(n) {
  return Math.round(Number(n || 0)).toLocaleString() + " " + CURRENCY;
}
function pct(n) {
  return (Number(n || 0) * 100).toFixed(1) + "%";
}

async function api(path, opts = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  if (API_KEY && opts.method && opts.method !== "GET") headers["X-API-Key"] = API_KEY;
  const res = await fetch(API + path, Object.assign({}, opts, { headers }));
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------------- bootstrap ----------------
async function loadCatalog() {
  const [cats, budget] = await Promise.all([api("/api/categories"), api("/api/budget")]);
  state.categories = cats;
  state.budget = budget;
  state.catMap = {};
  state.catType = {};
  for (const c of cats) {
    state.catMap[c.category] = state.catMap[c.category] || [];
    state.catMap[c.category].push(c.subcategory);
    state.catType[c.category] = c.type;
  }
}

// ---------------- tabs ----------------
document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  btn.classList.add("active");
  state.currentTab = btn.dataset.tab;
  render();
});

// ---------------- quick add (agent) ----------------
document.getElementById("quickadd-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("quickadd-input");
  const feedback = document.getElementById("quickadd-feedback");
  const text = input.value.trim();
  if (!text) return;
  feedback.textContent = "Thinking…";
  feedback.className = "quickadd-feedback";
  try {
    const res = await api("/api/agent/log", {
      method: "POST",
      body: JSON.stringify({ text, source: "web", created_by: "web-ui" }),
    });
    feedback.textContent = "✅ " + res.reply;
    feedback.className = "quickadd-feedback ok";
    input.value = "";
    await loadCatalog();
    render();
  } catch (err) {
    feedback.textContent = "❓ " + err.message;
    feedback.className = "quickadd-feedback error";
  }
});

// ---------------- render dispatch ----------------
async function render() {
  const view = document.getElementById("view");
  view.innerHTML = "";
  if (state.currentTab === "dashboard") return renderDashboard(view);
  if (state.currentTab === "monthly") return renderMonthly(view);
  if (state.currentTab === "transactions") return renderTransactions(view);
  if (state.currentTab === "budget") return renderBudget(view);
}

// ---------------- dashboard ----------------
let trendChart, catChart;

async function renderDashboard(view) {
  const tpl = document.getElementById("tpl-dashboard").content.cloneNode(true);
  view.appendChild(tpl);
  document.getElementById("kpi-income").textContent = "…";

  const [trend, cats] = await Promise.all([
    api(`/api/summary/monthly?year=${state.year}`),
    api(`/api/summary/categories?year=${state.year}`),
  ]);

  const ytdIncome = trend.reduce((a, m) => a + m.income, 0);
  const ytdExpense = trend.reduce((a, m) => a + m.expense, 0);
  const ytdSavings = trend.reduce((a, m) => a + m.savings, 0);
  document.getElementById("kpi-income").textContent = fmtInt(ytdIncome);
  document.getElementById("kpi-expense").textContent = fmtInt(ytdExpense);
  document.getElementById("kpi-savings").textContent = fmtInt(ytdSavings);
  document.getElementById("kpi-net").textContent = fmtInt(ytdIncome - ytdExpense - ytdSavings);

  const ctx = document.getElementById("chart-trend");
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: trend.map((m) => m.month_name.slice(0, 3)),
      datasets: [
        { label: "Income", data: trend.map((m) => m.income), backgroundColor: "#0E7C6B" },
        { label: "Expenses", data: trend.map((m) => m.expense), backgroundColor: "#B83B3B" },
        { label: "Savings", data: trend.map((m) => m.savings), backgroundColor: "#B8863B" },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "bottom", labels: { font: { family: "system-ui" } } } },
      scales: { y: { ticks: { callback: (v) => v.toLocaleString() } } },
    },
  });

  const catCtx = document.getElementById("chart-categories");
  if (catChart) catChart.destroy();
  const palette = ["#16233F", "#0E7C6B", "#B8863B", "#B83B3B", "#33456B", "#6B7280", "#8AA6C2", "#D8B26A", "#7FB8AB", "#C97B7B", "#9AA5B1", "#E4C87A"];
  catChart = new Chart(catCtx, {
    type: "doughnut",
    data: {
      labels: cats.map((c) => c.category),
      datasets: [{ data: cats.map((c) => c.ytd_actual), backgroundColor: palette }],
    },
    options: { plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } } },
  });

  const tableHtml = `
    <table>
      <thead><tr><th>Category</th><th class="num">YTD Actual</th><th class="num">% of expenses</th></tr></thead>
      <tbody>
        ${cats.map((c) => `<tr><td>${c.category}</td><td class="num">${fmtInt(c.ytd_actual)}</td><td class="num">${pct(c.pct_of_total)}</td></tr>`).join("") || `<tr><td colspan="3" class="empty">No expenses logged yet.</td></tr>`}
      </tbody>
    </table>`;
  document.getElementById("category-table").innerHTML = tableHtml;
}

// ---------------- monthly ----------------
async function renderMonthly(view) {
  const tpl = document.getElementById("tpl-monthly").content.cloneNode(true);
  view.appendChild(tpl);

  const select = document.getElementById("month-select");
  const months = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  select.innerHTML = months.map((m, i) => `<option value="${i + 1}" ${i + 1 === state.currentMonth ? "selected" : ""}>${m} ${state.year}</option>`).join("");
  select.addEventListener("change", () => { state.currentMonth = Number(select.value); loadMonthDetail(); });

  document.getElementById("detail-tabs").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    state.detailType = chip.dataset.type;
    loadMonthDetail(true);
  });

  await loadMonthDetail();
}

async function loadMonthDetail(skipFetch) {
  const data = state._monthCache && skipFetch
    ? state._monthCache
    : await api(`/api/summary/month/${state.year}/${state.currentMonth}`);
  state._monthCache = data;
  const t = data.totals;

  document.getElementById("m-income").innerHTML = `${fmtInt(t.income_actual)} <span class="muted mono" style="font-size:12px">/ ${fmtInt(t.income_projected)}</span>`;
  document.getElementById("m-expense").innerHTML = `${fmtInt(t.expense_actual)} <span class="muted mono" style="font-size:12px">/ ${fmtInt(t.expense_projected)}</span>`;
  document.getElementById("m-savings").innerHTML = `${fmtInt(t.savings_actual)} <span class="muted mono" style="font-size:12px">/ ${fmtInt(t.savings_projected)}</span>`;
  document.getElementById("m-net").textContent = fmtInt(t.net_actual);

  const lines = data[state.detailType] || [];
  const grouped = {};
  for (const l of lines) {
    grouped[l.category] = grouped[l.category] || [];
    grouped[l.category].push(l);
  }
  let rows = "";
  let totP = 0, totA = 0;
  for (const [cat, items] of Object.entries(grouped)) {
    if (Object.keys(grouped).length > 1) rows += `<tr class="group-row"><td colspan="4">${cat}</td></tr>`;
    for (const l of items) {
      totP += l.projected; totA += l.actual;
      const diffClass = l.difference < 0 ? "neg" : "pos";
      rows += `<tr><td>${Object.keys(grouped).length > 1 ? "" : cat}</td><td>${l.subcategory}</td>
        <td class="num">${fmtInt(l.projected)}</td><td class="num">${fmtInt(l.actual)}</td>
        <td class="num ${diffClass}">${fmtInt(l.difference)}</td></tr>`;
    }
  }
  document.getElementById("detail-table").innerHTML = `
    <table>
      <thead><tr><th>Category</th><th>Subcategory</th><th class="num">Projected</th><th class="num">Actual</th><th class="num">Difference</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="5" class="empty">Nothing here yet.</td></tr>`}</tbody>
      <tfoot><tr class="total-row"><td colspan="2">Total</td><td class="num">${fmtInt(totP)}</td><td class="num">${fmtInt(totA)}</td><td class="num">${fmtInt(totP - totA)}</td></tr></tfoot>
    </table>`;
}

// ---------------- transactions ----------------
async function renderTransactions(view) {
  const tpl = document.getElementById("tpl-transactions").content.cloneNode(true);
  view.appendChild(tpl);
  view.querySelectorAll(".cur").forEach((el) => (el.textContent = CURRENCY));

  const form = document.getElementById("txn-form");
  const catSelect = form.querySelector("[name=category]");
  const subSelect = form.querySelector("[name=subcategory]");
  const typeSelect = form.querySelector("[name=type]");
  const pmSelect = form.querySelector("[name=payment_method]");
  form.querySelector("[name=date]").value = new Date().toISOString().slice(0, 10);

  ["Cash","Debit Card","Credit Card","Bank Transfer","Mada","Apple Pay","Other"].forEach((pm) => {
    const o = document.createElement("option"); o.value = pm; o.textContent = pm; pmSelect.appendChild(o);
  });

  function categoriesForType(type) {
    return [...new Set(state.categories.filter((c) => c.type === type).map((c) => c.category))];
  }
  function refreshCategoryOptions() {
    const cats = categoriesForType(typeSelect.value);
    catSelect.innerHTML = cats.map((c) => `<option value="${c}">${c}</option>`).join("");
    refreshSubcategoryOptions();
  }
  function refreshSubcategoryOptions() {
    const subs = state.catMap[catSelect.value] || [];
    subSelect.innerHTML = subs.map((s) => `<option value="${s}">${s}</option>`).join("");
  }
  typeSelect.addEventListener("change", refreshCategoryOptions);
  catSelect.addEventListener("change", refreshSubcategoryOptions);
  refreshCategoryOptions();

  const filterSelect = document.getElementById("txn-filter");
  const allCats = [...new Set(state.categories.map((c) => c.category))];
  filterSelect.innerHTML = `<option value="">All</option>` + allCats.map((c) => `<option value="${c}">${c}</option>`).join("");
  filterSelect.addEventListener("change", () => loadTransactions(filterSelect.value));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const body = Object.fromEntries(fd.entries());
    body.amount = Number(body.amount);
    body.source = "web"; body.created_by = "web-ui";
    try {
      await api("/api/transactions", { method: "POST", body: JSON.stringify(body) });
      form.reset();
      form.querySelector("[name=date]").value = new Date().toISOString().slice(0, 10);
      refreshCategoryOptions();
      await loadTransactions(filterSelect.value);
    } catch (err) {
      alert("Couldn't add transaction: " + err.message);
    }
  });

  await loadTransactions("");
}

async function loadTransactions(category) {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  const rows = await api(`/api/transactions${qs}`);
  const html = `
    <table>
      <thead><tr><th>Date</th><th>Type</th><th>Category</th><th>Subcategory</th><th class="num">Amount</th><th>Via</th><th></th></tr></thead>
      <tbody>
        ${rows.map((r) => `
          <tr>
            <td class="mono">${r.date}</td>
            <td><span class="pill ${r.type.toLowerCase()}">${r.type}</span></td>
            <td>${r.category}</td>
            <td>${r.subcategory}</td>
            <td class="num">${fmt(r.amount)}</td>
            <td class="muted">${r.source}</td>
            <td><button class="del-btn" data-id="${r.id}">Delete</button></td>
          </tr>`).join("") || `<tr><td colspan="7" class="empty">No transactions yet — add one above, or use the quick-add bar.</td></tr>`}
      </tbody>
    </table>`;
  const container = document.getElementById("txn-table");
  container.innerHTML = html;
  container.querySelectorAll(".del-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this transaction?")) return;
      await api(`/api/transactions/${btn.dataset.id}`, { method: "DELETE" });
      await loadTransactions(category);
    });
  });
}

// ---------------- budget ----------------
async function renderBudget(view) {
  const tpl = document.getElementById("tpl-budget").content.cloneNode(true);
  view.appendChild(tpl);

  const grouped = {};
  for (const b of state.budget) {
    grouped[b.category] = grouped[b.category] || [];
    grouped[b.category].push(b);
  }
  let rows = "";
  for (const [cat, items] of Object.entries(grouped)) {
    rows += `<tr class="group-row"><td colspan="3">${cat}</td></tr>`;
    for (const b of items) {
      rows += `<tr>
        <td></td><td>${b.subcategory}</td>
        <td class="num"><input type="number" class="budget-input" data-id="${b.id}" min="0" step="1" value="${Number(b.monthly_amount).toFixed(0)}" /></td>
      </tr>`;
    }
  }
  document.getElementById("budget-table").innerHTML = `
    <table>
      <thead><tr><th>Category</th><th>Subcategory</th><th class="num">Monthly target (${CURRENCY})</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

  document.querySelectorAll(".budget-input").forEach((inp) => {
    inp.addEventListener("change", async () => {
      try {
        await api(`/api/budget/${inp.dataset.id}`, { method: "PUT", body: JSON.stringify({ monthly_amount: Number(inp.value) }) });
        inp.style.borderColor = "#0E7C6B";
        setTimeout(() => (inp.style.borderColor = ""), 800);
        await loadCatalog();
      } catch (err) {
        alert("Couldn't save: " + err.message);
      }
    });
  });
}

// ---------------- boot ----------------
(async function boot() {
  document.getElementById("year-badge").textContent = state.year;
  try {
    await loadCatalog();
    render();
  } catch (err) {
    document.getElementById("view").innerHTML = `<div class="card"><p class="empty">Couldn't reach the API at ${API}. ${err.message}</p></div>`;
  }
})();
