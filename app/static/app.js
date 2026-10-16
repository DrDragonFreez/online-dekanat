const form = document.getElementById("form");
const fileInput = document.getElementById("file");
const dropzone = document.getElementById("dropzone");
const dropFile = document.getElementById("dropFile");
const stages = document.getElementById("stages");
const result = document.getElementById("result");
const preview = document.getElementById("preview");
const previewBody = document.getElementById("previewBody");
const statusEl = document.getElementById("status");
const nonstandardCheckbox = document.getElementById("nonstandard");
const formatHint = document.getElementById("formatHint");
const toggleState = document.getElementById("toggleState");
const highlightCard = document.getElementById("highlightCard");
const highlightImg = document.getElementById("highlightImg");
const alwaysHighlight = document.getElementById("alwaysHighlight");
const highlightModeState = document.getElementById("highlightModeState");
const highlightHint = document.getElementById("highlightHint");
const highlightToggleRow = document.getElementById("highlightToggleRow");
const resetBtn = document.getElementById("resetBtn");
const empty = document.getElementById("empty");
const TYPE_LABEL = {
  study_certificate: "Справка об обучении",
  academic_leave_application: "Заявление на академический отпуск",
  internship_certificate: "Справка о практике",
  transfer_certificate: "Справка о переводе",
};
const FIELD_LABEL = {
  student_name: "ФИО студента",
  university: "Название вуза",
  program: "Направление подготовки",
  study_form: "Форма обучения",
  study_start: "Начало периода обучения",
  study_end: "Окончание периода обучения",
  document_number: "Номер справки",
  issue_date: "Дата выдачи",
  group: "Учебная группа",
  course: "Курс",
  leave_reason: "Причина отпуска",
  leave_start: "Дата начала отпуска",
  leave_end: "Дата окончания отпуска",
  application_date: "Дата заявления",
  organization: "Название организации",
  internship_start: "Дата начала практики",
  internship_end: "Дата окончания практики",
  supervisor_name: "ФИО руководителя практики",
  grade: "Оценка",
  from_university: "Откуда переводится",
  to_university: "Куда переводится",
  transfer_date: "Дата перевода",
  signature_present: "Подпись",
  seal_present: "Печать",
};
const SAMPLES = [
  {
    id: "std-certificate",
    label: "Справка об обучении",
    group: "standard",
    file: "/static/samples/std_certificate.png",
  },
  {
    id: "std-leave",
    label: "Заявление на академотпуск",
    group: "standard",
    file: "/static/samples/std_leave.png",
  },
  {
    id: "std-practice",
    label: "Справка о практике",
    group: "standard",
    file: "/static/samples/std_practice.png",
  },
  {
    id: "non-ranepa",
    label: "Реальная справка РАНХиГС",
    group: "nonstandard",
    file: "/static/samples/non_ranepa.png",
  },
  {
    id: "non-susu",
    label: "Реальная справка ЮУрГУ",
    group: "nonstandard",
    file: "/static/samples/non_susu.png",
  },
];
let previewUrl = null;
let highlightUrl = null;
let lastAnalyzeResult = null;
let lastFile = null;
function setupRouter() {
  const tabs = document.querySelectorAll(".nav-tab");
  const pages = document.querySelectorAll(".page");
  function show(name) {
    if (!["home", "check", "about"].includes(name)) name = "home";
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === name));
    pages.forEach(p => {
      p.classList.toggle("active", p.id === "page-" + name);
    });
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function fromHash() {
    const h = (location.hash || "#home").replace("#", "");
    show(h);
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
}
setupRouter();
async function loadDocTypes() {
  const sel = document.getElementById("doc_type");
  if (!sel) return;
  try {
    const res = await fetch("/api/document/types");
    if (!res.ok) return;
    const types = await res.json();
    for (const t of types) {
      const opt = document.createElement("option");
      opt.value = t.value;
      opt.textContent = t.title;
      sel.appendChild(opt);
    }
  } catch (e) {
    console.warn("[types] не удалось загрузить список типов", e);
  }
}
loadDocTypes();
function renderSamples() {
  const stdEl = document.getElementById("samplesStandard");
  const nonEl = document.getElementById("samplesNonstandard");
  if (!stdEl || !nonEl) return;
  for (const s of SAMPLES) {
    const card = document.createElement("div");
    card.className = "sample-card";
    card.dataset.sampleId = s.id;
    card.innerHTML = `
      <img src="${s.file}" alt="${s.label}" loading="lazy"/>
      <div class="sample-label">${s.label}</div>`;
    card.addEventListener("click", () => loadSample(s));
    (s.group === "standard" ? stdEl : nonEl).appendChild(card);
  }
}
renderSamples();
async function loadSample(sample) {
  try {
    setStatus("загружаю пример…", "busy");
    const res = await fetch(sample.file);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const blob = await res.blob();
    const filename = sample.file.split("/").pop();
    const file = new File([blob], filename, {
      type: blob.type || "image/png",
    });
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    nonstandardCheckbox.checked = sample.group === "nonstandard";
    updateToggleUI();
    updateFile(file);
    setStatus("пример загружен", "");
    location.hash = "#check";
  } catch (e) {
    console.error("[samples] не удалось загрузить пример", e);
    setStatus("не удалось загрузить пример", "err");
  }
}
function updateToggleUI() {
  const isNonstd = nonstandardCheckbox.checked;
  if (isNonstd) {
    formatHint.textContent = "Нестандартный — поля распознаются через LLM, подпись и печать — по форме";
    toggleState.textContent = "Нестандарт";
    toggleState.classList.add("active");
  } else {
    formatHint.textContent = "Стандартный — поля распознаются по меткам";
    toggleState.textContent = "Стандарт";
    toggleState.classList.remove("active");
  }
  let row = document.getElementById("highlightToggleRow");
  if (!row) {
    const always = document.getElementById("alwaysHighlight");
    if (always) row = always.closest(".toggle-row");
  }
  if (row) {
    if (isNonstd) {
      row.style.setProperty("display", "none", "important");
    } else {
      row.style.removeProperty("display");
    }
  }
}
nonstandardCheckbox.addEventListener("change", updateToggleUI);
updateToggleUI();
function updateAlwaysHighlightUI() {
  if (alwaysHighlight.checked) {
    highlightModeState.textContent = "Все поля";
    highlightModeState.classList.add("active");
    highlightHint.textContent = "Подсветить все найденные поля";
  } else {
    highlightModeState.textContent = "По проблеме";
    highlightModeState.classList.remove("active");
    highlightHint.textContent = "Только проблемные поля";
  }
}
alwaysHighlight.addEventListener("change", () => {
  updateAlwaysHighlightUI();
  if (lastFile && lastAnalyzeResult) {
    maybeShowHighlight(lastAnalyzeResult, lastFile);
  }
});
updateAlwaysHighlightUI();
function showEmpty() {
  if (empty) empty.classList.remove("hidden");
}
function hideEmpty() {
  if (empty) empty.classList.add("hidden");
}
if (resetBtn) {
  resetBtn.addEventListener("click", () => {
    fileInput.value = "";
    dropFile.textContent = "";
    dropzone.classList.remove("has-file");
    preview.classList.add("hidden");
    highlightCard.classList.add("hidden");
    stages.classList.add("hidden");
    result.classList.add("hidden");
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    if (highlightUrl) { URL.revokeObjectURL(highlightUrl); highlightUrl = null; }
    previewBody.innerHTML = "";
    highlightImg.removeAttribute("src");
    lastAnalyzeResult = null;
    lastFile = null;
    resetBtn.classList.add("hidden");
    showEmpty();
    setStatus("готов");
  });
}
["dragenter", "dragover"].forEach(e =>
  dropzone.addEventListener(e, ev => { ev.preventDefault(); dropzone.classList.add("drag"); })
);
["dragleave", "drop"].forEach(e =>
  dropzone.addEventListener(e, ev => { ev.preventDefault(); dropzone.classList.remove("drag"); })
);
dropzone.addEventListener("drop", ev => {
  const f = ev.dataTransfer.files[0];
  if (f) { fileInput.files = ev.dataTransfer.files; updateFile(f); }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) updateFile(fileInput.files[0]);
});
function updateFile(f) {
  dropFile.textContent = f.name;
  dropzone.classList.add("has-file");
  showPreview(f);
  highlightCard.classList.add("hidden");
  if (highlightUrl) { URL.revokeObjectURL(highlightUrl); highlightUrl = null; }
  lastAnalyzeResult = null;
  lastFile = null;
  if (resetBtn) resetBtn.classList.remove("hidden");
  hideEmpty();
}
function showPreview(f) {
  preview.classList.remove("hidden");
  previewBody.innerHTML = "";
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(f);
  if (f.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = previewUrl;
    previewBody.appendChild(img);
  } else if (f.type === "application/pdf") {
    const iframe = document.createElement("iframe");
    iframe.src = previewUrl;
    previewBody.appendChild(iframe);
  }
}
function setStage(name, state) {
  const el = stages.querySelector(`[data-stage="${name}"]`);
  if (!el) return;
  el.classList.remove("active", "done");
  if (state) el.classList.add(state);
}
function animateStages() {
  const seq = ["read", "ocr", "fields", "rules", "answer"];
  let i = 0;
  const t = setInterval(() => {
    if (i > 0) setStage(seq[i - 1], "done");
    if (i < seq.length) { setStage(seq[i], "active"); i++; }
    else clearInterval(t);
  }, 320);
  return t;
}
function setStatus(text, cls = "") {
  statusEl.className = "status " + cls;
  statusEl.innerHTML = `<span class="dot-ind"></span> ${text}`;
}
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".tab-panel").forEach(p => {
      p.classList.toggle("active", p.dataset.panel === name);
    });
  });
});
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!fileInput.files[0]) { setStatus("файл не выбран", "err"); return; }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  fd.append("question", document.getElementById("question").value);
  const dt = document.getElementById("doc_type").value;
  if (dt) fd.append("doc_type", dt);
  const nonstd = nonstandardCheckbox.checked;
  fd.append("use_llm", nonstd ? "1" : "0");
  fd.append("marks_mode", nonstd ? "loose" : "strict");
  hideEmpty();
  result.classList.add("hidden");
  highlightCard.classList.add("hidden");
  stages.classList.remove("hidden");
  setStatus(nonstd ? "обработка (LLM)…" : "обработка…", "busy");
  const stageTimer = animateStages();
  try {
    const res = await fetch("/api/document/analyze", { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const r = await res.json();
    clearInterval(stageTimer);
    ["read", "ocr", "fields", "rules", "answer"].forEach(s => setStage(s, "done"));
    setTimeout(() => stages.classList.add("hidden"), 300);
    renderResult(r);
    setStatus("готово");
    lastAnalyzeResult = r;
    lastFile = fileInput.files[0];
    maybeShowHighlight(r, lastFile);
    if (resetBtn) resetBtn.classList.remove("hidden");
  } catch (err) {
    clearInterval(stageTimer);
    stages.classList.add("hidden");
    setStatus("ошибка", "err");
    result.classList.remove("hidden");
    result.innerHTML = `<div class="answer err">Ошибка: ${err.message}</div>`;
    if (resetBtn) resetBtn.classList.remove("hidden");
  }
});
function maybeShowHighlight(result, file) {
  if (!file || !result || !result.doc_type) return;
  const hasProblems = result.validation &&
                      result.validation.status === "missing_fields";
  const mode = alwaysHighlight.checked ? "all" : "problems";
  if (mode === "problems" && !hasProblems) {
    highlightCard.classList.add("hidden");
    return;
  }
  loadHighlightImage(file, result.doc_type, mode);
}
async function loadHighlightImage(file, docType, mode) {
  highlightCard.classList.remove("hidden");
  if (highlightUrl) { URL.revokeObjectURL(highlightUrl); highlightUrl = null; }
  highlightImg.removeAttribute("src");
  highlightImg.alt = "Загружаю подсветку…";
  try {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_type", docType);
    fd.append("mode", mode);
    const res = await fetch("/api/document/highlight?_t=" + Date.now(), {
      method: "POST",
      body: fd,
    });
    if (res.status === 404) {
      highlightCard.classList.add("hidden");
      return;
    }
    if (!res.ok) {
      console.warn("[highlight] API error:", res.status);
      highlightCard.classList.add("hidden");
      return;
    }
    const blob = await res.blob();
    highlightUrl = URL.createObjectURL(blob);
    highlightImg.src = highlightUrl;
    highlightImg.alt = "Подсветка полей";
  } catch (e) {
    console.error("[highlight] fetch error:", e);
    highlightCard.classList.add("hidden");
  }
}
function renderResult(r) {
  result.classList.remove("hidden");
  const typeLabel = TYPE_LABEL[r.doc_type] || r.doc_type;
  const auto = r.doc_type_auto ? '<span class="auto">авто</span>' : "";
  document.getElementById("typeBadge").innerHTML = `📄 ${typeLabel} ${auto}`;
  const fields = document.getElementById("fields");
  fields.innerHTML = "";
  for (const [key, val] of Object.entries(r.fields)) {
    const label = FIELD_LABEL[key] || key;
    let icon = "•", cls = "", display = val;
    if (typeof val === "boolean") {
      if (val) { icon = "✅"; cls = "flag-true"; display = "есть"; }
      else { icon = "❌"; cls = "flag-false"; display = "нет"; }
    } else if (val === "не найдено" || !val) {
      icon = "❌"; cls = "miss"; display = "не найдено";
    } else {
      icon = "✅";
    }
    fields.insertAdjacentHTML("beforeend", `
      <div class="field-row ${cls}">
        <div class="icon">${icon}</div>
        <div class="label">${label}</div>
        <div class="value">${escapeHtml(String(display))}</div>
      </div>`);
  }
  const v = r.validation;
  const verdict = document.getElementById("verdict");
  if (v.status === "document_ok") {
    verdict.className = "verdict ok";
    verdict.innerHTML = `Документ содержит все обязательные сведения.<span class="src">${v.sources.join(" · ")}</span>`;
  } else {
    verdict.className = "verdict warn";
    const miss = v.missing_fields.map(k => FIELD_LABEL[k] || k).join(", ");
    verdict.innerHTML = `Не хватает: ${miss}<span class="src">Основание: ${v.sources.join(" · ")}</span>`;
  }
  const answer = document.getElementById("answer");
  if (r.answer) {
    let cls = "ok";
    if (!r.answer.answerable) cls = "err";
    else if (r.answer.value === "missing_fields") cls = "warn";
    answer.className = "answer " + cls;
    answer.innerHTML = `${escapeHtml(r.answer.answer)}
      ${r.answer.sources.length ? `<span class="src">${r.answer.sources.join(" · ")}</span>` : ""}`;
  } else {
    answer.className = "answer";
    answer.textContent = "Вопрос не задан.";
  }
  document.getElementById("rawText").textContent = r.text || "";
}
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}