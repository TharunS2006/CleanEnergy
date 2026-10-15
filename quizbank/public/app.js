// Plain JavaScript, no framework. Talks to the REST API with fetch().
let token = localStorage.getItem("token");
let user = null;
let qpage = 1;
let timerHandle = null;
const $ = (id) => document.getElementById(id);
const view = () => $("view");

async function api(path, method = "GET", body = null, raw = false) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch("/api" + path, { method, headers, body: body ? JSON.stringify(body) : null });
  if (res.status === 204) return null;
  if (raw && res.ok) return res;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = data.detail || "Something went wrong";
    if (Array.isArray(msg)) msg = msg.map((e) => e.loc[e.loc.length - 1] + ": " + e.msg).join("; ");
    throw new Error(msg);
  }
  return data;
}
function say(text, ok) { $("msg").textContent = text || ""; $("msg").className = "msg" + (ok ? " ok" : ""); }
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------------------------------------------------------------- login
$("login-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const r = await api("/login", "POST", { email: $("l-email").value, password: $("l-pass").value });
    token = r.token; localStorage.setItem("token", token); start();
  } catch (err) { $("login-msg").textContent = err.message; }
};
$("reg-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/register", "POST", { name: $("r-name").value, email: $("r-email").value, password: $("r-pass").value, role: $("r-role").value });
    $("login-msg").className = "msg ok"; $("login-msg").textContent = "Registered. You can login now.";
  } catch (err) { $("login-msg").className = "msg"; $("login-msg").textContent = err.message; }
};
function logout() { localStorage.removeItem("token"); token = null; location.reload(); }

async function start() {
  try { user = await api("/me"); } catch { localStorage.removeItem("token"); return; }
  $("login-box").hidden = true; $("app").hidden = false;
  $("who").innerHTML = esc(user.name) + " (" + user.role + ") <button class='small' onclick='logout()'>Logout</button>";
  const tabs = user.role === "student"
    ? [["quizzes", "Quizzes"], ["practice", "Practice"], ["revision", "Revision"], ["progress", "My progress"], ["results", "My results"]]
    : [["questions", "Question bank"], ["quizzes", "Quizzes"]].concat(user.role === "admin" ? [["admin", "Admin"]] : []);
  $("tabs").innerHTML = tabs.map(([id, label]) => `<button id="nav-${id}" onclick="show('${id}')">${label}</button>`).join("");
  show(tabs[0][0]);
}
function show(id) {
  clearInterval(timerHandle); say("");
  document.querySelectorAll("nav button").forEach((b) => b.classList.remove("on"));
  if ($("nav-" + id)) $("nav-" + id).classList.add("on");
  ({ questions: pageQuestions, quizzes: pageQuizzes, practice: pagePractice, revision: pageRevision, progress: pageProgress,
     results: pageResults, admin: pageAdmin })[id]();
}

// ---------------------------------------------------------------- confidence picker (used in quizzes and practice)
const confHtml = (name) => `<div class="conf">How sure are you?
  <label style="display:inline"><input type="radio" name="${name}" value="1"> guessing</label>
  <label style="display:inline"><input type="radio" name="${name}" value="2" checked> fairly sure</label>
  <label style="display:inline"><input type="radio" name="${name}" value="3"> certain</label></div>`;
const confOf = (name) => +(document.querySelector(`input[name="${name}"]:checked`) || { value: 2 }).value;
const optionsHtml = (q, name) => q.options.map((o, i) => `<label><input type="radio" name="${name}" value="${o.key}"> ${"ABCD"[i]}. ${esc(o.text)}</label>`).join("");
const letterOf = (q, key) => (key ? "ABCD"[q.options.findIndex((o) => o.key === key)] : "-");

