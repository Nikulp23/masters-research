(function () {
  const data = window.AGENTIC_CONVERSATIONS || { issues: [] };
  const issueList = document.getElementById("issue-list");
  const app = document.getElementById("conversation-app");

  if (!issueList || !app) {
    return;
  }

  const state = {
    issueId: data.issues[0] ? data.issues[0].task_id : null,
    architecture: "single",
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function prettyValue(value) {
    return String(value || "")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function architectureLabel(value) {
    return value === "multi" ? "Multi-Agent" : "Single-Agent";
  }

  function statusClass(status) {
    if (status === "success") {
      return "success-chip";
    }
    if (status === "failed") {
      return "failure-chip";
    }
    return "mixed-chip";
  }

  function renderIssueList() {
    if (!data.issues.length) {
      issueList.innerHTML = '<div class="empty-state">No exported conversation data was found.</div>';
      return;
    }

    issueList.innerHTML = data.issues
      .map((issue) => {
        const isActive = issue.task_id === state.issueId;
        const singleCount = (issue.runs.single || []).length;
        const multiCount = (issue.runs.multi || []).length;
        return `
          <button class="issue-button${isActive ? " active" : ""}" data-issue-id="${escapeHtml(issue.task_id)}">
            <span class="issue-title">${escapeHtml(issue.title)}</span>
            <span class="issue-meta">${escapeHtml(issue.repository)}</span>
            <span class="issue-meta">${singleCount} single / ${multiCount} multi</span>
          </button>
        `;
      })
      .join("");

    issueList.querySelectorAll("[data-issue-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.issueId = button.getAttribute("data-issue-id");
        render();
      });
    });
  }

  function renderTranscriptEntry(entry) {
    const segments = [];
    if (entry.prompt) {
      segments.push(`
        <details class="transcript-panel">
          <summary>Prompt</summary>
          <pre>${escapeHtml(entry.prompt)}</pre>
        </details>
      `);
    }
    if (entry.response) {
      segments.push(`
        <details class="transcript-panel" open>
          <summary>Response</summary>
          <pre>${escapeHtml(entry.response)}</pre>
        </details>
      `);
    }
    if (entry.message) {
      segments.push(`<div class="transcript-note">${escapeHtml(entry.message)}</div>`);
    }
    if (entry.patch_payload) {
      segments.push(`
        <details class="transcript-panel">
          <summary>Patch Payload</summary>
          <pre>${escapeHtml(entry.patch_payload)}</pre>
        </details>
      `);
    }
    if (entry.test_stdout || entry.test_stderr) {
      const executionText = `returncode=${entry.test_returncode}\n\nSTDOUT:\n${entry.test_stdout || ""}\n\nSTDERR:\n${entry.test_stderr || ""}`;
      segments.push(`
        <details class="transcript-panel">
          <summary>Test Output</summary>
          <pre>${escapeHtml(executionText)}</pre>
        </details>
      `);
    }

    return `
      <article class="transcript-item">
        <div class="transcript-meta">
          <span class="role-pill">${escapeHtml(prettyValue(entry.role))}</span>
          <span>${escapeHtml(prettyValue(entry.phase))}</span>
          <span>Iteration ${escapeHtml(entry.iteration ?? 0)}</span>
          <span>Revision ${escapeHtml(entry.revision ?? 0)}</span>
        </div>
        ${segments.join("") || '<div class="transcript-note">No detailed content was recorded for this step.</div>'}
      </article>
    `;
  }

  function renderRun(run) {
    const transcript = Array.isArray(run.transcript) ? run.transcript : [];
    const changedFiles = run.changed_files && run.changed_files.length
      ? run.changed_files.map((value) => `<code>${escapeHtml(value)}</code>`).join(", ")
      : "None";

    const branchResults = Array.isArray(run.branch_results) ? run.branch_results : [];
    return `
      <article class="run-card">
        <div class="run-card-top">
          <div>
            <div class="mini-label">${escapeHtml(run.timestamp_utc || "Unknown time")}</div>
            <h3>${escapeHtml(run.run_id)}</h3>
          </div>
          <span class="summary-chip ${statusClass(run.final_status)}">${escapeHtml(run.final_status)}</span>
        </div>
        <div class="run-stats">
          <span>Model: <code>${escapeHtml(run.model || "n/a")}</code></span>
          <span>LLM calls: <strong>${escapeHtml(run.llm_calls_used ?? 0)}</strong></span>
          <span>Iterations: <strong>${escapeHtml(run.iterations ?? 0)}</strong></span>
          <span>Revisions: <strong>${escapeHtml(run.revision_count ?? 0)}</strong></span>
          <span>Latency: <strong>${escapeHtml(run.latency_seconds ?? 0)}s</strong></span>
          ${branchResults.length ? `<span>Engineer workers: <strong>${escapeHtml(run.engineer_worker_count ?? branchResults.length)}</strong></span>` : ""}
        </div>
        <div class="detail-grid detail-grid-wide">
          <article class="detail-block">
            <h3>Issue summary</h3>
            <p>${escapeHtml(run.issue_summary || "No summary recorded.")}</p>
            <p>${escapeHtml(run.root_cause || "No root-cause note recorded.")}</p>
          </article>
          <article class="detail-block">
            <h3>Validation and review</h3>
            <p>${escapeHtml(run.validation_report || "No validation report recorded.")}</p>
            <p>${escapeHtml(run.review_notes || "No review notes recorded.")}</p>
          </article>
        </div>
        <div class="detail-grid detail-grid-wide">
          <article class="detail-block">
            <h3>Patch details</h3>
            <p>${escapeHtml(run.patch_summary || "No patch summary recorded.")}</p>
            <p>Changed files: ${changedFiles}</p>
          </article>
          <article class="detail-block">
            <h3>Run outcome</h3>
            <p>Failure category: <code>${escapeHtml(run.failure_category || "success")}</code></p>
            <p>Review recommendation: <code>${escapeHtml(run.review_recommendation || "n/a")}</code></p>
            <p>Test return code: <code>${escapeHtml(run.test_returncode ?? "n/a")}</code></p>
            ${branchResults.length ? `<p>Selected branch: <code>${escapeHtml(run.selected_branch_id || "n/a")}</code></p>` : ""}
          </article>
        </div>
        ${
          branchResults.length
            ? `
              <div class="detail-block">
                <h3>Engineer Branches</h3>
                ${branchResults
                  .map((branch) => {
                    const branchTranscript = Array.isArray(branch.transcript) ? branch.transcript : [];
                    const branchChangedFiles = branch.changed_files && branch.changed_files.length
                      ? branch.changed_files.map((value) => `<code>${escapeHtml(value)}</code>`).join(", ")
                      : "None";
                    return `
                      <details class="transcript-panel"${branch.branch_id === run.selected_branch_id ? " open" : ""}>
                        <summary>${escapeHtml(branch.branch_id)}${branch.branch_id === run.selected_branch_id ? " (selected)" : ""}</summary>
                        <p>Status: <code>${escapeHtml(branch.validation_passed && branch.review_recommendation === "accept" ? "accepted" : "rejected")}</code></p>
                        <p>Changed files: ${branchChangedFiles}</p>
                        <p>Validation: ${escapeHtml(branch.validation_report || "No validation report recorded.")}</p>
                        <p>Review: ${escapeHtml(branch.review_notes || "No review notes recorded.")}</p>
                        <div class="transcript-list">
                          ${branchTranscript.length ? branchTranscript.map(renderTranscriptEntry).join("") : '<div class="empty-state">No branch transcript was recorded.</div>'}
                        </div>
                      </details>
                    `;
                  })
                  .join("")}
              </div>
            `
            : ""
        }
        <div class="transcript-list">
          ${transcript.length ? transcript.map(renderTranscriptEntry).join("") : '<div class="empty-state">No transcript was recorded for this run.</div>'}
        </div>
      </article>
    `;
  }

  function renderConversationView() {
    const issue = data.issues.find((item) => item.task_id === state.issueId);
    if (!issue) {
      app.innerHTML = '<div class="empty-state">No issue selected.</div>';
      return;
    }

    const runs = (issue.runs[state.architecture] || []).slice();
    app.innerHTML = `
      <div class="conversation-header">
        <div>
          <p class="eyebrow">Selected issue</p>
          <h2>${escapeHtml(issue.title)}</h2>
          <p class="lede">${escapeHtml(issue.repository)}</p>
        </div>
        <div class="tab-bar">
          ${["single", "multi"]
            .map(
              (architecture) => `
                <button class="tab-button${architecture === state.architecture ? " active" : ""}" data-architecture="${architecture}">
                  ${architectureLabel(architecture)}
                </button>
              `
            )
            .join("")}
        </div>
      </div>
      ${
        runs.length
          ? runs.map(renderRun).join("")
          : `<div class="empty-state">No ${architectureLabel(state.architecture)} runs were exported for this issue yet.</div>`
      }
    `;

    app.querySelectorAll("[data-architecture]").forEach((button) => {
      button.addEventListener("click", () => {
        state.architecture = button.getAttribute("data-architecture");
        renderConversationView();
        renderIssueList();
      });
    });
  }

  function render() {
    renderIssueList();
    renderConversationView();
  }

  render();
})();
