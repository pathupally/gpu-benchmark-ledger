(() => {
  "use strict";

  const data = window.BENCHMARK_LEDGER_DATA;
  if (!data) {
    document.body.innerHTML = '<main class="noscript"><h1>Analysis data is missing.</h1><p>Run <code>make build</code>, then reload this page.</p></main>';
    return;
  }

  const dimensionLabels = {
    gpu_model: "GPU model",
    memory_gb: "Memory",
    form_factor: "Form factor",
    tier: "Provider tier",
    region: "Region",
    rental_type: "Rental type",
    observation_window: "Observation window",
    contributor_coverage: "Contributors"
  };

  const eventLabels = {
    acknowledged_jump: "Acknowledged coverage jump",
    methodology_change: "Methodology change",
    new_index: "New index",
    provider_change: "Provider change",
    audit_status: "Audit status"
  };

  const methodLabels = {
    effective_from: "Effective from",
    price_input: "Price input",
    aggregation: "Aggregation",
    observation_window: "Window",
    rental_type: "Rental type",
    provider_weighting: "Provider weighting",
    dated_break_register: "Dated break register"
  };

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const titleCase = (value) => String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());

  const formatMoney = (value) => `$${Number(value).toFixed(2)}`;
  const formatSigned = (value, digits = 1) => {
    const numeric = Number(value);
    const prefix = numeric > 0 ? "+" : numeric < 0 ? "−" : "";
    return `${prefix}${Math.abs(numeric).toFixed(digits)}%`;
  };
  const display = (value) => value === null || value === undefined || value === ""
    ? "Not disclosed"
    : titleCase(value);

  document.getElementById("asOfDate").textContent = `As of ${data.meta.generated_on}`;
  document.getElementById("matchedCount").textContent = data.headline.matched_cells;
  document.getElementById("eligibleCount").textContent = data.headline.decision_eligible_cells;

  function renderBasisChart() {
    const container = document.getElementById("basisChart");
    const rows = data.pairs;
    const width = 920;
    const marginLeft = 100;
    const marginRight = 70;
    const chartWidth = width - marginLeft - marginRight;
    const rowHeight = 74;
    const top = 48;
    const height = top + rows.length * rowHeight + 24;
    const min = -35;
    const max = 45;
    const ticks = [-30, -20, -10, 0, 10, 20, 30, 40];
    const x = value => marginLeft + ((Math.max(min, Math.min(max, value)) - min) / (max - min)) * chartWidth;

    const grid = ticks.map(tick => `
      <line class="${tick === 0 ? "zero-line" : "grid-line"}" x1="${x(tick)}" y1="30" x2="${x(tick)}" y2="${height - 16}" />
      <text class="axis-label" x="${x(tick)}" y="17" text-anchor="middle">${tick > 0 ? "+" : ""}${tick}%</text>
    `).join("");

    const marks = rows.map((row, index) => {
      const y = top + index * rowHeight + rowHeight / 2;
      const raw = row.basis.raw_pct;
      const sensitivity = row.basis.break_sensitivity;
      const low = sensitivity.adjusted_pct_low;
      const high = sensitivity.adjusted_pct_high;
      const dotClass = row.comparison_class === "approximate" ? "approx-dot" : "raw-dot";
      const unbounded = sensitivity.is_fully_bounded ? "" : `
        <path class="unbounded-flag" d="M ${marginLeft - 16} ${y} l 8 -6 v 12 z">
          <title>An earlier published break is unquantified; this band is not a complete bound.</title>
        </path>`;
      return `
        <g>
          <title>${escapeHtml(row.gpu_model)}: raw basis ${formatSigned(raw)}; adjusted ${formatSigned(low)} to ${formatSigned(high)}</title>
          <text class="row-label" x="0" y="${y + 5}">${escapeHtml(row.gpu_model)}</text>
          <line class="row-rule" x1="${marginLeft}" y1="${y}" x2="${width - marginRight}" y2="${y}" />
          ${Math.abs(high - low) > 0.01 ? `
            <line class="band" x1="${x(low)}" y1="${y}" x2="${x(high)}" y2="${y}" />
            <line class="band-cap" x1="${x(low)}" y1="${y - 8}" x2="${x(low)}" y2="${y + 8}" />
            <line class="band-cap" x1="${x(high)}" y1="${y - 8}" x2="${x(high)}" y2="${y + 8}" />` : ""}
          <circle class="${dotClass}" cx="${x(raw)}" cy="${y}" r="8" />
          ${unbounded}
          <text class="row-value" x="${width - marginRight + 12}" y="${y + 5}">${formatSigned(raw)}</text>
        </g>`;
    }).join("");

    container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">${grid}${marks}</svg>`;
    const summary = rows.map(row => `${row.gpu_model} ${formatSigned(row.basis.raw_pct)}`).join(", ");
    container.setAttribute("aria-label", `Ornn basis relative to Silicon Data: ${summary}.`);
  }

  let selectedIndex = Math.max(0, data.pairs.findIndex(pair => pair.gpu_model === "H100"));

  function sensitivityCopy(pair) {
    const sensitivity = pair.basis.break_sensitivity;
    const band = `${formatSigned(sensitivity.adjusted_pct_low)} to ${formatSigned(sensitivity.adjusted_pct_high)}`;
    if (sensitivity.status === "quantified") {
      return `<strong>Published break sensitivity: ${band}</strong>Fully bounded by the quantified non-restated event${sensitivity.applied_breaks.length === 1 ? "" : "s"} in the ledger.`;
    }
    if (sensitivity.status === "partial_unbounded") {
      return `<strong>Quantified range: ${band}</strong>An earlier coverage jump is unquantified, so this is a partial sensitivity range—not a complete bound.`;
    }
    if (sensitivity.status === "unbounded") {
      return `<strong>No numerical band is defensible.</strong>The public register acknowledges a non-restated jump but does not quantify its impact.`;
    }
    return `<strong>No applicable quantified break.</strong>The raw basis is shown without a numerical adjustment.`;
  }

  function renderPairDetail() {
    const pair = data.pairs[selectedIndex];
    const basisClass = pair.basis.raw_pct >= 0 ? "positive" : "negative";
    const eligibilityClass = pair.analysis_eligible ? "eligible" : "diagnostic";
    const eligibilityLabel = pair.analysis_eligible ? "Decision eligible" : "Diagnostic only";
    document.getElementById("pairDetail").innerHTML = `
      <article class="pair-detail" role="tabpanel" aria-labelledby="gpu-tab-${selectedIndex}">
        <div class="pair-detail-head">
          <div>
            <h3>${escapeHtml(pair.gpu_model)}</h3>
            <div class="pair-badges">
              <span class="badge">${escapeHtml(pair.comparison_class)} match</span>
              <span class="badge ${eligibilityClass}">${eligibilityLabel}</span>
            </div>
          </div>
          <span class="confidence-seal" aria-label="Confidence grade ${pair.confidence_grade}">${pair.confidence_grade}</span>
        </div>
        <div class="price-ledger">
          <div><p class="vendor-label">Ornn</p><p class="price-value">${formatMoney(pair.ornn.value)}</p></div>
          <span class="versus">vs.</span>
          <div><p class="vendor-label">Silicon Data</p><p class="price-value">${formatMoney(pair.silicon_data.value)}</p></div>
        </div>
        <div class="basis-readout">
          <div><p class="label">Raw basis</p><strong class="${basisClass}">${formatSigned(pair.basis.raw_pct)}</strong></div>
          <div><p class="label">Log basis</p><strong>${pair.basis.raw_log.toFixed(4)}</strong></div>
        </div>
        <p class="sensitivity-note">${sensitivityCopy(pair)}</p>
        <p class="pair-rationale">${escapeHtml(pair.rationale)}</p>
        <p class="source-line"><span>Source records</span>${escapeHtml(pair.ornn.source_id)}<br>${escapeHtml(pair.silicon_data.source_id)}</p>
      </article>`;
  }

  function selectGpu(index, focus = false) {
    selectedIndex = index;
    const tabs = [...document.querySelectorAll(".gpu-tab")];
    tabs.forEach((tab, tabIndex) => {
      const selected = tabIndex === selectedIndex;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    if (focus) tabs[selectedIndex].focus();
    renderPairDetail();
  }

  function renderGpuTabs() {
    const tabs = document.getElementById("gpuTabs");
    tabs.innerHTML = data.pairs.map((pair, index) => `
      <button id="gpu-tab-${index}" class="gpu-tab" type="button" role="tab" aria-selected="${index === selectedIndex}" tabindex="${index === selectedIndex ? 0 : -1}" data-index="${index}">${escapeHtml(pair.gpu_model)}</button>
    `).join("");
    tabs.addEventListener("click", event => {
      const button = event.target.closest(".gpu-tab");
      if (button) selectGpu(Number(button.dataset.index));
    });
    tabs.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let next = selectedIndex;
      if (event.key === "ArrowLeft") next = (selectedIndex - 1 + data.pairs.length) % data.pairs.length;
      if (event.key === "ArrowRight") next = (selectedIndex + 1) % data.pairs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = data.pairs.length - 1;
      selectGpu(next, true);
    });
  }

  function renderEstimateGates() {
    const correlation = data.analytics.correlation;
    const hedge = data.analytics.rolling_hedge_ratio;
    const correlationPct = Math.min(100, correlation.observed_shared_levels / correlation.levels_required * 100);
    const hedgePct = Math.min(100, hedge.observed_shared_levels / hedge.levels_required * 100);
    document.getElementById("correlationProgress").style.width = `${correlationPct}%`;
    document.getElementById("hedgeProgress").style.width = `${hedgePct}%`;
    document.getElementById("correlationReason").textContent = `${correlation.observed_shared_levels} of ${correlation.levels_required} shared levels archived. ${correlation.reason}`;
    document.getElementById("hedgeReason").textContent = `${hedge.observed_shared_levels} of ${hedge.levels_required} shared levels archived. ${hedge.reason}`;
    document.getElementById("effectivenessReason").textContent = data.analytics.hedge_effectiveness.reason;
  }

  function renderCoverage() {
    const coverage = data.coverage;
    const dimensions = coverage[0].dimensions.map(item => item.dimension);
    document.getElementById("coverageHead").innerHTML = `<tr><th scope="col">Dimension</th>${coverage.map(pair => `<th scope="col">${escapeHtml(pair.gpu_model)} <span aria-label="confidence grade ${pair.confidence_grade}">/${pair.confidence_grade}</span></th>`).join("")}</tr>`;
    document.getElementById("coverageBody").innerHTML = dimensions.map(dimension => {
      const cells = coverage.map(pair => {
        const assessment = pair.dimensions.find(item => item.dimension === dimension);
        return `<td class="coverage-cell" data-label="${escapeHtml(pair.gpu_model)}">
          <div class="coverage-cell-head"><i class="status-mark ${assessment.status}" aria-hidden="true"></i>${titleCase(assessment.status)}</div>
          <div class="coverage-values"><span>O: ${escapeHtml(display(assessment.ornn))}</span><span>SD: ${escapeHtml(display(assessment.silicon_data))}</span></div>
        </td>`;
      }).join("");
      return `<tr><th scope="row">${escapeHtml(dimensionLabels[dimension] || titleCase(dimension))}</th>${cells}</tr>`;
    }).join("");
  }

  let eventFilter = "all";

  function eventMatches(event) {
    if (eventFilter === "all") return true;
    if (eventFilter === "quantified") return event.impact_status === "quantified_range";
    if (eventFilter === "unrestated") return event.restated === false && event.event_type !== "new_index";
    if (eventFilter === "ornn") return event.vendor === "ornn";
    return true;
  }

  function impactText(event) {
    if (!event.impacts.length) return event.impact_status === "unquantified" ? "Impact not quantified" : "No impact range";
    return event.impacts.map(impact => {
      const range = impact.low_pct === impact.high_pct
        ? formatSigned(impact.low_pct)
        : `${formatSigned(impact.low_pct)} to ${formatSigned(impact.high_pct)}`;
      return `${impact.benchmark_id}: ${range}`;
    }).join(" · ");
  }

  function renderEvents() {
    const events = data.events.filter(eventMatches);
    const ledger = document.getElementById("eventLedger");
    if (!events.length) {
      ledger.innerHTML = '<li class="empty-ledger">No events match this filter.</li>';
      return;
    }
    ledger.innerHTML = events.map(event => `
      <li class="event-row">
        <p class="event-date"><time datetime="${event.effective}">${event.effective}</time>${event.announced ? `<br>Announced ${event.announced}` : ""}</p>
        <div class="event-main">
          <h3>${escapeHtml(eventLabels[event.event_type] || titleCase(event.event_type))}</h3>
          <p>${escapeHtml(event.notes)}</p>
        </div>
        <div class="event-meta">
          <span class="event-chip">${escapeHtml(event.vendor === "silicon_data" ? "Silicon Data" : "Ornn")}</span>
          ${event.restated === true ? '<span class="event-chip restated">Restated</span>' : event.restated === false ? '<span class="event-chip signal">Not restated</span>' : ""}
          <span class="event-impact">${escapeHtml(impactText(event))}</span>
        </div>
      </li>`).join("");
  }

  function setupEventFilters() {
    document.querySelector(".ledger-toolbar").addEventListener("click", event => {
      const button = event.target.closest(".filter-button");
      if (!button) return;
      eventFilter = button.dataset.filter;
      document.querySelectorAll(".filter-button").forEach(item => {
        const active = item === button;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      renderEvents();
    });
  }

  function methodValue(key, value) {
    if (key === "dated_break_register") return value ? "Published" : "Not found in archived evidence";
    return display(value);
  }

  function renderMethodologies() {
    document.getElementById("methodologyGrid").innerHTML = data.methodologies.map(method => {
      const rows = Object.keys(methodLabels).map(key => `
        <div><dt>${methodLabels[key]}</dt><dd>${escapeHtml(methodValue(key, method[key]))}</dd></div>
      `).join("");
      return `<article class="methodology-sheet">
        <p class="methodology-vendor">${method.vendor === "silicon_data" ? "Silicon Data" : "Ornn"}</p>
        <h3>${escapeHtml(method.methodology_version)}</h3>
        <dl class="method-list">${rows}</dl>
        <p class="methodology-note">${escapeHtml(method.notes)}</p>
      </article>`;
    }).join("");
  }

  renderBasisChart();
  renderGpuTabs();
  renderPairDetail();
  renderEstimateGates();
  renderCoverage();
  setupEventFilters();
  renderEvents();
  renderMethodologies();
})();
