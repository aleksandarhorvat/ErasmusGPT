// ErasmusGPT gold-set annotator. Owner: Person B, used by Person A.
// Plain file:// page. No build step, no server, no network. See docs/05-evaluation.md.

const S = {
  courses: new Map(),   // course_uid -> {course, programme}
  rows: [],             // {home_uid, host_uid, llm_label, label, checked}
  i: 0,
  handle: null,         // FileSystemFileHandle, when the browser supports it
  name: "gold_pairs.csv",
  keepLlm: false,       // a half from scripts/split_gold.py: write the proposal back too
  loadedJson: [],
};

const $ = (id) => document.getElementById(id);
const hasFS = typeof window.showOpenFilePicker === "function";

// ---------- csv ----------------------------------------------------------

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else { quoted = false; }
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  if (!rows.length) return [];
  const head = rows.shift().map((h) => h.trim());
  return rows
    .filter((r) => r.some((v) => v.trim() !== ""))
    .map((r) => Object.fromEntries(head.map((h, j) => [h, (r[j] ?? "").trim()])));
}

function quote(value) {
  const s = String(value ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv() {
  // gold_pairs.csv has four columns. The halves made by scripts/split_gold.py also keep
  // the model's proposal, so reopening a half-finished file still shows it and still
  // counts corrections; they go back into gold_pairs.csv via scripts/merge_gold.py.
  const out = [S.keepLlm
    ? "home_uid,host_uid,llm_label,llm_reason,label,checked"
    : "home_uid,host_uid,label,checked"];
  for (const r of S.rows) {
    const checked = r.checked ? "yes" : "no";
    out.push(S.keepLlm
      ? [r.home_uid, r.host_uid, r.llm_label ?? "", r.llm_reason, r.label, checked].map(quote).join(",")
      : `${r.home_uid},${r.host_uid},${r.label},${checked}`);
  }
  return out.join("\n") + "\n";
}

// ---------- loading ------------------------------------------------------

function loadCurriculum(text, filename) {
  const data = JSON.parse(text);
  const inst = data.institution_id;
  if (!inst || !Array.isArray(data.courses)) throw new Error("not a curriculum file");
  for (const c of data.courses) {
    S.courses.set(`${inst}:${c.code}`, { course: c, programme: data });
  }
  S.loadedJson.push(`${filename} (${data.courses.length} courses)`);
}

function loadPairs(text, filename) {
  const raw = parseCsv(text);
  if (!raw.length) throw new Error("no rows");
  S.rows = raw.map((r) => {
    const llm = r.llm_label !== undefined && r.llm_label !== "" ? Number(r.llm_label) : null;
    const lab = r.label !== undefined && r.label !== "" ? Number(r.label) : llm;
    return {
      home_uid: r.home_uid,
      host_uid: r.host_uid,
      llm_label: llm,
      llm_reason: r.llm_reason || "",
      label: Number.isFinite(lab) ? lab : 0,
      checked: String(r.checked || "").toLowerCase() === "yes",
    };
  });
  S.keepLlm = "llm_label" in raw[0] && "label" in raw[0];
  S.name = filename.replace("llm_prelabels", "gold_pairs");
  restore();
  S.i = Math.max(0, S.rows.findIndex((r) => !r.checked));
  if (S.i < 0) S.i = 0;
}

function renderFiles(err) {
  const el = $("files");
  el.innerHTML = "";
  for (const f of S.loadedJson) el.insertAdjacentHTML("beforeend", `<span>${f}</span>`);
  if (S.rows.length) el.insertAdjacentHTML("beforeend", `<span>${S.name} (${S.rows.length} pairs)</span>`);
  if (err) el.insertAdjacentHTML("beforeend", `<span class="bad">${err}</span>`);
}

function ready() {
  if (!S.rows.length || !S.courses.size) return;
  $("setup").hidden = true;
  $("work").hidden = false;
  ["prev", "jump", "save"].forEach((id) => ($(id).disabled = false));
  draw();
}

async function readFiles(fileList) {
  let err = "";
  for (const f of fileList) {
    try {
      const text = await f.text();
      if (f.name.toLowerCase().endsWith(".json")) loadCurriculum(text, f.name);
      else if (f.name.toLowerCase().endsWith(".csv")) loadPairs(text, f.name);
    } catch (e) { err = `${f.name}: ${e.message}`; }
  }
  renderFiles(err);
  ready();
}

// ---------- drawing ------------------------------------------------------

function courseCard(uid, side) {
  const hit = S.courses.get(uid);
  const who = side === "home" ? "Your course" : "Host course";
  if (!hit) {
    return `<p class="who">${who}</p><h2>${uid}</h2>
            <p class="missing">Not found in the loaded curricula. Load the JSON file that contains it.</p>`;
  }
  const c = hit.course, p = hit.programme;
  const bits = [c.code, `${c.ects} ECTS`];
  if (c.year) bits.push(`year ${c.year}`);
  if (c.semester) bits.push(`semester ${c.semester}`);
  if (c.module) bits.push(c.module);
  let html = `<p class="who">${who} &middot; ${p.institution_name}</p>
    <h2>${esc(c.title)}</h2>
    <p class="meta">${bits.join(" &middot; ")}</p>
    <div class="body">${c.description ? esc(c.description) : '<span class="missing">No description published.</span>'}</div>`;
  if (c.learning_outcomes && c.learning_outcomes.length) {
    html += `<p class="sub">Learning outcomes</p><ul>${c.learning_outcomes.map((o) => `<li>${esc(o)}</li>`).join("")}</ul>`;
  }
  if (c.topics && c.topics.length) {
    html += `<p class="sub">Topics</p><div class="body">${c.topics.map(esc).join(", ")}</div>`;
  }
  return html;
}

function esc(s) {
  return String(s).replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
}

function draw() {
  const r = S.rows[S.i];
  if (!r) return;
  $("cardHome").innerHTML = courseCard(r.home_uid, "home");
  $("cardHost").innerHTML = courseCard(r.host_uid, "host");
  $("pos").textContent = `pair ${S.i + 1} of ${S.rows.length}`;
  $("flagChecked").hidden = !r.checked;
  $("flagCorrected").hidden = !(r.checked && r.llm_label !== null && r.llm_label !== r.label);
  $("proposed").innerHTML = r.llm_label === null
    ? "No proposed label for this pair. Judge it cold."
    : `Proposed <b>${r.llm_label}</b>${r.llm_reason ? " &mdash; " + esc(r.llm_reason) : ""}`;
  for (const b of document.querySelectorAll(".choices button")) {
    b.setAttribute("aria-pressed", String(Number(b.dataset.l) === r.label));
  }
  const done = S.rows.filter((x) => x.checked).length;
  const corr = S.rows.filter((x) => x.checked && x.llm_label !== null && x.llm_label !== x.label).length;
  $("bar").style.width = `${(done / S.rows.length) * 100}%`;
  $("counts").innerHTML = `checked <b>${done}</b>/<b>${S.rows.length}</b> &middot; corrected <b>${corr}</b>`;
  $("prev").disabled = S.i === 0;
  persist();
}

function setLabel(v) {
  const r = S.rows[S.i];
  if (!r) return;
  r.label = v;
  draw();
}

function accept() {
  const r = S.rows[S.i];
  if (!r) return;
  r.checked = true;
  next();
}

function next() {
  if (S.i < S.rows.length - 1) S.i++;
  else toast("That was the last pair. Save the file.");
  draw();
}

function prev() { if (S.i > 0) S.i--; draw(); }

function jumpUnchecked() {
  const from = S.rows.findIndex((r, j) => j > S.i && !r.checked);
  const any = from >= 0 ? from : S.rows.findIndex((r) => !r.checked);
  if (any < 0) { toast("Every pair is checked."); return; }
  S.i = any; draw();
}

// ---------- saving -------------------------------------------------------

function persist() {
  try { localStorage.setItem("erasmusgpt-annotator", JSON.stringify({ name: S.name, rows: S.rows, i: S.i })); }
  catch (e) { /* private window or blocked storage: autosave is a convenience only */ }
}

function restore() {
  try {
    const saved = JSON.parse(localStorage.getItem("erasmusgpt-annotator") || "null");
    if (!saved || saved.name !== S.name || saved.rows.length !== S.rows.length) return;
    const by = new Map(saved.rows.map((r) => [`${r.home_uid}|${r.host_uid}`, r]));
    let restored = 0;
    for (const r of S.rows) {
      const s = by.get(`${r.home_uid}|${r.host_uid}`);
      if (s && s.checked) { r.label = s.label; r.checked = true; restored++; }
    }
    if (restored) toast(`Restored ${restored} checked rows from this browser.`);
  } catch (e) { /* ignore */ }
}

async function save() {
  const csv = toCsv();
  try {
    if (S.handle) {
      const perm = await S.handle.requestPermission({ mode: "readwrite" });
      if (perm !== "granted") throw new Error("permission denied");
      const w = await S.handle.createWritable();
      await w.write(csv); await w.close();
      toast(`Saved to ${S.handle.name}`);
      return;
    }
    if (hasFS) {
      S.handle = await window.showSaveFilePicker({
        suggestedName: S.name,
        types: [{ description: "CSV", accept: { "text/csv": [".csv"] } }],
      });
      const w = await S.handle.createWritable();
      await w.write(csv); await w.close();
      toast(`Saved to ${S.handle.name}. Saving again overwrites it.`);
      return;
    }
  } catch (e) {
    if (e && e.name === "AbortError") return;
    toast("Could not write the file, downloading instead.");
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = S.name;
  a.click();
  URL.revokeObjectURL(a.href);
}

let toastTimer;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
}

// ---------- wiring -------------------------------------------------------

$("fJson").addEventListener("change", (e) => readFiles(e.target.files));
$("fCsv").addEventListener("change", (e) => readFiles(e.target.files));

$("pickCsv").addEventListener("click", async () => {
  if (!hasFS) { toast("This browser cannot save in place. Use the Pairs CSV button."); return; }
  try {
    const [h] = await window.showOpenFilePicker({
      types: [{ description: "CSV", accept: { "text/csv": [".csv"] } }],
    });
    S.handle = h;
    const f = await h.getFile();
    loadPairs(await f.text(), f.name);
    if (f.name.includes("llm_prelabels")) {
      S.handle = null;  // never overwrite the frozen pre-label file
      toast("Loaded the pre-labels. Save will ask where to write gold_pairs.csv.");
    }
    renderFiles("");
    ready();
  } catch (e) { if (e.name !== "AbortError") renderFiles(e.message); }
});

const drop = $("drop");
["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("hot"); }));
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("hot"); }));
drop.addEventListener("drop", (e) => readFiles(e.dataTransfer.files));

document.querySelectorAll(".choices button").forEach((b) =>
  b.addEventListener("click", () => setLabel(Number(b.dataset.l))));
$("accept").addEventListener("click", accept);
$("skip").addEventListener("click", next);
$("prev").addEventListener("click", prev);
$("jump").addEventListener("click", jumpUnchecked);
$("save").addEventListener("click", save);

document.addEventListener("keydown", (e) => {
  if ($("work").hidden) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); return; }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === "0" || e.key === "1" || e.key === "2") { setLabel(Number(e.key)); e.preventDefault(); }
  else if (e.key === "Enter") { accept(); e.preventDefault(); }
  else if (e.key === "ArrowRight") { next(); e.preventDefault(); }
  else if (e.key === "ArrowLeft") { prev(); e.preventDefault(); }
});

window.addEventListener("beforeunload", (e) => {
  if (S.rows.some((r) => r.checked)) { e.preventDefault(); e.returnValue = ""; }
});

$("fsNote").textContent = hasFS
  ? "This browser can write back to the file you opened, so Save overwrites it in place."
  : "This browser cannot write files in place, so Save downloads a new copy of the file. Chrome or Edge can overwrite in place.";
