// QuickPay frontend. Django serves this page at "/", so API calls are same-origin.
"use strict";

const API = {
  register: "/api/users/register/",
  login: "/api/users/login/",
  refresh: "/api/users/token/refresh/",
  profile: "/api/users/profile/",
  deposit: "/deposit/",
  transfer: "/transfer/",
  balance: "/balance/",
  history: "/history/",
};

const KYC_MESSAGE =
  "Your account is awaiting identity verification. An administrator must approve it before you can move money.";

// ---------- storage (sessionStorage, guarded) ----------
const store = {
  get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { sessionStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  del(k) { try { sessionStorage.removeItem(k); } catch { /* storage unavailable */ } },
  json(k, fallback) { try { return JSON.parse(this.get(k)) ?? fallback; } catch { return fallback; } },
};

// ---------- API client ----------
class ApiError extends Error {
  constructor(status, data) {
    super("API error " + status);
    this.status = status;
    this.data = data;
  }
}

async function refreshAccessToken() {
  const refresh = store.get("qp.refresh");
  if (!refresh) return false;
  try {
    const res = await fetch(API.refresh, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    store.set("qp.access", data.access);
    if (data.refresh) store.set("qp.refresh", data.refresh);
    return true;
  } catch {
    return false;
  }
}

async function api(path, { method = "GET", body, auth = true, retried = false } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const access = store.get("qp.access");
  if (auth && access) headers.Authorization = "Bearer " + access;

  let res;
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, { detail: "Network problem. Check your connection and try again. Retrying a payment is safe." });
  }

  let data = null;
  try { data = await res.json(); } catch { /* empty or non-JSON body */ }

  if (res.status === 401 && auth && !retried) {
    if (await refreshAccessToken()) return api(path, { method, body, auth, retried: true });
    signOut("Your session has expired. Please sign in again.");
    throw new ApiError(401, { detail: "Your session has expired. Please sign in again." });
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

// ---------- error messages ----------
// The API returns DRF field errors ({field: [msg]}), {detail: msg} or {status, message}.
// Some messages arrive as stringified Python lists, e.g. "['Insufficient funds.']".
function tidy(text) {
  let s = String(text).trim();
  for (let i = 0; i < 4; i++) {
    s = s.replace(/^\[+|\]+$/g, "").trim().replace(/^["']|["']$/g, "").trim();
  }
  return s.replace(/^Transaction aborted:\s*/i, "").replace(/^\[+|\]+$/g, "").replace(/^["']|["']$/g, "");
}

function collectMessages(data) {
  if (data == null) return [];
  if (typeof data === "string") return [tidy(data)];
  if (Array.isArray(data)) return data.flatMap(collectMessages);
  const out = [];
  for (const [key, value] of Object.entries(data)) {
    if (key === "status") continue;
    out.push(...collectMessages(value));
  }
  return out;
}

function errorMessages(err, { moneyAction = false } = {}) {
  if (!(err instanceof ApiError)) return ["Something went wrong. Please try again."];
  if (moneyAction && err.status === 403) return [KYC_MESSAGE];
  if (err.status === 502) return collectMessages(err.data);
  if (err.status >= 500) return ["The server had a problem. Please try again in a moment."];
  const msgs = collectMessages(err.data).filter(Boolean);
  return msgs.length ? msgs : ["Something went wrong. Please try again."];
}

function showFormError(form, messages) {
  const box = form.querySelector(".form-error");
  box.textContent = "";
  if (!messages || !messages.length) { box.hidden = true; return; }
  if (messages.length === 1) {
    box.textContent = messages[0];
  } else {
    const ul = document.createElement("ul");
    for (const m of messages) {
      const li = document.createElement("li");
      li.textContent = m;
      ul.appendChild(li);
    }
    box.appendChild(ul);
  }
  box.hidden = false;
}

// ---------- money helpers (strings and integer cents, never floats) ----------
const AMOUNT_RE = /^\d{1,9}(\.\d{1,2})?$/;

function normaliseAmount(raw) {
  const s = String(raw).trim().replace(/\s|,/g, "");
  if (!AMOUNT_RE.test(s)) return null;
  const [whole, frac = ""] = s.split(".");
  const normal = String(Number.parseInt(whole, 10)) + "." + (frac + "00").slice(0, 2);
  return toCents(normal) > 0 ? normal : null;
}

function toCents(amount) {
  const [whole, frac = "00"] = amount.split(".");
  return Number.parseInt(whole, 10) * 100 + Number.parseInt((frac + "00").slice(0, 2), 10);
}

function formatRand(cents) {
  const sign = cents < 0 ? "−" : "";
  const abs = Math.abs(cents);
  const whole = String(Math.floor(abs / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const frac = String(abs % 100).padStart(2, "0");
  return `${sign}R ${whole}.${frac}`;
}

// ---------- idempotency ----------
// One key per payment attempt. The same inputs keep the same key, so pressing the
// button again after a dropped connection cannot create a second payment.
function newKey() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  return Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}

function keyFor(form, signature) {
  if (form.dataset.signature !== signature || !form.dataset.key) {
    form.dataset.signature = signature;
    form.dataset.key = newKey();
  }
  return form.dataset.key;
}

function forgetKey(form) {
  delete form.dataset.signature;
  delete form.dataset.key;
}

// ---------- UI helpers ----------
const $ = (id) => document.getElementById(id);

let toastTimer;
function toast(message, success = true) {
  const t = $("toast");
  t.textContent = message;
  t.className = "toast" + (success ? " is-success" : "");
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 4000);
}

async function withBusy(form, label, fn) {
  const btn = form.querySelector('button[type="submit"]');
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = label;
  try { return await fn(); } finally { btn.disabled = false; btn.textContent = original; }
}

function maskId(id) {
  if (!id) return "–";
  const s = String(id);
  return "•••••••••" + s.slice(-4);
}

// ---------- views ----------
function showAuth() {
  $("view-app").hidden = true;
  $("topbar-user").hidden = true;
  $("view-auth").hidden = false;
}

function showApp(profile) {
  $("view-auth").hidden = true;
  $("view-app").hidden = false;
  $("topbar-user").hidden = false;
  const name = [profile.first_name, profile.last_name].filter(Boolean).join(" ");
  $("topbar-name").textContent = name || profile.email;
  $("greeting").textContent = profile.first_name ? `Welcome, ${profile.first_name}` : "Welcome";
  $("pf-name").textContent = name || "–";
  $("pf-email").textContent = profile.email || "–";
  $("pf-phone").textContent = profile.phone_number || "–";
  $("pf-id").textContent = maskId(profile.id_number);
  renderStatus();
  loadWallet();
}

function setTab(which) {
  const signin = which === "signin";
  $("tab-signin").classList.toggle("is-active", signin);
  $("tab-register").classList.toggle("is-active", !signin);
  $("tab-signin").setAttribute("aria-selected", String(signin));
  $("tab-register").setAttribute("aria-selected", String(!signin));
  $("form-signin").hidden = !signin;
  $("form-register").hidden = signin;
}

function setBanner(message) {
  const b = $("auth-banner");
  b.textContent = message || "";
  b.hidden = !message;
}

// Verification status is not in the profile response; it is learned from the wallet endpoints,
// which refuse accounts that are still pending KYC.
function renderStatus() {
  const status = store.get("qp.kyc");
  const pill = $("status-pill");
  if (status === "verified") {
    pill.textContent = "Verified";
    pill.className = "status-pill is-verified";
    pill.hidden = false;
    $("kyc-banner").hidden = true;
  } else if (status === "pending") {
    pill.textContent = "Verification pending";
    pill.className = "status-pill is-pending";
    pill.hidden = false;
    $("kyc-banner").hidden = false;
  } else {
    pill.hidden = true;
    $("kyc-banner").hidden = true;
  }
}

// The history response has no counterparty, so remember who each payment from this browser went to.
function recipientsKey() {
  return "qp.recipients." + (store.get("qp.email") || "anon");
}

function rememberRecipient(transactionId, to) {
  const map = store.json(recipientsKey(), {});
  map[transactionId] = to;
  store.set(recipientsKey(), JSON.stringify(map));
}

// Balance arrives as a JSON number and history amounts as strings; both become integer cents.
function centsFrom(value) {
  if (typeof value === "number") return Math.round(value * 100);
  return toCents(String(value));
}

const DEPOSIT_PREFIX = "SYSTEM DEPOSIT: ";

function renderBalance(state, cents) {
  const el = $("balance");
  const note = $("balance-note");
  el.className = "session-net mono";
  if (state === "ok") {
    el.textContent = formatRand(cents);
    note.textContent = "Worked out from your ledger entries, to the cent.";
  } else if (state === "pending") {
    el.textContent = "–";
    note.textContent = "Your balance appears once your identity is verified.";
  } else {
    el.textContent = "–";
    note.textContent = "Your balance couldn't be loaded. Try Refresh.";
  }
}

function renderHistory(state, entries) {
  const list = $("activity");
  const empty = $("activity-empty");
  list.textContent = "";
  if (state !== "ok") {
    empty.textContent = state === "pending"
      ? "Your transaction history appears once your identity is verified."
      : "Your transaction history couldn't be loaded. Try Refresh.";
    empty.hidden = false;
    return;
  }
  const recipients = store.json(recipientsKey(), {});
  for (const entry of entries) {
    const incoming = centsFrom(entry.credit) > 0;
    const cents = incoming ? centsFrom(entry.credit) : centsFrom(entry.debit);
    const raw = String(entry.description || "");
    const isDeposit = raw.startsWith(DEPOSIT_PREFIX);
    const description = isDeposit ? raw.slice(DEPOSIT_PREFIX.length) : raw;
    const to = recipients[entry.transaction_id];

    const li = document.createElement("li");
    const icon = document.createElement("span");
    icon.className = "icon " + (incoming ? "icon-in" : "icon-out");
    icon.textContent = incoming ? "+" : "→";
    const what = document.createElement("div");
    what.className = "what";
    const title = document.createElement("strong");
    title.textContent = isDeposit ? "Money added" : incoming ? "Money received" : to ? `Sent to ${to}` : "Money sent";
    const meta = document.createElement("span");
    const when = new Date(entry.timestamp).toLocaleString("en-ZA", { dateStyle: "medium", timeStyle: "short" });
    meta.textContent = `${description} · Transaction #${entry.transaction_id} · ${when}`;
    what.append(title, meta);
    const amt = document.createElement("span");
    amt.className = "amt " + (incoming ? "in" : "out");
    amt.textContent = (incoming ? "+" : "−") + formatRand(cents);
    li.append(icon, what, amt);
    list.appendChild(li);
  }
  empty.textContent = "No payments yet. Money you add or send appears here with its transaction number.";
  empty.hidden = entries.length > 0;
}

// 403 (not approved) and 404 (no wallet yet) both mean the account is still pending KYC.
function outcome(result) {
  if (result.status === "fulfilled") return "ok";
  const err = result.reason;
  return err instanceof ApiError && (err.status === 403 || err.status === 404) ? "pending" : "error";
}

async function loadWallet() {
  const [balance, history] = await Promise.allSettled([api(API.balance), api(API.history)]);
  const balanceState = outcome(balance);
  const historyState = outcome(history);
  renderBalance(balanceState, balanceState === "ok" ? centsFrom(balance.value.balance) : 0);
  renderHistory(historyState, historyState === "ok" ? history.value.history || [] : []);
  if (balanceState === "ok" || historyState === "ok") store.set("qp.kyc", "verified");
  else if (balanceState === "pending" || historyState === "pending") store.set("qp.kyc", "pending");
  renderStatus();
}

function signOut(message) {
  store.del("qp.access");
  store.del("qp.refresh");
  store.del("qp.kyc");
  store.del("qp.email");
  setTab("signin");
  setBanner(message || "");
  showAuth();
}

async function loadProfile() {
  const profile = await api(API.profile);
  store.set("qp.email", profile.email);
  showApp(profile);
}

// ---------- form handlers ----------
function fieldValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

$("tab-signin").addEventListener("click", () => { setTab("signin"); setBanner(""); });
$("tab-register").addEventListener("click", () => { setTab("register"); setBanner(""); });
$("signout-btn").addEventListener("click", () => signOut("You have signed out."));
$("refresh-btn").addEventListener("click", () => loadWallet());

$("form-signin").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const { email, password } = fieldValues(form);
  if (!email || !password) return showFormError(form, ["Enter your email and password."]);
  showFormError(form, null);
  await withBusy(form, "Signing in…", async () => {
    try {
      const tokens = await api(API.login, { method: "POST", body: { email: email.trim(), password }, auth: false });
      store.set("qp.access", tokens.access);
      store.set("qp.refresh", tokens.refresh);
      form.reset();
      setBanner("");
      await loadProfile();
    } catch (err) {
      const msgs = err instanceof ApiError && err.status === 401
        ? ["That email and password combination is not recognised."]
        : errorMessages(err);
      showFormError(form, msgs);
    }
  });
});

$("form-register").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  const v = fieldValues(form);
  const missing = ["first_name", "last_name", "email", "phone_number", "id_number", "password"].filter((k) => !String(v[k] || "").trim());
  if (missing.length) return showFormError(form, ["Please complete every field."]);
  if (!/^\d{13}$/.test(v.id_number.trim())) return showFormError(form, ["An SA ID number has exactly 13 digits."]);
  showFormError(form, null);
  await withBusy(form, "Creating account…", async () => {
    try {
      await api(API.register, {
        method: "POST",
        auth: false,
        body: {
          first_name: v.first_name.trim(),
          last_name: v.last_name.trim(),
          email: v.email.trim(),
          phone_number: v.phone_number.trim(),
          id_number: v.id_number.trim(),
          password: v.password,
        },
      });
      const email = v.email.trim();
      form.reset();
      setTab("signin");
      $("signin-email").value = email;
      setBanner("Account created. You can sign in now. Sending and adding money unlock once your identity is verified.");
      $("signin-password").focus();
    } catch (err) {
      showFormError(form, errorMessages(err));
    }
  });
});

async function moneySubmit(e, kind) {
  e.preventDefault();
  const form = e.currentTarget;
  const v = fieldValues(form);
  const amount = normaliseAmount(v.amount || "");
  const description = String(v.description || "").trim();
  const recipient = kind === "transfer" ? String(v.recipient || "").trim() : null;

  const problems = [];
  if (kind === "transfer" && !recipient) problems.push("Enter the recipient's email or mobile number.");
  if (!amount) problems.push("Enter an amount in rand, for example 150 or 150.50.");
  if (!description) problems.push("Add a reference so you recognise this payment later.");
  if (problems.length) return showFormError(form, problems);
  showFormError(form, null);

  const signature = [kind, recipient, amount, description].join("|");
  const idempotency_key = keyFor(form, signature);
  const body = kind === "transfer"
    ? { recipient, amount, description, idempotency_key }
    : { amount, description, idempotency_key };

  await withBusy(form, kind === "transfer" ? "Sending…" : "Adding…", async () => {
    try {
      const res = await api(kind === "transfer" ? API.transfer : API.deposit, { method: "POST", body });
      store.set("qp.kyc", "verified");
      renderStatus();
      if (kind === "transfer") rememberRecipient(res.transaction_id, recipient);
      loadWallet();
      forgetKey(form);
      form.reset();
      toast(kind === "transfer"
        ? `Sent ${formatRand(toCents(amount))} to ${recipient}.`
        : `Added ${formatRand(toCents(amount))} to your account.`);
    } catch (err) {
      // A 403 means the account is not approved yet; a 400 means it passed the approval check.
      if (err instanceof ApiError && (err.status === 403 || err.status === 400)) {
        store.set("qp.kyc", err.status === 403 ? "pending" : "verified");
        renderStatus();
      }
      showFormError(form, errorMessages(err, { moneyAction: true }));
    }
  });
}

$("form-deposit").addEventListener("submit", (e) => moneySubmit(e, "deposit"));
$("form-transfer").addEventListener("submit", (e) => moneySubmit(e, "transfer"));

// ---------- start ----------
(async function start() {
  setTab("signin");
  if (!store.get("qp.access")) return showAuth();
  try {
    await loadProfile();
  } catch {
    signOut("Please sign in to continue.");
  }
})();
