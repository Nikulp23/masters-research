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

  function renderSummary() {
    if (!data.issues.length) {
      summaryRoot.innerHTML = '<div class="empty-state">No benchmark results yet. Run a benchmark suite and export site data to populate this page.</div>';
      return;
    }

    const rows = data.issues
      .map((issue) => {
        const single = latestRun(issue, "single");
        const multi = latestRun(issue, "multi");
        return `
          <tr>
            <td>${issueLabel(issue)}</td>
            <td>${escapeHtml(formatStatus(single))}</td>
            <td>${escapeHtml(formatStatus(multi))}</td>
            <td>${escapeHtml(takeaway(issue))}</td>
          </tr>
        `;
      })
      .join("");

    summaryRoot.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Issue</th>
              <th>Single-Agent</th>
              <th>Multi-Agent</th>
              <th>Takeaway</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
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
              <h3>Run summary</h3>
              <ul class="clean-list">
                ${renderRunDetails("Single-agent", single)}
                ${renderRunDetails("Multi-agent", multi)}
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

  renderSummary();
  renderTests();
})();
