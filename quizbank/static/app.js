// Plain JavaScript, no framework. Talks to the REST API with fetch().
let token = localStorage.getItem("token");
let user = null;
let page = 1;
let timerHandle = null;

const $ = (id) => document.getElementById(id);

async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch("/api" + path, { method, headers, body: body ? JSON.stringify(body) : null });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = data.detail || "Something went wrong";
    if (Array.isArray(msg)) msg = msg.map((e) => e.loc[e.loc.length - 1] + ": " + e.msg).join("; ");
    throw new Error(msg);
  }
  return data;
}

function say(text, ok) {
  $("msg").textContent = text || "";
  $("msg").className = "msg" + (ok ? " ok" : "");
}

// ---------- login / register ----------
$("login-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const r = await api("/login", "POST", { email: $("l-email").value, password: $("l-pass").value });
    token = r.token;
    localStorage.setItem("token", token);
    start();
  } catch (err) { $("login-msg").textContent = err.message; }
};

$("reg-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/register", "POST", { name: $("r-name").value, email: $("r-email").value, password: $("r-pass").value, role: $("r-role").value });
    $("login-msg").className = "msg ok";
    $("login-msg").textContent = "Registered. You can login now.";
  } catch (err) { $("login-msg").className = "msg"; $("login-msg").textContent = err.message; }
};

function logout() {
  localStorage.removeItem("token");
  token = null;
  location.reload();
}

async function start() {
  try { user = await api("/me"); } catch { return; }
  $("login-box").hidden = true;
  $("app").hidden = false;
  $("who").innerHTML = user.name + " (" + user.role + ") <button class='small' onclick='logout()'>Logout</button>";
  const tabs = [];
  if (user.role !== "student") tabs.push(["questions", "Question bank"]);
  tabs.push(["quizzes", "Quizzes"]);
  if (user.role === "student") tabs.push(["results", "My results"]);
  if (user.role === "admin") tabs.push(["admin", "Admin"]);
  $("tabs").innerHTML = tabs.map(([id, label]) => `<button id="nav-${id}" onclick="show('${id}')">${label}</button>`).join("");
  $("make-quiz").hidden = user.role === "student";
  show(tabs[0][0]);
}

function show(id) {
  clearInterval(timerHandle);
  say("");
  document.querySelectorAll(".tab").forEach((t) => (t.hidden = true));
  document.querySelectorAll("nav button").forEach((b) => b.classList.remove("on"));
  $("tab-" + id).hidden = false;
  const nav = $("nav-" + id);
  if (nav) nav.classList.add("on");
  if (id === "questions") loadQuestions();
  if (id === "quizzes") loadQuizzes();
  if (id === "results") loadMyResults();
  if (id === "admin") loadAdmin();
}

// ---------- question bank ----------
async function loadQuestions() {
  const q = new URLSearchParams({ page, size: 8 });
  if ($("f-subject").value) q.set("subject", $("f-subject").value);
  if ($("f-topic").value) q.set("topic", $("f-topic").value);
  if ($("f-diff").value) q.set("difficulty", $("f-diff").value);
  if ($("f-search").value) q.set("search", $("f-search").value);
  try {
    const r = await api("/questions?" + q);
    $("q-table").innerHTML =
      "<tr><th>ID</th><th>Subject</th><th>Topic</th><th>Level</th><th>Question</th><th>Ans</th><th></th></tr>" +
      r.items.map((x) => `<tr><td>${x.id}</td><td>${x.subject}</td><td>${x.topic}</td><td>${x.difficulty}</td><td>${x.text}</td><td>${x.answer.toUpperCase()}</td>
        <td><button class="small" onclick='editQuestion(${JSON.stringify(x)})'>Edit</button>
            <button class="small red" onclick="delQuestion(${x.id})">Delete</button></td></tr>`).join("");
    $("page-info").textContent = `Page ${r.page} of ${Math.max(1, Math.ceil(r.total / r.size))}  (${r.total} questions)`;
    $("prev").disabled = page <= 1;
    $("next").disabled = page * r.size >= r.total;
  } catch (err) { say(err.message); }
}