// ---------------------------------------------------------------- question bank (teacher / admin)
async function pageQuestions() {
  view().innerHTML = `<h2>Question bank</h2>
    <form id="filter-form" class="row"><input id="f-subject" placeholder="Subject"><input id="f-topic" placeholder="Topic">
      <select id="f-diff"><option value="">Any level</option><option>easy</option><option>medium</option><option>hard</option></select>
      <input id="f-search" placeholder="Search text"><button>Filter</button></form>
    <table id="q-table"></table>
    <div class="row"><button id="prev">Previous</button> <span id="page-info"></span> <button id="next">Next</button></div>
    <h3 id="q-form-title">Add a question</h3>
    <form id="q-form"><input id="q-id" type="hidden">
      <div class="row"><input id="q-subject" placeholder="Subject" required><input id="q-topic" placeholder="Topic" required>
        <select id="q-diff"><option>easy</option><option>medium</option><option>hard</option></select></div>
      <textarea id="q-text" placeholder="Question text" required></textarea>
      <input id="q-a" placeholder="Option A" required><input id="q-b" placeholder="Option B" required>
      <input id="q-c" placeholder="Option C" required><input id="q-d" placeholder="Option D" required>
      <label>Correct answer <select id="q-ans"><option>a</option><option>b</option><option>c</option><option>d</option></select></label>
      <textarea id="q-expl" placeholder="Explanation shown to the student after answering (why is it correct?)"></textarea>
      <button>Save question</button> <button type="button" id="q-cancel">Clear</button></form>
    <h3>Import many questions from a CSV file</h3>
    <p class="note">Columns: subject, topic, difficulty, text, opt_a, opt_b, opt_c, opt_d, answer, explanation</p>
    <input type="file" id="csv-file" accept=".csv"> <button id="csv-go">Import</button> <div id="csv-result" class="note"></div>`;
  $("filter-form").onsubmit = (e) => { e.preventDefault(); qpage = 1; loadQuestions(); };
  $("prev").onclick = () => { qpage--; loadQuestions(); };
  $("next").onclick = () => { qpage++; loadQuestions(); };
  $("q-cancel").onclick = clearQForm;
  $("q-form").onsubmit = saveQuestion;
  $("csv-go").onclick = importCsv;
  loadQuestions();
}
async function loadQuestions() {
  const q = new URLSearchParams({ page: qpage, size: 8 });
  [["subject", "f-subject"], ["topic", "f-topic"], ["difficulty", "f-diff"], ["search", "f-search"]].forEach(([k, id]) => { if ($(id).value) q.set(k, $(id).value); });
  try {
    const r = await api("/questions?" + q);
    $("q-table").innerHTML = "<tr><th>ID</th><th>Subject / topic</th><th>Level</th><th>Question</th><th>Ans</th><th></th></tr>" +
      r.items.map((x) => `<tr><td>${x.id}</td><td>${esc(x.subject)} / ${esc(x.topic)}</td><td>${x.difficulty}</td><td>${esc(x.text)}</td><td>${x.answer.toUpperCase()}</td>
        <td><button class="small" onclick='editQuestion(${JSON.stringify(x).replace(/'/g, "&#39;")})'>Edit</button>
        <button class="small red" onclick="delQuestion(${x.id})">Delete</button></td></tr>`).join("");
    $("page-info").textContent = `Page ${r.page} of ${Math.max(1, Math.ceil(r.total / r.size))} (${r.total} questions)`;
    $("prev").disabled = qpage <= 1; $("next").disabled = qpage * r.size >= r.total;
  } catch (err) { say(err.message); }
}
function editQuestion(x) {
  $("q-form-title").textContent = "Edit question " + x.id;
  $("q-id").value = x.id; $("q-subject").value = x.subject; $("q-topic").value = x.topic; $("q-diff").value = x.difficulty;
  $("q-text").value = x.text; $("q-a").value = x.opt_a; $("q-b").value = x.opt_b; $("q-c").value = x.opt_c; $("q-d").value = x.opt_d;
  $("q-ans").value = x.answer; $("q-expl").value = x.explanation || "";
  $("q-form").scrollIntoView();
}
function clearQForm() { $("q-form").reset(); $("q-id").value = ""; $("q-form-title").textContent = "Add a question"; }
async function saveQuestion(e) {
  e.preventDefault();
  const body = { subject: $("q-subject").value, topic: $("q-topic").value, difficulty: $("q-diff").value, text: $("q-text").value,
    opt_a: $("q-a").value, opt_b: $("q-b").value, opt_c: $("q-c").value, opt_d: $("q-d").value, answer: $("q-ans").value, explanation: $("q-expl").value };
  try {
    if ($("q-id").value) await api("/questions/" + $("q-id").value, "PUT", body); else await api("/questions", "POST", body);
    say("Question saved", true); clearQForm(); loadQuestions();
  } catch (err) { say(err.message); }
}
async function delQuestion(id) {
  if (!confirm("Delete question " + id + "?")) return;
  try { await api("/questions/" + id, "DELETE"); say("Deleted", true); loadQuestions(); } catch (err) { say(err.message); }
}
async function importCsv() {
  const f = $("csv-file").files[0];
  if (!f) { say("Choose a CSV file first"); return; }
  try {
    const r = await api("/questions/import", "POST", { csv: await f.text() });
    $("csv-result").innerHTML = `Added ${r.added} questions.` + (r.errors.length ? " Problems:<br>" + r.errors.map((x) => `line ${x.line}: ${esc(x.problem)}`).join("<br>") : "");
    loadQuestions();
  } catch (err) { say(err.message); }
}

