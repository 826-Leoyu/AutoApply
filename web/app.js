const state = {
  view: "jobs",
  jobs: [],
  currentId: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail || detail;
    } catch {
      /* keep text */
    }
    throw new Error(detail);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res;
}

function show(view) {
  state.view = view;
  $$(".view").forEach((el) => el.classList.add("hidden"));
  const target = view === "detail" ? "view-detail" : `view-${view}`;
  $(`#${target}`).classList.remove("hidden");
  $$("nav button").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
}

function statusLabel(status) {
  return (
    {
      queued: "待处理",
      preparing: "生成中",
      ready: "材料就绪",
      applying: "投递中",
      needs_review: "请在电脑确认",
      submitted: "已提交",
      error: "出错",
    }[status] || status
  );
}

async function refreshMeta() {
  const meta = await api("/api/meta");
  $("#localUrl").textContent = meta.local_url;
  $("#phoneUrl").textContent = meta.phone_url;
  $("#masterHint").textContent = meta.master_pdf
    ? "已找到 resume/master.pdf，将按原版框架改 Highlight。"
    : "还没有 master.pdf。本地测试会用档案生成一份简易简历。";
}

async function refreshJobs() {
  state.jobs = await api("/api/jobs");
  const root = $("#jobList");
  if (!state.jobs.length) {
    root.innerHTML = `<div class="card muted">队列是空的。先点「添加本地测试岗位」走一遍，或粘贴一个真实 ATS 链接。</div>`;
    return;
  }
  root.innerHTML = state.jobs
    .map(
      (job) => `
      <article class="card job" data-id="${job.id}">
        <div>
          <h3>${escapeHtml(job.title || job.url)}</h3>
          <p>${escapeHtml(job.company || "未知公司")} · ${escapeHtml(job.source)}</p>
        </div>
        <span class="badge">${statusLabel(job.status)}</span>
        <button data-open="${job.id}">打开</button>
      </article>`
    )
    .join("");
  root.querySelectorAll("[data-open]").forEach((btn) => {
    btn.addEventListener("click", () => openJob(btn.dataset.open));
  });
}

async function openJob(id) {
  state.currentId = id;
  show("detail");
  await renderDetail();
}

async function renderDetail() {
  if (!state.currentId) return;
  const job = await api(`/api/jobs/${state.currentId}`);
  $("#detailTitle").textContent = job.title || "未命名岗位";
  $("#detailMeta").textContent = `${job.company || "未知公司"} · ${job.url}`;
  $("#detailStatus").textContent = `${statusLabel(job.status)}${job.error ? " — " + job.error : ""}`;
  $("#jdText").textContent = job.jd_text || "还没抓取 JD，请点「生成材料」。";
  $("#logText").textContent = (job.apply_log || []).join("\n") || "暂无日志";
  const box = $("#highlights");
  if (!job.highlights?.length) {
    box.innerHTML = `<p class="muted">没有从 PDF 里识别到 Highlight。放入 master.pdf 后效果更好；本地测试仍会生成 PDF。</p>`;
  } else {
    box.innerHTML = job.highlights
      .map(
        (item, i) => `
        <div class="hl">
          <p class="muted">原句：${escapeHtml(item.original)}</p>
          <textarea data-i="${i}">${escapeHtml(item.rewritten)}</textarea>
        </div>`
      )
      .join("");
  }
  $("#resumeFrame").src = job.resume_path ? `/api/jobs/${job.id}/files/resume?ts=${Date.now()}` : "about:blank";
  $("#coverFrame").src = job.cover_path ? `/api/jobs/${job.id}/files/cover?ts=${Date.now()}` : "about:blank";
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadProfile() {
  const profile = await api("/api/profile");
  const form = $("#profileForm");
  for (const [key, value] of Object.entries(profile)) {
    if (form[key] && typeof value === "string") {
      if (value === "********") form[key].value = "";
      else form[key].value = value;
    }
  }
}

function init() {
  $$("nav button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      show(btn.dataset.view);
      if (btn.dataset.view === "jobs") await refreshJobs();
      if (btn.dataset.view === "profile") await loadProfile();
      if (btn.dataset.view === "phone") await refreshMeta();
    });
  });

  $("#addForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    await api("/api/jobs", { method: "POST", body: JSON.stringify(data) });
    event.target.reset();
    await refreshJobs();
  });

  $("#scanForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    event.target.querySelector("button").disabled = true;
    try {
      const result = await api("/api/jobs/scan", {
        method: "POST",
        body: JSON.stringify({ ...data, limit: 8 }),
      });
      alert(`扫到 ${result.count} 个岗位，已加入队列`);
      await refreshJobs();
    } catch (err) {
      alert(err.message);
    } finally {
      event.target.querySelector("button").disabled = false;
    }
  });

  $("#demoBtn").addEventListener("click", async () => {
    const job = await api("/api/jobs/demo", { method: "POST" });
    await refreshJobs();
    await openJob(job.id);
  });

  $("#backBtn").addEventListener("click", async () => {
    show("jobs");
    await refreshJobs();
  });

  $("#prepareBtn").addEventListener("click", async () => {
    $("#prepareBtn").disabled = true;
    try {
      await api(`/api/jobs/${state.currentId}/prepare`, { method: "POST" });
      await renderDetail();
    } catch (err) {
      alert(err.message);
    } finally {
      $("#prepareBtn").disabled = false;
    }
  });

  $("#applyBtn").addEventListener("click", async () => {
    try {
      const result = await api(`/api/jobs/${state.currentId}/apply`, { method: "POST" });
      alert(result.message);
      await renderDetail();
    } catch (err) {
      alert(err.message);
    }
  });

  $("#submittedBtn").addEventListener("click", async () => {
    await api(`/api/jobs/${state.currentId}/mark?status=submitted`, { method: "POST" });
    await renderDetail();
  });

  $("#saveHighlights").addEventListener("click", async () => {
    const job = await api(`/api/jobs/${state.currentId}`);
    const textareas = $$("#highlights textarea");
    const highlights = job.highlights.map((item, i) => ({
      ...item,
      rewritten: textareas[i] ? textareas[i].value : item.rewritten,
    }));
    await api(`/api/jobs/${state.currentId}/highlights`, {
      method: "POST",
      body: JSON.stringify({ highlights }),
    });
    await renderDetail();
  });

  $("#profileForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    await api("/api/profile", { method: "PUT", body: JSON.stringify(data) });
    $("#profileMsg").textContent = "已保存";
  });

  refreshMeta().catch(console.error);
  refreshJobs().catch(console.error);
}

init();