$("filter-form").onsubmit = (e) => { e.preventDefault(); page = 1; loadQuestions(); };
$("prev").onclick = () => { page--; loadQuestions(); };
$("next").onclick = () => { page++; loadQuestions(); };

function editQuestion(x) {
  $("q-form-title").textContent = "Edit question " + x.id;
  $("q-id").value = x.id; $("q-subject").value = x.subject; $("q-topic").value = x.topic; $("q-diff").value = x.difficulty;
  $("q-text").value = x.text; $("q-a").value = x.opt_a; $("q-b").value = x.opt_b; $("q-c").value = x.opt_c; $("q-d").value = x.opt_d;
  $("q-ans").value = x.answer;
  window.scrollTo(0, document.body.scrollHeight);
}

function clearForm() {
  $("q-form").reset(); $("q-id").value = ""; $("q-form-title").textContent = "Add a question";
}
$("q-cancel").onclick = clearForm;

$("q-form").onsubmit = async (e) => {
  e.preventDefault();
  const body = { subject: $("q-subject").value, topic: $("q-topic").value, difficulty: $("q-diff").value, text: $("q-text").value,
                 opt_a: $("q-a").value, opt_b: $("q-b").value, opt_c: $("q-c").value, opt_d: $("q-d").value, answer: $("q-ans").value };
  try {
    if ($("q-id").value) await api("/questions/" + $("q-id").value, "PUT", body);
    else await api("/questions", "POST", body);
    say("Question saved", true);
    clearForm();
    loadQuestions();
  } catch (err) { say(err.message); }
};

async function delQuestion(id) {
  if (!confirm("Delete question " + id + "?")) return;
  try { await api("/questions/" + id, "DELETE"); say("Deleted", true); loadQuestions(); } catch (err) { say(err.message); }
}

// ---------- quizzes ----------
async function loadQuizzes() {
  try {
    const list = await api("/quizzes");
    const staff = user.role !== "student";
    $("quiz-table").innerHTML =
      "<tr><th>ID</th><th>Title</th><th>Subject</th><th>Questions</th><th>Minutes</th><th></th></tr>" +
      list.map((x) => `<tr><td>${x.id}</td><td>${x.title}</td><td>${x.subject}</td><td>${x.questions}</td><td>${x.minutes}</td><td>` +
        (staff ? `<button class="small" onclick="quizResults(${x.id})">Results</button> <button class="small red" onclick="delQuiz(${x.id})">Delete</button>`
               : `<button class="small" onclick="takeQuiz(${x.id})">Take quiz</button>`) + "</td></tr>").join("");
  } catch (err) { say(err.message); }
}

$("rq-form").onsubmit = async (e) => {
  e.preventDefault();
  const body = { title: $("rq-title").value, subject: $("rq-subject").value, minutes: +$("rq-min").value, count: +$("rq-count").value };
  if ($("rq-topic").value) body.topic = $("rq-topic").value;
  if ($("rq-diff").value) body.difficulty = $("rq-diff").value;
  try { await api("/quizzes/random", "POST", body); say("Quiz created", true); loadQuizzes(); } catch (err) { say(err.message); }
};

async function delQuiz(id) {
  if (!confirm("Delete quiz " + id + "?")) return;
  try { await api("/quizzes/" + id, "DELETE"); loadQuizzes(); } catch (err) { say(err.message); }
}

// ---------- taking a quiz ----------
async function takeQuiz(id) {
  try {
    const quiz = await api("/quizzes/" + id);
    document.querySelectorAll(".tab").forEach((t) => (t.hidden = true));
    $("tab-take").hidden = false;
    $("take-result").innerHTML = "";
    $("take-title").textContent = quiz.title + " (" + quiz.subject + ")";
    $("take-form").innerHTML = quiz.questions.map((q, i) => `<div class="question" id="qbox-${q.id}"><b>${i + 1}. ${q.text}</b><br>` +
      ["a", "b", "c", "d"].map((o) => `<label><input type="radio" name="q${q.id}" value="${o}"> ${o.toUpperCase()}. ${q["opt_" + o]}</label>`).join("") + "</div>").join("") +
      "<button>Submit quiz</button>";
    $("take-form").onsubmit = (e) => { e.preventDefault(); submitQuiz(id, quiz); };
    let left = quiz.minutes * 60;
    clearInterval(timerHandle);
    timerHandle = setInterval(() => {
      left--;
      $("timer").textContent = "Time left: " + Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
      if (left <= 0) { clearInterval(timerHandle); submitQuiz(id, quiz); }
    }, 1000);
  } catch (err) { say(err.message); }
}