// ---------------------------------------------------------------- quizzes
async function pageQuizzes() {
  const staff = user.role !== "student";
  view().innerHTML = `<h2>Quizzes</h2><table id="quiz-table"></table>` + (staff ? `<h3>Make a random quiz</h3>
    <form id="rq-form" class="row"><input id="rq-title" placeholder="Quiz title" required><input id="rq-subject" placeholder="Subject" required>
      <input id="rq-topic" placeholder="Topic (optional)"><select id="rq-diff"><option value="">Any level</option><option>easy</option><option>medium</option><option>hard</option></select>
      <input id="rq-count" type="number" min="1" value="5" title="Number of questions"><input id="rq-min" type="number" min="1" value="10" title="Minutes">
      <input id="rq-att" type="number" min="1" value="2" title="Attempts allowed"><button>Create</button></form>
    <p class="note">Fields: title, subject, topic, level, number of questions, minutes, attempts allowed.</p>` : "");
  try {
    const list = await api("/quizzes");
    $("quiz-table").innerHTML = "<tr><th>ID</th><th>Title</th><th>Subject</th><th>Questions</th><th>Minutes</th><th>Attempts</th><th></th></tr>" +
      list.map((x) => `<tr><td>${x.id}</td><td>${esc(x.title)}</td><td>${esc(x.subject)}</td><td>${x.questions}</td><td>${x.minutes}</td>
        <td>${staff ? x.max_attempts : x.my_attempts + " of " + x.max_attempts}</td><td>` +
        (staff ? `<button class="small" onclick="quizResults(${x.id})">Results</button> <button class="small" onclick="quizAnalysis(${x.id})">Item analysis</button>
                  <button class="small" onclick="leaderboard(${x.id})">Leaderboard</button> <button class="small red" onclick="delQuiz(${x.id})">Delete</button>`
               : `<button class="small" ${x.my_attempts >= x.max_attempts ? "disabled" : ""} onclick="takeQuiz(${x.id})">Take quiz</button>
                  <button class="small" onclick="leaderboard(${x.id})">Leaderboard</button>`) + "</td></tr>").join("");
  } catch (err) { say(err.message); }
  if (staff) $("rq-form").onsubmit = async (e) => {
    e.preventDefault();
    const body = { title: $("rq-title").value, subject: $("rq-subject").value, minutes: +$("rq-min").value, count: +$("rq-count").value, max_attempts: +$("rq-att").value };
    if ($("rq-topic").value) body.topic = $("rq-topic").value;
    if ($("rq-diff").value) body.difficulty = $("rq-diff").value;
    try { await api("/quizzes/random", "POST", body); say("Quiz created", true); pageQuizzes(); } catch (err) { say(err.message); }
  };
}
async function delQuiz(id) {
  if (!confirm("Delete quiz " + id + "?")) return;
  try { await api("/quizzes/" + id, "DELETE"); pageQuizzes(); } catch (err) { say(err.message); }
}

