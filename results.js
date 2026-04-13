const T_TABLE = { 1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365 };

function ciHalfWidth(values) {
  if (values.length < 2) return null;
  const n = values.length;
  const mean = values.reduce((s, v) => s + v, 0) / n;
  const std = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1));
  const t = T_TABLE[n - 1] || 1.96;
  return (t * std) / Math.sqrt(n);
}

(function () {
  const data = window.AGENTIC_CONVERSATIONS || { issues: [] };
  const summaryRoot = document.getElementById("results-summary");
  const testsRoot = document.getElementById("results-tests");

  if (!summaryRoot || !testsRoot) {
    return;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatStatus(run) {
    if (!run) {
      return "No run";
    }
    return `${run.final_status === "success" ? "Success" : "Failed"}, ${run.llm_calls_used} calls, ${Number(run.latency_seconds || 0).toFixed(2)}s`;
  }

  function latestRun(issue, architecture) {
    const runs = issue.runs && issue.runs[architecture] ? issue.runs[architecture] : [];
    return runs.length ? runs[0] : null;
  }

  function issueLabel(issue) {
    return escapeHtml(issue.title || issue.task_id || "Issue");
  }

  function outcomeChip(issue) {
    const single = latestRun(issue, "single");
    const multi = latestRun(issue, "multi");
    const singlePass = single && single.final_status === "success";
    const multiPass = multi && multi.final_status === "success";
    if (singlePass && multiPass) {
      return '<span class="summary-chip success-chip">Both passed</span>';
    }
    if (singlePass && !multiPass) {
      return '<span class="summary-chip mixed-chip">Single won</span>';
    }
    if (!singlePass && multiPass) {
      return '<span class="summary-chip mixed-chip">Multi won</span>';
    }
    return '<span class="summary-chip failure-chip">Still failing</span>';
  }

  function takeaway(issue) {
    const single = latestRun(issue, "single");
    const multi = latestRun(issue, "multi");
    const singlePass = single && single.final_status === "success";
    const multiPass = multi && multi.final_status === "success";

    if (singlePass && multiPass) {
      const faster = Number(single.latency_seconds || 0) <= Number(multi.latency_seconds || 0) ? "Single-agent" : "Multi-agent";
      return `${faster} was more efficient on the latest recorded runs.`;
    }
    if (singlePass && !multiPass) {
      return "Single-agent passed the latest run while multi-agent did not.";
    }
    if (!singlePass && multiPass) {
      return "Multi-agent passed the latest run while single-agent did not.";
    }
    return "Neither architecture has a passing latest run for this issue.";
  }

  function architectureRuns(issue, architecture) {
    return issue.runs && issue.runs[architecture] ? issue.runs[architecture] : [];
  }

  function summarizeRuns(runs) {
    if (!runs.length) {
      return {
        runCount: 0,
        successRate: "No runs",
        failureCategories: "No runs",
        avgLatency: "No runs",
        avgIterations: "No runs",
        avgLlmCalls: "No runs",
      };
    }

    const successes = runs.filter((run) => run.final_status === "success").length;
    const latencyVals = runs.map((run) => Number(run.latency_seconds || 0));
    const avgLatencyRaw = latencyVals.reduce((sum, v) => sum + v, 0) / runs.length;
    const latencyCi = ciHalfWidth(latencyVals);
    const avgLatency = latencyCi !== null
      ? `${avgLatencyRaw.toFixed(2)}s \u00b1 ${latencyCi.toFixed(2)}s (95% CI)`
      : `${avgLatencyRaw.toFixed(2)}s`;
    const avgIterations = runs.reduce((sum, run) => sum + Number(run.iterations || 0), 0) / runs.length;
    const avgLlmCalls = runs.reduce((sum, run) => sum + Number(run.llm_calls_used || 0), 0) / runs.length;
    const failureCounts = {};

    runs.forEach((run) => {
      const key = run.failure_category || "unknown";
      failureCounts[key] = (failureCounts[key] || 0) + 1;
    });

    const failureCategories = Object.entries(failureCounts)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([label, count]) => `${label} (${count})`)
      .join(", ");

    return {
      runCount: runs.length,
      successRate: `${((successes / runs.length) * 100).toFixed(0)}%`,
      failureCategories,
      avgLatency: `${avgLatency.toFixed(2)}s`,
      avgIterations: avgIterations.toFixed(2),
      avgLlmCalls: avgLlmCalls.toFixed(2),
    };
  }

  function renderCharts() {
    const cd = window.AGENTIC_CHART_DATA;
    if (!cd) return;

    const SINGLE_COLOR  = "rgba(15, 118, 110, 0.75)";
    const MULTI_COLOR   = "rgba(29, 78, 216, 0.75)";
    const SINGLE_BORDER = "rgba(15, 118, 110, 1)";
    const MULTI_BORDER  = "rgba(29, 78, 216, 1)";

    // Latency bar chart
    new Chart(document.getElementById("chart-latency"), {
      type: "bar",
      data: {
        labels: cd.taskLabels,
        datasets: [
          {
            label: "Single-agent",
            data: cd.latency.single.means,
            backgroundColor: SINGLE_COLOR,
            borderColor: SINGLE_BORDER,
            borderWidth: 1.5,
            borderRadius: 6,
          },
          {
            label: "Multi-agent",
            data: cd.latency.multi.means,
            backgroundColor: MULTI_COLOR,
            borderColor: MULTI_BORDER,
            borderWidth: 1.5,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              afterLabel: (ctx) => {
                const arch = ctx.datasetIndex === 0 ? "single" : "multi";
                const ci = cd.latency[arch].ci[ctx.dataIndex];
                return ci !== null ? `95% CI: \u00b1${ci.toFixed(2)}s` : "";
              },
            },
          },
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "Seconds" } },
        },
      },
    });

    // LLM calls bar chart
    new Chart(document.getElementById("chart-llm"), {
      type: "bar",
      data: {
        labels: cd.taskLabels,
        datasets: [
          {
            label: "Single-agent",
            data: cd.llmCalls.single.means,
            backgroundColor: SINGLE_COLOR,
            borderColor: SINGLE_BORDER,
            borderWidth: 1.5,
            borderRadius: 6,
          },
          {
            label: "Multi-agent",
            data: cd.llmCalls.multi.means,
            backgroundColor: MULTI_COLOR,
            borderColor: MULTI_BORDER,
            borderWidth: 1.5,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "bottom" } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1 },
            title: { display: true, text: "LLM calls" },
          },
        },
      },
    });

    // Success rate horizontal bar chart
    new Chart(document.getElementById("chart-success"), {
      type: "bar",
      data: {
        labels: cd.taskLabels,
        datasets: [
          {
            label: "Single-agent",
            data: cd.successRate.single.map((v) => (v * 100).toFixed(0)),
            backgroundColor: SINGLE_COLOR,
            borderRadius: 6,
          },
          {
            label: "Multi-agent",
            data: cd.successRate.multi.map((v) => (v * 100).toFixed(0)),
            backgroundColor: MULTI_COLOR,
            borderRadius: 6,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { position: "bottom" } },
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
            title: { display: true, text: "Success %" },
          },
        },
      },
    });
  }

  function renderSummary() {
    if (!data.issues.length) {
      summaryRoot.innerHTML = '<div class="empty-state">No benchmark results yet. Run a benchmark suite and export site data to populate this page.</div>';
      return;
    }

    const cards = data.issues
      .map((issue) => {
        const singleStats = summarizeRuns(architectureRuns(issue, "single"));
        const multiStats = summarizeRuns(architectureRuns(issue, "multi"));
        return `
          <article class="test-card" open>
            <div class="test-card-body">
              <div class="detail-grid">
                <article class="detail-block">
                  <h3>${issueLabel(issue)}</h3>
                  <ul class="clean-list">
                    <li>Repository: <code>${escapeHtml(issue.repository || "Unknown")}</code></li>
                    <li>Single-agent success rate: ${escapeHtml(singleStats.successRate)}</li>
                    <li>Single-agent failure categories: ${escapeHtml(singleStats.failureCategories)}</li>
                    <li>Single-agent latency: ${escapeHtml(singleStats.avgLatency)}</li>
                    <li>Single-agent iteration count: ${escapeHtml(singleStats.avgIterations)}</li>
                    <li>Single-agent LLM call usage: ${escapeHtml(singleStats.avgLlmCalls)}</li>
                  </ul>
                </article>
                <article class="detail-block">
                  <h3>Multi-Agent</h3>
                  <ul class="clean-list">
                    <li>Run count: ${escapeHtml(String(multiStats.runCount))}</li>
                    <li>Success rate: ${escapeHtml(multiStats.successRate)}</li>
                    <li>Failure categories: ${escapeHtml(multiStats.failureCategories)}</li>
                    <li>Latency: ${escapeHtml(multiStats.avgLatency)}</li>
                    <li>Iteration count: ${escapeHtml(multiStats.avgIterations)}</li>
                    <li>LLM call usage: ${escapeHtml(multiStats.avgLlmCalls)}</li>
                  </ul>
                </article>
              </div>
            </div>
          </article>
        `;
      })
      .join("");

    summaryRoot.innerHTML = `<div class="accordion-list">${cards}</div>`;
  }

  function renderRunDetails(label, run) {
    if (!run) {
      return `<li>${label}: no run recorded.</li>`;
    }
    return `
      <li>${label}: ${escapeHtml(run.final_status)}, ${escapeHtml(run.llm_calls_used)} calls, ${escapeHtml(Number(run.latency_seconds || 0).toFixed(2))}s.</li>
      <li>${label} review: ${escapeHtml(run.review_notes || "No review notes recorded.")}</li>
    `;
  }

  function renderIssueCard(issue, index) {
    const single = latestRun(issue, "single");
    const multi = latestRun(issue, "multi");
    const singleStats = summarizeRuns(architectureRuns(issue, "single"));
    const multiStats = summarizeRuns(architectureRuns(issue, "multi"));
    const changedFiles = Array.from(new Set([...(single?.changed_files || []), ...(multi?.changed_files || [])]));
    return `
      <details class="test-card"${index === 0 ? " open" : ""}>
        <summary>
          <span>
            <span class="mini-label">${escapeHtml(issue.repository || "Repository")}</span>
            <strong>${issueLabel(issue)}</strong>
          </span>
          ${outcomeChip(issue)}
        </summary>
        <div class="test-card-body">
          <div class="detail-grid">
            <article class="detail-block">
              <h3>Task details</h3>
              <ul class="clean-list">
                <li>Repo: <code>${escapeHtml(issue.repository || "Unknown")}</code></li>
                <li>Workflow data source: <code>${escapeHtml((single || multi || {}).workflow_label || "n/a")}</code></li>
                <li>Changed files: ${changedFiles.length ? changedFiles.map((value) => `<code>${escapeHtml(value)}</code>`).join(", ") : "None recorded"}</li>
                <li>Takeaway: ${escapeHtml(takeaway(issue))}</li>
              </ul>
            </article>
            <article class="detail-block">
              <h3>Requested stats</h3>
              <ul class="clean-list">
                <li>Single-agent success rate: ${escapeHtml(singleStats.successRate)}</li>
                <li>Single-agent failure categories: ${escapeHtml(singleStats.failureCategories)}</li>
                <li>Single-agent latency: ${escapeHtml(singleStats.avgLatency)}</li>
                <li>Single-agent iteration count: ${escapeHtml(singleStats.avgIterations)}</li>
                <li>Single-agent LLM call usage: ${escapeHtml(singleStats.avgLlmCalls)}</li>
                <li>Multi-agent success rate: ${escapeHtml(multiStats.successRate)}</li>
                <li>Multi-agent failure categories: ${escapeHtml(multiStats.failureCategories)}</li>
                <li>Multi-agent latency: ${escapeHtml(multiStats.avgLatency)}</li>
                <li>Multi-agent iteration count: ${escapeHtml(multiStats.avgIterations)}</li>
                <li>Multi-agent LLM call usage: ${escapeHtml(multiStats.avgLlmCalls)}</li>
              </ul>
            </article>
          </div>
          <div class="detail-grid detail-grid-wide">
            <article class="detail-block">
              <h3>Latest recorded run</h3>
              <ul class="clean-list">
                <li>Single-agent model: <code>${escapeHtml((single || {}).model || "n/a")}</code></li>
                <li>Multi-agent model: <code>${escapeHtml((multi || {}).model || "n/a")}</code></li>
                <li>Single-agent validation: ${escapeHtml((single || {}).validation_report || "No validation report recorded.")}</li>
                <li>Multi-agent validation: ${escapeHtml((multi || {}).validation_report || "No validation report recorded.")}</li>
              </ul>
            </article>
            <article class="detail-block">
              <h3>Architecture details</h3>
              <ul class="clean-list">
                <li>Single-agent role count: <code>${escapeHtml((single || {}).role_count ?? "n/a")}</code></li>
                <li>Multi-agent role count: <code>${escapeHtml((multi || {}).role_count ?? "n/a")}</code></li>
                <li>Single-agent workflow label: <code>${escapeHtml((single || {}).workflow_label || "n/a")}</code></li>
                <li>Multi-agent workflow label: <code>${escapeHtml((multi || {}).workflow_label || "n/a")}</code></li>
              </ul>
            </article>
          </div>
        </div>
      </details>
    `;
  }

  function renderTests() {
    if (!data.issues.length) {
      testsRoot.innerHTML = '<div class="empty-state">No benchmark results yet. Run a benchmark suite and export site data to populate this page.</div>';
      return;
    }

    testsRoot.innerHTML = `<div class="accordion-list">${data.issues.map(renderIssueCard).join("")}</div>`;
  }

  renderCharts();
  renderSummary();
  renderTests();
})();
