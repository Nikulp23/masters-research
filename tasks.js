(function () {
  const data = window.AGENTIC_CONVERSATIONS || { issues: [] };
  const catalog = window.AGENTIC_TASK_CATALOG || {};
  const root = document.getElementById("task-reference-list");
  const projectRepoBase = "https://github.com/Nikulp23/masters-research/tree/main/";

  if (!root) {
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

  function externalRepoUrl(repository, taskMeta) {
    if (repository.startsWith("local-fixture/")) {
      return taskMeta && taskMeta.localPath ? `${projectRepoBase}${taskMeta.localPath}` : "";
    }
    return `https://github.com/${repository}`;
  }

  function issueUrl(issue, taskMeta) {
    if (issue.repository.startsWith("local-fixture/")) {
      return taskMeta && taskMeta.localPath ? `${projectRepoBase}${taskMeta.localPath}` : "";
    }
    return `https://github.com/${issue.repository}/issues?q=${encodeURIComponent(issue.title || issue.task_id)}`;
  }

  function unique(values) {
    return Array.from(new Set(values.filter(Boolean)));
  }

  function groupIssuesByRepo() {
    const groups = new Map();
    data.issues.forEach((issue) => {
      const group = groups.get(issue.repository) || [];
      group.push(issue);
      groups.set(issue.repository, group);
    });
    return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }

  function renderRepoCard([repository, issues]) {
    const tasks = issues.map((issue) => catalog[issue.task_id] || {});
    const testFiles = unique(tasks.flatMap((task) => task.testFiles || []));
    const testCommands = unique(tasks.map((task) => task.testCommand || ""));
    const repoLink = externalRepoUrl(repository, tasks.find((task) => task.localPath) || {});

    return `
      <article class="test-card">
        <div class="test-card-body">
          <div class="detail-grid">
            <article class="detail-block">
              <h3>${repoLink ? `<a class="resource-link" href="${escapeHtml(repoLink)}" target="_blank" rel="noreferrer">${escapeHtml(repository)}</a>` : escapeHtml(repository)}</h3>
              <ul class="clean-list">
                <li>Repo name: <code>${escapeHtml(repository)}</code></li>
                <li>Repo link: ${repoLink ? `<a class="resource-link" href="${escapeHtml(repoLink)}" target="_blank" rel="noreferrer">${escapeHtml(repoLink)}</a>` : "No external repo link recorded"}</li>
                <li>Issues tried: ${escapeHtml(String(issues.length))}</li>
              </ul>
            </article>
            <article class="detail-block">
              <h3>Tests used</h3>
              <ul class="clean-list">
                ${testFiles.length ? testFiles.map((file) => `<li><code>${escapeHtml(file)}</code></li>`).join("") : "<li>No test file metadata recorded.</li>"}
                ${testCommands.length ? testCommands.map((command) => `<li><code>${escapeHtml(command)}</code></li>`).join("") : "<li>No test command recorded.</li>"}
              </ul>
            </article>
          </div>
          <div class="detail-grid detail-grid-wide">
            <article class="detail-block">
              <h3>Issue names tried</h3>
              <ul class="clean-list issue-link-list">
                ${issues.map((issue) => {
                  const taskMeta = catalog[issue.task_id] || {};
                  const link = issueUrl(issue, taskMeta);
                  if (!link) {
                    return `<li>${escapeHtml(issue.title || issue.task_id)}</li>`;
                  }
                  return `<li><a class="resource-link" href="${escapeHtml(link)}" target="_blank" rel="noreferrer">${escapeHtml(issue.title || issue.task_id)}</a></li>`;
                }).join("")}
              </ul>
            </article>
          </div>
        </div>
      </article>
    `;
  }

  if (!data.issues.length) {
    root.innerHTML = '<div class="empty-state">No exported issue data yet. Run a benchmark suite first.</div>';
    return;
  }

  root.innerHTML = groupIssuesByRepo().map(renderRepoCard).join("");
})();