// ---------------------------------------------------------------- taking a quiz (timer comes from the server)
async function takeQuiz(id) {
  try {
    const p = await api("/quizzes/" + id + "/start", "POST");
    view().innerHTML = `<h2>${esc(p.title)} (${esc(p.subject)})</h2><p class="timer" id="timer"></p>
      <p class="note">The timer runs on the server. Questions and options are shuffled for each student. Tell us how sure you are about each answer.</p>
      <form id="take-form">` + p.questions.map((q, i) => `<div class="question"><b>${i + 1}. ${esc(q.text)}</b><br>${optionsHtml(q, "q" + q.id)}${confHtml("c" + q.id)}</div>`).join("") +
      `<button>Submit quiz</button></form><div id="take-result"></div>`;
    $("take-form").onsubmit = (e) => { e.preventDefault(); submitQuiz(p); };
    let left = p.seconds_left;
    const tick = () => {
      $("timer").textContent = "Time left: " + Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
      if (left-- <= 0) { clearInterval(timerHandle); submitQuiz(p); }
    };
    tick(); timerHandle = setInterval(tick, 1000);
  } catch (err) { say(err.message); }
}
async function submitQuiz(p) {
  clearInterval(timerHandle);
  const answers = {};
  p.questions.forEach((q) => {
    const picked = document.querySelector(`input[name=q${q.id}]:checked`);
    if (picked) answers[q.id] = { choice: picked.value, confidence: confOf("c" + q.id) };
  });
  try {
    const r = await api("/attempts/" + p.attempt_id + "/submit", "POST", { answers });
    const byId = Object.fromEntries(p.questions.map((q) => [q.id, q]));
    view().innerHTML = `<h2>You scored ${r.score} out of ${r.total} (${r.percent}%)</h2>` +
      (r.late ? `<p class="warn">Submitted after the time limit, so this attempt is kept out of the leaderboard.</p>` : "") +
      (r.calibration !== null ? `<p>Knowledge calibration: <b>${r.calibration} / 100</b>
         <span class="note">(how well your confidence matched your results; 100 means you were sure only when you were right)</span></p>` : "") +
      r.review.map((x, i) => `<div class="question ${x.correct ? "right" : "wrong"}"><b>${i + 1}. ${esc(x.text)}</b><br>
        Your answer: ${letterOf(byId[x.question_id], x.your_answer)} | Correct answer: ${letterOf(byId[x.question_id], x.correct_answer)}
        ${x.confidence ? ` | You said: ${["", "guessing", "fairly sure", "certain"][x.confidence]}` : ""}
        ${x.misconception ? `<br><span class="warn">You were certain and wrong. This is worth revising, it has been added to your revision list.</span>` : ""}
        ${x.explanation ? `<br><span class="note">Why: ${esc(x.explanation)}</span>` : ""}</div>`).join("") +
      `<button onclick="show('quizzes')">Back to quizzes</button>`;
  } catch (err) { say(err.message); }
}

