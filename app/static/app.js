const form = document.getElementById("form");
const fileInput = document.getElementById("file");
const dropzone = document.getElementById("dropzone");
const dropFile = document.getElementById("dropFile");
const stages = document.getElementById("stages");
const result = document.getElementById("result");
const empty = document.getElementById("empty");
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
const TYPE_LABEL = {
  study_certificate: "Справка об обучении",
  academic_leave_application: "Заявление на академический отпуск",
  internship_certificate: "Справка о практике",
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
  signature_present: "Подпись",
  seal_present: "Печать",
};
let previewUrl = null;
let highlightUrl = null;
let lastAnalyzeResult = null;
let lastFile = null;
function updateToggleUI() {
  if (nonstandardCheckbox.checked) {
    formatHint.textContent = "Нестандартный — поля распознаются через LLM, подпись и печать — по форме";
    toggleState.textContent = "Нестандарт";
    toggleState.classList.add("active");
  } else {
    formatHint.textContent = "Стандартный — поля распознаются по меткам";
    toggleState.textContent = "Стандарт";
    toggleState.classList.remove("active");
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
  empty.classList.add("hidden");
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
  } catch (err) {
    clearInterval(stageTimer);
    stages.classList.add("hidden");
    setStatus("ошибка", "err");
    result.classList.remove("hidden");
    result.innerHTML = `<div class="answer err">Ошибка: ${err.message}</div>`;
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
  console.log("[highlight] mode:", mode, "docType:", docType);
  try {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_type", docType);
    fd.append("mode", mode);
    const res = await fetch("/api/document/highlight?_t=" + Date.now(), {
      method: "POST",
      body: fd,
    });
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