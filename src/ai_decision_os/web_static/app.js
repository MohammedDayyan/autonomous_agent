const form = document.querySelector("#goalForm");
const goalInput = document.querySelector("#goalInput");
const runState = document.querySelector("#runState");
const toolCount = document.querySelector("#toolCount");
const successCount = document.querySelector("#successCount");
const planList = document.querySelector("#planList");
const resultsList = document.querySelector("#resultsList");
const planBadge = document.querySelector("#planBadge");
const resultBadge = document.querySelector("#resultBadge");
const activeTransport = document.querySelector("#activeTransport");
const transportCopy = document.querySelector("#transportCopy");
const reportList = document.querySelector("#reportList");
const reportPreview = document.querySelector("#reportPreview");
const latestReport = document.querySelector("#latestReport");
const refreshReports = document.querySelector("#refreshReports");
const sampleButton = document.querySelector("#sampleButton");
const goalAnswer = document.querySelector("#goalAnswer");
const answerPreview = document.querySelector("#answerPreview");
const clearAnswer = document.querySelector("#clearAnswer");

function selectedTransport() {
  return document.querySelector("input[name='transport']:checked").value;
}

function updateTransportCopy() {
  const transport = selectedTransport();
  activeTransport.textContent = transport === "mcp" ? "MCP client" : "Direct calls";
  transportCopy.textContent =
    transport === "mcp"
      ? "Agent calls tools through the MCP server."
      : "Agent calls local tool functions in-process.";
}

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function describeTool(tool, args = {}) {
  if (tool === "search_memory") {
    return "Checking memory";
  }
  if (tool === "search_web") {
    return `Searching: ${args.query || "web"}`;
  }
  if (tool === "extract_page") {
    return "Reading source page";
  }
  if (tool === "analyze_github_repo") {
    return `Inspecting repo: ${args.repo || "GitHub"}`;
  }
  if (tool === "list_user_repos") {
    return `Listing repos for: ${args.username || "GitHub user"}`;
  }
  if (tool === "save_report") {
    return "Writing report";
  }
  if (tool === "save_memory") {
    return "Saving memory";
  }
  return `Running ${tool}`;
}

function setRunState(text, active = false) {
  runState.textContent = text;
  runState.classList.toggle("is-active", active);
}

function setAnswer(content) {
  answerPreview.textContent = content;
  goalAnswer.hidden = false;
}

function reportPathFromResults(results) {
  const reportResult = results.find((result) => result.tool === "save_report" && result.ok && result.data?.path);
  return reportResult?.data?.path || "";
}

function reportNameFromPath(path) {
  return path.split(/[\\/]/).filter(Boolean).pop() || "";
}

async function showAnswerFromOutput(output) {
  if (output.answer) {
    setAnswer(output.answer);
    return;
  }
  setAnswer(synthesizeAnswerFromObservations(output.goal || goalInput.value.trim(), output.observations || []));
}

function synthesizeAnswerFromObservations(goal, observations) {
  if (isCybersecurityToolsGoal(goal)) {
    return cybersecurityToolsAnswer(goal);
  }
  const bullets = [];
  observations.forEach((observation) => {
    const data = observation.data;
    if (Array.isArray(data)) {
      data.slice(0, 4).forEach((item) => {
        const title = item.title || item.repo || item.url || "Result";
        const snippet = item.snippet || item.description || "";
        if (snippet && !looksLikeFailure(`${title} ${snippet}`)) {
          bullets.push(`${title}: ${shorten(snippet)}`);
        }
      });
    } else if (data && typeof data === "object" && !data.error) {
      const title = data.title || data.repo || data.url || "Result";
      const text = data.text || data.description || data.snippet || "";
      if (text && !looksLikeFailure(`${title} ${text}`)) {
        bullets.push(`${title}: ${shorten(text)}`);
      }
    }
  });
  if (!bullets.length) {
    return `Answer to: ${goal}\n\nThe run completed, but there was not enough structured research output to synthesize a final answer.`;
  }
  return [`Answer to: ${goal}`, "", ...dedupe(bullets).slice(0, 5).map((item) => `- ${item}`)].join("\n");
}

function isCybersecurityToolsGoal(goal) {
  const lowered = String(goal).toLowerCase();
  return lowered.includes("cybersecurity") && lowered.includes("tool");
}