// ---------------------------------------------------------------- practice (adaptive) and revision (spaced repetition)
async function pagePractice() {
  let subjects = [];
  try { subjects = await api("/subjects"); } catch (err) { say(err.message); }
  const names = [...new Set(subjects.map((s) => s.subject))];
  view().innerHTML = `<h2>Adaptive practice</h2>
    <p class="note">Questions come one at a time. Difficulty follows your recent answers, and when you do not pick a topic we steer you to your weakest one.</p>
    <div class="row">Subject <select id="pr-subject">${names.map((n) => `<option>${esc(n)}</option>`).join("")}</select>
    Topic <select id="pr-topic"></select> <button id="pr-go">Next question</button></div><div id="pr-box"></div>`;
  const fill = () => { $("pr-topic").innerHTML = `<option value="">Weakest first</option>` + subjects.filter((s) => s.subject === $("pr-subject").value).map((s) => `<option>${esc(s.topic)}</option>`).join(""); };
  $("pr-subject").onchange = fill; fill();
  $("pr-go").onclick = nextPractice;
}
function showQuestionCard(q, onAnswer, extra) {
  $("pr-box").innerHTML = `<div class="question"><b>${esc(q.text)}</b> <span class="note">(${esc(q.subject || "")} ${q.topic ? "/ " + esc(q.topic) : ""})</span><br>
    ${optionsHtml(q, "pq")}${confHtml("pc")}<button id="pq-go">Check answer</button> <span class="note">${extra || ""}</span></div><div id="pq-out"></div>`;
  $("pq-go").onclick = async () => {
    const picked = document.querySelector("input[name=pq]:checked");
    if (!picked) { say("Pick an option first"); return; }
    say("");
    try {
      const r = await api("/practice/answer", "POST", { question_id: q.id, choice: picked.value, confidence: confOf("pc") });
      $("pq-go").disabled = true;
      $("pq-out").innerHTML = `<div class="question ${r.correct ? "right" : "wrong"}"><b>${r.correct ? "Correct" : "Not quite"}</b>. Right answer: ${letterOf(q, r.correct_answer)}.
        ${r.misconception ? `<br><span class="warn">You were certain, so this is probably a misconception. It will come back for revision.</span>` : ""}
        ${r.explanation ? `<br><span class="note">Why: ${esc(r.explanation)}</span>` : ""}</div>`;
      if (onAnswer) onAnswer();
    } catch (err) { say(err.message); }
  };
}
async function nextPractice() {
  try {
    const q = await api("/practice/next?subject=" + encodeURIComponent($("pr-subject").value) + ($("pr-topic").value ? "&topic=" + encodeURIComponent($("pr-topic").value) : ""));
    showQuestionCard(q, null, q.why_this_question);
  } catch (err) { say(err.message); }
}
async function pageRevision() {
  try {
    const r = await api("/revision/due");
    view().innerHTML = `<h2>Revision</h2><p class="note">Questions you got wrong come back after 1, 2, 4, 8 and 16 days (spaced repetition). Answer them correctly each time and they leave your list.</p>
      <p><b>${r.due}</b> due today, ${r.in_queue} waiting in total.</p><div id="pr-box"></div>`;
    let i = 0;
    const next = () => {
      if (i >= r.questions.length) { $("pr-box").innerHTML = "<p>Nothing more due today. Well done.</p>"; return; }
      const q = r.questions[i++];
      showQuestionCard(q, () => { $("pq-go").insertAdjacentHTML("afterend", ` <button id="rv-next">Next</button>`); $("rv-next").onclick = next; }, "Box " + q.box + " of 5");
    };
    next();
  } catch (err) { say(err.message); }
}

// ---------------------------------------------------------------- progress and results (student)
async function pageProgress() {
  try {
    const m = await api("/me/mastery");
    view().innerHTML = `<h2>My progress</h2>
      <p>Practice answers: <b>${m.practice_answers}</b> | Revision due today: <b>${m.revision_due}</b> |
      Knowledge calibration (last quizzes): <b>${m.calibration_average ?? "no data yet"}</b></p>
      ${m.focus_on.length ? `<h3>Focus on these topics next</h3><ul>${m.focus_on.map((t) => `<li>${esc(t.subject)} / ${esc(t.topic)}: ${t.percent}%</li>`).join("")}</ul>` : ""}
      <h3>Topic mastery</h3><table><tr><th>Subject / topic</th><th>Answered</th><th>Mastery</th><th></th></tr>` +
      m.topics.map((t) => `<tr><td>${esc(t.subject)} / ${esc(t.topic)}</td><td>${t.answered}</td>
        <td><span class="bar ${t.level}"><span style="width:${t.percent}%"></span></span> ${t.percent}%</td><td>${t.level}</td></tr>`).join("") + "</table>" +
      `<p class="note">Mastery is calculated from your practice answers and finished quizzes together. Topics with fewer than 3 answers show "not enough data".</p>`;
  } catch (err) { say(err.message); }
}
async function pageResults() {
  try {
    const list = await api("/attempts/mine");
    view().innerHTML = "<h2>My results</h2><table><tr><th>Quiz</th><th>Score</th><th>Calibration</th><th>Date</th></tr>" +
      list.map((x) => `<tr><td>${esc(x.title)}${x.late ? " (late)" : ""}</td><td>${x.score} / ${x.total}</td><td>${x.calibration ?? "-"}</td><td>${x.submitted_at || ""}</td></tr>`).join("") + "</table>";
  } catch (err) { say(err.message); }
}