async function submitQuiz(id, quiz) {
  clearInterval(timerHandle);
  const answers = {};
  quiz.questions.forEach((q) => {
    const picked = document.querySelector(`input[name=q${q.id}]:checked`);
    if (picked) answers[q.id] = picked.value;
  });
  try {
    const r = await api("/quizzes/" + id + "/attempt", "POST", { answers });
    $("take-form").innerHTML = "";
    $("timer").textContent = "";
    $("take-result").innerHTML = `<h3>You scored ${r.score} out of ${r.total} (${r.percent}%)</h3>` +
      quiz.questions.map((q, i) => {
        const rv = r.review.find((x) => x.question_id === q.id);
        return `<div class="question ${rv.correct ? "right" : "wrong"}"><b>${i + 1}. ${q.text}</b><br>
          Your answer: ${rv.your_answer ? rv.your_answer.toUpperCase() : "not answered"} | Correct answer: ${rv.correct_answer.toUpperCase()}</div>`;
      }).join("") + `<button onclick="show('quizzes')">Back to quizzes</button>`;
  } catch (err) { say(err.message); }
}

// ---------- results ----------
async function loadMyResults() {
  try {
    const list = await api("/attempts/mine");
    $("res-title").textContent = "My results";
    $("res-body").innerHTML = "<table><tr><th>Quiz</th><th>Score</th><th>Date</th></tr>" +
      list.map((x) => `<tr><td>${x.title}</td><td>${x.score} / ${x.total}</td><td>${x.taken_at}</td></tr>`).join("") + "</table>";
  } catch (err) { say(err.message); }
}

async function quizResults(id) {
  try {
    const r = await api("/quizzes/" + id + "/results");
    say("");
    document.querySelectorAll(".tab").forEach((t) => (t.hidden = true));
    $("tab-results").hidden = false;
    $("res-title").textContent = "Results: " + r.quiz;
    $("res-body").innerHTML = `<p>Attempts: ${r.attempts.length} | Average: ${r.average_percent}%</p>` +
      "<table><tr><th>Student</th><th>Score</th><th>Date</th></tr>" +
      r.attempts.map((x) => `<tr><td>${x.name}</td><td>${x.score} / ${x.total}</td><td>${x.taken_at}</td></tr>`).join("") + "</table>" +
      "<h3>Hardest questions</h3><table><tr><th>Question</th><th>Answered right</th></tr>" +
      r.hardest_questions.map((x) => `<tr><td>${x.text}</td><td>${x.right_count} of ${x.times}</td></tr>`).join("") + "</table>" +
      `<button onclick="show('quizzes')">Back</button>`;
  } catch (err) { say(err.message); }
}

// ---------- admin ----------
async function loadAdmin() {
  try {
    const s = await api("/stats");
    $("stats").innerHTML = `<p>Users: ${s.users} | Questions: ${s.questions} | Quizzes: ${s.quizzes} | Attempts: ${s.attempts}</p>`;
    const users = await api("/users");
    $("user-table").innerHTML = "<tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th></th></tr>" +
      users.map((u) => `<tr><td>${u.id}</td><td>${u.name}</td><td>${u.email}</td><td>${u.role}</td>
        <td>${u.id === user.id ? "" : `<button class="small red" onclick="delUser(${u.id})">Delete</button>`}</td></tr>`).join("");
  } catch (err) { say(err.message); }
}

async function delUser(id) {
  if (!confirm("Delete user " + id + "?")) return;
  try { await api("/users/" + id, "DELETE"); loadAdmin(); } catch (err) { say(err.message); }
}

if (token) start();