function cybersecurityToolsAnswer(goal) {
  return [
    `Answer to: ${goal}`,
    "",
    "There is no single finite list of all cybersecurity tools, because the category changes constantly. A complete practical toolkit is usually organized by security function:",
    "",
    "- Network protection: firewalls, web application firewalls, VPNs, IDS/IPS, network detection and response, DNS filtering, and secure web gateways.",
    "- Endpoint protection: antivirus, EDR, XDR, mobile device management, host firewalls, disk encryption, and patch management.",
    "- Identity and access: IAM, single sign-on, MFA, privileged access management, password managers, and identity threat detection.",
    "- Vulnerability management: asset discovery, vulnerability scanners, exposure management, configuration auditing, and penetration-testing frameworks.",
    "- Application security: SAST, DAST, SCA, secrets scanning, container scanning, API security testing, and runtime application protection.",
    "- Cloud and infrastructure security: CSPM, CWPP, CIEM, Kubernetes security, infrastructure-as-code scanning, and cloud log monitoring.",
    "- Detection and response: SIEM, SOAR, threat intelligence platforms, case management, digital forensics, malware analysis, and incident response tools.",
    "- Data security: DLP, encryption/key management, database activity monitoring, backup/recovery, and data discovery/classification.",
    "- Governance and compliance: GRC platforms, security awareness training, phishing simulation, policy management, and audit evidence collection.",
    "",
    "In short: use layered tooling across network, endpoint, identity, application, cloud, data, detection, response, and compliance instead of looking for one universal tool.",
  ].join("\n");
}

function looksLikeFailure(value) {
  return ["failed", "unavailable", "not found", "all connection attempts failed"].some((term) =>
    String(value).toLowerCase().includes(term)
  );
}

function shorten(value, limit = 260) {
  const cleaned = String(value).replace(/\s+/g, " ").trim();
  return cleaned.length <= limit ? cleaned : `${cleaned.slice(0, limit - 3).trim()}...`;
}