// ---------------------------------------------------------------- teacher views
async function quizResults(id) {
  try {
    const r = await api("/quizzes/" + id + "/results");
    view().innerHTML = `<h2>Results: ${esc(r.quiz)}</h2><p>Attempts: ${r.attempts.length} | Average (on-time attempts): ${r.average_percent}%
      <button class="small" onclick="downloadCsv(${id})">Download CSV</button></p>
      <table><tr><th>Student</th><th>Score</th><th>Calibration</th><th>Late</th><th>Submitted</th></tr>` +
      r.attempts.map((x) => `<tr><td>${esc(x.name)}</td><td>${x.score} / ${x.total}</td><td>${x.calibration ?? "-"}</td><td>${x.late ? "yes" : ""}</td><td>${x.submitted_at || ""}</td></tr>`).join("") + "</table>" +
      "<h3>Hardest questions</h3><table><tr><th>Question</th><th>Answered right</th></tr>" +
      r.hardest_questions.map((x) => `<tr><td>${esc(x.text)}</td><td>${x.right_count} of ${x.times}</td></tr>`).join("") + "</table>" +
      `<button onclick="show('quizzes')">Back</button>`;
  } catch (err) { say(err.message); }
}
async function downloadCsv(id) {
  const res = await api("/quizzes/" + id + "/results.csv", "GET", null, true);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(await res.blob()); a.download = "quiz-" + id + "-results.csv"; a.click();
}
async function quizAnalysis(id) {
  try {
    const r = await api("/quizzes/" + id + "/analysis");
    view().innerHTML = `<h2>Item analysis: ${esc(r.quiz)}</h2><p class="note">${r.students} on-time attempts. Difficulty index = share of students who got the question right.
      Discrimination = how much better the top 27% did than the bottom 27% (needs at least 4 students; above 0.3 is good).</p>
      <table><tr><th>Question</th><th>Labelled</th><th>Difficulty index</th><th>Discrimination</th><th>Most chosen wrong option</th><th>Advice</th></tr>` +
      r.items.map((x) => `<tr><td>${esc(x.text)}</td><td>${x.labelled}</td><td>${x.difficulty_index ?? "-"}</td><td>${x.discrimination ?? "-"}</td>
        <td>${x.most_chosen_wrong_option ? x.most_chosen_wrong_option.toUpperCase() : "-"}</td><td>${x.flags.map(esc).join("<br>") || "fine"}</td></tr>`).join("") +
      `</table><button onclick="show('quizzes')">Back</button>`;
  } catch (err) { say(err.message); }
}
async function leaderboard(id) {
  try {
    const r = await api("/quizzes/" + id + "/leaderboard");
    view().innerHTML = `<h2>Leaderboard</h2><p class="note">Best on-time attempt per student. Ties are broken by time taken.${r.your_rank ? " Your rank: " + r.your_rank + " of " + r.players + "." : ""}</p>
      <table><tr><th>Rank</th><th>Student</th><th>Score</th><th>Time</th></tr>` +
      r.top.map((x) => `<tr ${x.you ? 'style="background:#e7f4e7"' : ""}><td>${x.rank}</td><td>${esc(x.name)}</td><td>${x.score} / ${x.total}</td><td>${Math.floor(x.seconds / 60)}m ${x.seconds % 60}s</td></tr>`).join("") +
      `</table><button onclick="show('quizzes')">Back</button>`;
  } catch (err) { say(err.message); }
}

// ---------------------------------------------------------------- admin
async function pageAdmin() {
  try {
    const s = await api("/stats"), users = await api("/users");
    view().innerHTML = `<h2>Overview</h2><p>Users: ${s.users} | Questions: ${s.questions} | Quizzes: ${s.quizzes} | Finished attempts: ${s.attempts} | Practice answers: ${s.practice_answers}</p>
      <h3>Users</h3><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th></th></tr>` +
      users.map((u) => `<tr><td>${u.id}</td><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${u.role}</td>
        <td>${u.id === user.id ? "" : `<button class="small red" onclick="delUser(${u.id})">Delete</button>`}</td></tr>`).join("") + "</table>";
  } catch (err) { say(err.message); }
}
async function delUser(id) {
  if (!confirm("Delete user " + id + "?")) return;
  try { await api("/users/" + id, "DELETE"); pageAdmin(); } catch (err) { say(err.message); }
}

if (token) start();
