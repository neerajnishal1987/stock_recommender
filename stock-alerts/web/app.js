/* StockAlerts – dashboard logic.
   Fetches instruments, latest market data & alerts from Supabase REST API.
   Applies country / asset / category / commodity / crypto filters client-side. */
(() => {
    "use strict";

    // Supabase direct-read config (used when NOT running via local serve.py)
    const SUPABASE_URL = (typeof STOCKALERTS_SUPABASE_URL !== "undefined")
        ? STOCKALERTS_SUPABASE_URL : "";
    const SUPABASE_ANON = (typeof STOCKALERTS_SUPABASE_ANON_KEY !== "undefined")
        ? STOCKALERTS_SUPABASE_ANON_KEY : "";
    const IS_LOCAL = (location.hostname === "localhost" || location.hostname === "127.0.0.1");

    const $ = (id) => document.getElementById(id);

    const statusBadge = $("statusBadge");
    const countryFilter = $("countryFilter");
    const assetFilter = $("assetFilter");
    const stockCapFilter = $("stockCapFilter");
    const categoryFilter = $("categoryFilter");
    const commodityFilter = $("commodityFilter");
    const cryptoFilter = $("cryptoFilter");
    const applyBtn = $("applyFiltersBtn");
    const marketBody = $("marketBody");
    const resultCount = $("resultCount");
    const alertsList = $("alertsList");

    // ---------- State ----------
    let instruments = [];
    let marketData = [];
    let latestByInstrument = {};
    let alerts = [];

    // ---------- Data fetch: local API (serve.py) OR direct Supabase REST ----------
    async function supabaseFetch(path) {
        const url = `${SUPABASE_URL}/rest/v1/${path}`;
        const resp = await fetch(url, {
            headers: {
                "apikey": SUPABASE_ANON,
                "Authorization": `Bearer ${SUPABASE_ANON}`,
            },
        });
        if (!resp.ok) throw new Error(`Supabase error ${resp.status}`);
        return resp.json();
    }

    async function apiFetch(path) {
        const resp = await fetch(path);
        if (!resp.ok) throw new Error(`API error ${resp.status}`);
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error || "API error");
        return data;
    }

    async function loadData() {
        if (IS_LOCAL) {
            // Local dev server (serve.py) proxies Supabase
            const [inst, mdata, alertRows] = await Promise.all([
                apiFetch("/api/instruments"),
                apiFetch("/api/market_data"),
                apiFetch("/api/alerts"),
            ]);
            return [inst.data || [], mdata.data || [], alertRows.data || []];
        }
        // Static hosting: read Supabase directly via anon key
        if (!SUPABASE_URL || SUPABASE_URL.includes("YOUR_SUPABASE")) {
            throw new Error("Supabase not configured in config.js");
        }
        const [inst, mdata, alertRows] = await Promise.all([
            supabaseFetch("instruments?select=*&is_active=eq.true"),
            supabaseFetch("market_data?select=*&order=as_of.desc&limit=500"),
            supabaseFetch("alerts?select=*&order=detected_at.desc&limit=20"),
        ]);
        return [inst || [], mdata || [], alertRows || []];
    }

    // ---------- Init ----------
    async function init() {
        try {
            setStatus("Loading data…", "neutral");
            const [inst, mdata, alertRows] = await loadData();
            instruments = inst;
            marketData = mdata;
            alerts = alertRows;
            buildLatestMap();
            setStatus("Connected ✓", "good");
            applyFilters();
            renderAlerts();
        } catch (e) {
            console.error(e);
            setStatus("Connection failed", "error");
            renderConfigMessage();
        }
    }

    function renderConfigMessage() {
        if (IS_LOCAL) {
            marketBody.innerHTML = `<tr><td colspan="10" class="empty">Could not reach the local API. Start the Flask server (<code>python3 serve.py</code>) and ensure Supabase is configured in <code>.env</code>.</td></tr>`;
        } else {
            marketBody.innerHTML = `<tr><td colspan="10" class="empty">Set your Supabase URL & anon key in <code>config.js</code> to load market data.</td></tr>`;
        }
    }

    function setStatus(text, cls) {
        statusBadge.textContent = text;
        statusBadge.className = "status-badge " + cls;
    }

    // Newest market_data row per instrument
    function buildLatestMap() {
        latestByInstrument = {};
        for (const row of marketData) {
            const rid = row.instrument_id;
            if (!latestByInstrument[rid] || (row.as_of || "") > (latestByInstrument[rid].as_of || "")) {
                latestByInstrument[rid] = row;
            }
        }
    }

    // ---------- Filter UI visibility ----------
    function updateFilterVisibility() {
        const type = assetFilter.value;
        $("stockCapGroup").classList.toggle("hidden", type !== "stock");
        // MF & ETF share category options (show for both)
        $("mfEtfGroup").classList.toggle("hidden", !(type === "mutual_fund" || type === "etf"));
        $("commodityGroup").classList.toggle("hidden", type !== "commodity");
        $("cryptoGroup").classList.toggle("hidden", type !== "crypto");
    }

    assetFilter.addEventListener("change", updateFilterVisibility);

    // ---------- Filtering ----------
    function applyFilters() {
        const country = countryFilter.value;
        const type = assetFilter.value;
        const cap = stockCapFilter.value;
        const cat = categoryFilter.value;
        const comm = commodityFilter.value;
        const crypt = cryptoFilter.value;

        let rows = instruments.map((inst) => {
            const md = latestByInstrument[inst.id] || {};
            return { ...inst, md };
        });

        if (country !== "all") rows = rows.filter((r) => r.country === country);
        if (type !== "all") rows = rows.filter((r) => r.asset_type === type);

        if (type === "stock" && cap !== "all") {
            rows = rows.filter((r) => r.category === cap);
        }
        if ((type === "mutual_fund" || type === "etf") && cat !== "all") {
            rows = rows.filter((r) => r.category === cat);
        }
        if (type === "commodity" && comm !== "all") {
            rows = rows.filter((r) => r.category === comm);
        }
        if (type === "crypto" && crypt !== "all") {
            rows = rows.filter((r) => r.category === crypt);
        }

        // Sort by % off high (biggest drop first)
        rows.sort((a, b) => (b.md.moved_off_high || b.md.off_high || 0) - (a.md.moved_off_high || a.md.off_high || 0));
        renderMarket(rows);
    }

    function fmtNum(v, digits = 2) {
        if (v === null || v === undefined || isNaN(Number(v))) return "—";
        return Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits });
    }

    function offHigh(inst) {
        const price = inst.md.price;
        const high = inst.md.day_high;
        if (!price || !high || Number(high) <= 0) return null;
        return ((Number(high) - Number(price)) / Number(high)) * 100;
    }

    function renderMarket(rows) {
        resultCount.textContent = `${rows.length} assets`;
        if (!rows.length) {
            marketBody.innerHTML = `<tr><td colspan="10" class="empty">No assets match the selected filters.</td></tr>`;
            return;
        }
        marketBody.innerHTML = rows.map((r) => {
            const off = offHigh(r);
            const changePct = r.md.change_pct;
            const offCls = off !== null && off >= 5 ? "neg" : (off !== null ? "warn" : "");
            const changeCls = changePct !== null && changePct < 0 ? "neg" : (changePct !== null ? "pos" : "");
            return `<tr>
                <td><strong>${escapeHtml(r.name)}</strong></td>
                <td>${escapeHtml(r.symbol)}</td>
                <td>${labelType(r.asset_type)}</td>
                <td>${r.country}</td>
                <td>${escapeHtml(r.category || "—")}</td>
                <td>${fmtNum(r.md.price)}</td>
                <td>${fmtNum(r.md.day_high)}</td>
                <td>${fmtNum(r.md.day_low)}</td>
                <td class="${offCls}">${off !== null ? off.toFixed(2) + "%" : "—"}</td>
                <td class="${changeCls}">${changePct !== null ? changePct.toFixed(2) + "%" : "—"}</td>
            </tr>`;
        }).join("");
    }

    function renderAlerts() {
        if (!alerts.length) {
            alertsList.innerHTML = `<p class="muted">No drop alerts yet.</p>`;
            return;
        }
        alertsList.innerHTML = alerts.map((a) => {
            const inst = instruments.find((i) => i.id === a.instrument_id);
            const name = inst ? inst.name : "Unknown";
            const sym = inst ? inst.symbol : "";
            const summary = (a.groq_analysis || "No analysis available")
                .split("\n").filter((l) => l.trim()).slice(0, 6).join(" | ");
            return `<div class="alert-item ${a.status === 'email_sent' ? 'emailed' : ''}">
                <div class="alert-head">
                    <strong>${escapeHtml(name)} (${escapeHtml(sym)})</strong>
                    <span class="badge negative">-${Number(a.drop_pct).toFixed(2)}%</span>
                    <span class="alert-status">${a.status === 'email_sent' ? '📧 emailed' : 'new'}</span>
                </div>
                <p class="alert-time">${fmtDate(a.detected_at)}</p>
                <p class="alert-analysis">${escapeHtml(summary)}</p>
            </div>`;
        }).join("");
    }

    function fmtDate(iso) {
        if (!iso) return "";
        try {
            const d = new Date(iso);
            return d.toLocaleString();
        } catch (e) {
            return iso;
        }
    }

    function labelType(t) {
        const map = {
            stock: "Stock",
            mutual_fund: "Mutual Fund",
            etf: "ETF",
            commodity: "Commodity",
            crypto: "Crypto",
        };
        return map[t] || t;
    }

    function escapeHtml(s) {
        if (!s) return "";
        const a = String.fromCharCode(38); // &
        const lt = String.fromCharCode(60); // <
        const gt = String.fromCharCode(62); // >
        const qt = String.fromCharCode(34); // "
        const ap = String.fromCharCode(39); // '
        const map = {};
        map[a] = a + "amp;";
        map[lt] = lt + "t;";
        map[gt] = gt + "t;";
        map[qt] = qt + "quot;";
        map[ap] = ap + "#39;";
        return String(s).replace(/[&<>"']/g, (c) => map[c]);
    }

    // ---------- Events ----------
    applyBtn.addEventListener("click", () => {
        applyFilters();
        renderAlerts();
    });

    // ---------- Start ----------
    updateFilterVisibility();
    init();
})();