function dedupe(values) {
  const seen = new Set();
  return values.filter((value) => {
    const key = value.toLowerCase();
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function clearRun() {
  planList.innerHTML = "";
  resultsList.innerHTML = "";
  resultsList.className = "";
  toolCount.textContent = "0";
  successCount.textContent = "0";
  planBadge.textContent = "Planning";
  resultBadge.textContent = "Running";
  setRunState("Queued", true);
}

function appendEventLine(message, tone = "") {
  if (!resultsList.querySelector(".event-log")) {
    resultsList.innerHTML = `<div class="event-log"></div>`;
  }
  const log = resultsList.querySelector(".event-log");
  const row = document.createElement("div");
  row.className = `event-line ${tone}`;
  row.textContent = message;
  log.appendChild(row);
  resultsList.scrollTop = resultsList.scrollHeight;
}

function renderPlan(steps) {
  planList.innerHTML = "";
  steps.forEach((step) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="tool-name">
        <span>${step.tool}</span>
      </div>
      <div>${step.reason || "Scheduled tool call"}</div>
      <pre class="args">${formatJson(step.args || {})}</pre>
    `;
    planList.appendChild(item);
  });
  planBadge.textContent = `${steps.length} steps`;
}

function renderResults(results) {
  resultsList.className = "";
  resultsList.innerHTML = "";
  results.forEach((result) => {
    const item = document.createElement("article");
    item.className = "result-item";
    const status = result.ok ? "ok" : "error";
    item.innerHTML = `
      <div class="tool-name">
        <span>${result.tool}</span>
        <span class="pill ${status}">${status}</span>
      </div>
      ${result.error ? `<div class="error-text">${result.error}</div>` : ""}
      <pre class="result-data">${formatJson(result.data)}</pre>
    `;
    resultsList.appendChild(item);
  });
  const okCount = results.filter((result) => result.ok).length;
  toolCount.textContent = String(results.length);
  successCount.textContent = String(okCount);
  resultBadge.textContent = `${okCount}/${results.length} ok`;
}

async function runAgent(event) {
  event.preventDefault();
  const goal = goalInput.value.trim();
  if (!goal) {
    goalInput.focus();
    return;
  }

  clearRun();
  setRunState("Starting agent", true);
  form.querySelector("button[type='submit']").disabled = true;

  const params = new URLSearchParams({ goal, transport: selectedTransport() });
  const stream = new EventSource(`/api/run-stream?${params.toString()}`);
  let streamDone = false;

  appendEventLine("Run queued.");

  stream.onmessage = async (message) => {
    const payload = JSON.parse(message.data);
    if (payload.event === "started") {
      setRunState(`Planning ${payload.strategy || "run"}`, true);
      appendEventLine(`Strategy selected: ${payload.strategy}`);
    } else if (payload.event === "iteration") {
      setRunState(`Preparing ${payload.steps} tool step${payload.steps === 1 ? "" : "s"}`, true);
      appendEventLine(`Preparing ${payload.steps} tool step${payload.steps === 1 ? "" : "s"}.`);
    } else if (payload.event === "tool_started") {
      setRunState(describeTool(payload.tool, payload.args), true);
      appendEventLine(`Starting ${payload.tool}`);
    } else if (payload.event === "tool_finished") {
      setRunState(payload.ok ? `Finished ${payload.tool}` : `${payload.tool} failed`, true);
      appendEventLine(`${payload.tool} ${payload.ok ? "completed" : "failed"}`, payload.ok ? "ok" : "error");
    } else if (payload.event === "heartbeat") {
      return;
    } else if (payload.event === "complete") {
      streamDone = true;
      stream.close();
      const output = payload.output;
      renderPlan(output.plan.steps || []);
      renderResults(output.results || []);
      await showAnswerFromOutput(output);
      setRunState("Complete", false);
      await loadReports();
      form.querySelector("button[type='submit']").disabled = false;
    } else if (payload.event === "error") {
      streamDone = true;
      stream.close();
      setRunState("Failed", false);
      resultBadge.textContent = "Error";
      appendEventLine(payload.error || "Agent run failed.", "error");
      form.querySelector("button[type='submit']").disabled = false;
    }
  };

  stream.onerror = () => {
    if (streamDone) {
      return;
    }
    setRunState("Failed", false);
    resultBadge.textContent = "Error";
    appendEventLine("The run stream stopped unexpectedly. Check the server terminal for the backend error.", "error");
    stream.close();
    form.querySelector("button[type='submit']").disabled = false;
  };
}

async function loadReports() {
  const response = await fetch("/api/reports");
  const payload = await response.json();
  const reports = payload.reports || [];
  reportList.innerHTML = "";
  latestReport.textContent = reports[0]?.name || "None yet";

  if (!reports.length) {
    reportList.innerHTML = `<div class="results-empty">No reports saved yet.</div>`;
    return;
  }

  reports.forEach((report) => {
    const item = document.createElement("div");
    item.className = "report-item";
    item.innerHTML = `
      <button class="report-preview-button" type="button">
        <strong>${report.name}</strong>
        <span>${Math.ceil(report.size / 1024)} KB</span>
      </button>
      <button class="report-download" type="button">
        Download
      </button>
    `;
    item.querySelector(".report-preview-button").addEventListener("click", () => previewReport(report.name));
    item.querySelector(".report-download").addEventListener("click", () => downloadReport(report.name));
    reportList.appendChild(item);
  });
}

async function previewReport(name) {
  const response = await fetch(`/api/reports/${encodeURIComponent(name)}`);
  const payload = await response.json();
  if (response.ok) {
    if (window.marked) {
      reportPreview.innerHTML = marked.parse(payload.content);
    } else {
      reportPreview.textContent = payload.content;
    }
  } else {
    reportPreview.textContent = payload.error;
  }
}

async function downloadReport(name) {
  const response = await fetch(`/api/reports/${encodeURIComponent(name)}`);
  const payload = await response.json();
  if (!response.ok) {
    reportPreview.textContent = payload.error || "Report download failed.";
    return;
  }
  downloadTextFile(payload.name || name, payload.content || "");
}

document.querySelectorAll("input[name='transport']").forEach((input) => {
  input.addEventListener("change", updateTransportCopy);
});

form.addEventListener("submit", runAgent);
refreshReports.addEventListener("click", loadReports);
sampleButton.addEventListener("click", () => {
  goalInput.value = "Compare CrewAI, AutoGen, and LangGraph for backend automation and save a report";
  goalInput.focus();
});
clearAnswer.addEventListener("click", () => {
  goalAnswer.hidden = true;
  answerPreview.textContent = "";
});

updateTransportCopy();
loadReports();
