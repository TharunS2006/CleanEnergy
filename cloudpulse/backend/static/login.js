(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const form = $("#login-form");
  const err = $("#login-error");
  const submit = $("#login-submit");

  const post = async (url, body) => {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CloudPulse": "1" },
      body: body ? JSON.stringify(body) : "{}",
      credentials: "same-origin",
    });
    let data = null;
    try { data = await res.json(); } catch { /* empty */ }
    if (!res.ok) throw new Error((data && data.detail) || "Something went wrong. Try again.");
    return data;
  };
  const showError = (msg) => { err.textContent = msg; err.hidden = false; };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.hidden = true;
    const email = $("#email").value.trim();
    const password = $("#password").value;
    if (!email || !password) { showError("Enter your email and password."); return; }
    submit.disabled = true;
    submit.textContent = "Signing in…";
    try {
      await post("/api/auth/login", { email, password });
      location.replace("/");
    } catch (ex) {
      showError(ex.message);
      $("#password").select();
    } finally {
      submit.disabled = false;
      submit.textContent = "Sign in";
    }
  });

  $("#demo-btn").addEventListener("click", async (e) => {
    const b = e.currentTarget;
    b.disabled = true;
    b.textContent = "Opening the demo…";
    try {
      await post("/api/auth/demo");
      location.replace("/");
    } catch (ex) {
      showError(ex.message);
      b.disabled = false;
      b.textContent = "Explore the demo";
    }
  });

  $("#pw-toggle").addEventListener("click", (e) => {
    const input = $("#password");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    e.currentTarget.textContent = show ? "Hide" : "Show";
    e.currentTarget.setAttribute("aria-pressed", String(show));
    e.currentTarget.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
})();
