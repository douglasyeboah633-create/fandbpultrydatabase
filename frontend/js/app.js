const API = '';
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
function tok() { return localStorage.getItem('fb_token') || sessionStorage.getItem('fb_token'); }
function me() { try { return JSON.parse(localStorage.getItem('fb_user') || sessionStorage.getItem('fb_user') || 'null'); } catch(e){ return null; } }

// ---------- KEEPING YOU LOGGED IN ON FREE HOSTING ----------
// Free hosting (Vercel) runs several copies of this app and recycles them
// without warning. A recycled copy forgets its memory, so a login made a
// moment earlier can suddenly be "unknown" - the pages used to say
// "Please log in first" even though you had just signed in.
// To hide that, the username and password are kept in sessionStorage (this
// browser tab only - closing the tab forgets them, and nothing is ever
// written into the code or the repository). When a copy says the session is
// gone, the app signs in again on whichever copy is answering and repeats the
// request, so you simply never see an error.
function creds() { try { return JSON.parse(sessionStorage.getItem('fb_creds') || localStorage.getItem('fb_creds') || 'null'); } catch(e) { return null; } }
function keepCreds(username, password, remember) {
  try {
    const rec = JSON.stringify({ u: String(username), p: String(password) });
    const box = remember ? localStorage : sessionStorage;
    const other = remember ? sessionStorage : localStorage;
    other.removeItem('fb_creds');
    box.setItem('fb_creds', rec);
  } catch(e) {}
}
function dropCreds() { try { sessionStorage.removeItem('fb_creds'); localStorage.removeItem('fb_creds'); } catch(e) {} }
function dropToken() {
  try {
    localStorage.removeItem('fb_token'); localStorage.removeItem('fb_user');
    sessionStorage.removeItem('fb_token'); sessionStorage.removeItem('fb_user');
  } catch(e) {}
}
// Store the token where the user asked for it ("Remember me" = this computer,
// otherwise this tab only) and clear the other place so a stale copy of an old
// token can never be sent by mistake.
function saveSession(j, remember) {
  const box = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  try { other.removeItem('fb_token'); other.removeItem('fb_user'); } catch(e) {}
  box.setItem('fb_token', j.token);
  box.setItem('fb_user', JSON.stringify(j.user));
}
// One sign-in at a time, however many requests notice the dead session.
let reloginBusy = null;
let reloginWhy = '';   // why the last silent sign-in failed, for a clear message
function postJSON(path, body) {
  return fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(function (r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      return { ok: r.ok, status: r.status, body: j };
    });
  });
}
function relogin() {
  if (reloginBusy) return reloginBusy;
  const c = creds();
  if (!c) return Promise.resolve(false);
  const remember = !!localStorage.getItem('fb_token');
  reloginBusy = postJSON('/api/auth/login', { username: c.u, password: c.p })
    .then(function (a) {
      if (a.ok && a.body && a.body.token) {
        saveSession(a.body, remember);
        return true;
      }
      // This particular copy of the app was recycled and came back with an
      // empty database, so it no longer knows the manager account. Put the
      // SAME account back (same username, same password that was accepted a
      // moment ago) and sign in. This is exactly what the set-up form on the
      // login page does by hand, done quietly so the user never gets thrown
      // out of the page they are working in.
      if (a.status === 503 && a.body && a.body.code === 'setup_required') {
        return postJSON('/api/auth/setup', { username: c.u, password: c.p })
          .then(function (b) {
            if (b.ok && b.body && b.body.token) {
              saveSession(b.body, remember);
              return true;
            }
            // Another copy created the account first, or set-up was refused:
            // simply try the ordinary login once more.
            reloginWhy = (b.body && b.body.error) || '';
            return postJSON('/api/auth/login', { username: c.u, password: c.p })
              .then(function (d) {
                if (d.ok && d.body && d.body.token) {
                  saveSession(d.body, remember);
                  reloginWhy = '';
                  return true;
                }
                if (!reloginWhy) reloginWhy = (d.body && d.body.error) || '';
                return false;
              });
          });
      }
      reloginWhy = (a.body && (a.body.error || a.body.msg)) || '';
      return false;
    }).catch(function () { return false; })
    .then(function (ok) { reloginBusy = null; return ok; });
  return reloginBusy;
}
async function api(path, opt={}, tries) {
  tries = tries || 0;
  opt.headers = opt.headers || {};
  const t = tok();
  if (t) opt.headers['Authorization'] = 'Bearer ' + t;
  if (opt.body && typeof opt.body === 'object') { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(opt.body); }
  let r;
  try { r = await fetch(API + path, opt); }
  catch(e) { throw new Error('Cannot reach the farm server. Check your internet connection and try again.'); }
  let j = {};
  try { j = await r.json(); } catch(e) {}
  if (r.ok) return j;

  // The copy that just answered has restarted and no longer knows this
  // session. Sign in again and repeat the request (up to twice) instead of
  // throwing the user out of the page they are already using.
  const isAuthCall = path.indexOf('/api/auth/login') > -1 || path.indexOf('/api/auth/setup') > -1;
  const deadSession = !isAuthCall && (j.code === 'bad_token' || r.status === 422 ||
                                      (r.status === 401 && (t || creds())));
  if (deadSession && tries < 2) {
    reloginWhy = '';
    const ok = await relogin();
    if (ok) return api(path, opt, tries + 1);
  }
  // Show the SERVER'S own words (wrong password, missing setup, expired
  // session, ...) instead of one generic message for every problem.
  let msg = j.error || j.msg ||
    (r.status === 404 ? 'That page or action was not found on the server.'
     : r.status === 401 ? 'Your session has ended. Please log in again.'
     : 'Something went wrong. Please try again.');
  const err = new Error(msg);
  err.code = j.code || '';   // 'setup_required' opens the first-time form
  if (j.code === 'setup_required') {
    const lb = document.getElementById('loginbox');
    const sb = document.getElementById('setupbox');
    if (lb && sb) {
      lb.style.display = 'none';
      sb.style.display = 'block';
      err.message = 'First time here: choose your manager username and password below.';
    }
  }
  if (j.code === 'bad_token' || (r.status === 401 && !isAuthCall)) {
    // Nothing left to try (no password kept for this tab, or it was refused):
    // clear the dead session and walk back to the login page once. Keep the
    // stored password when the copy merely lost its manager account, so the
    // login page can restore it by itself instead of asking for it again.
    const lostAccount = /no manager login yet/i.test(reloginWhy);
    err.message = lostAccount
      ? 'This copy of the farm app restarted and lost its manager account. Taking you back to the login page - it will restore itself.'
      : (reloginWhy || 'Your session ended because the server restarted - taking you back to the login page...');
    dropToken();
    if (!lostAccount) dropCreds();
    setTimeout(function(){ location.href = 'login.html'; }, 1500);
  }
  throw err;
}
function say(id, ok, text) {
  const el = typeof id === 'string' ? $(id) : id;
  if (!el) { alert(text); return; }
  el.className = 'msg ' + (ok ? 'ok' : 'err');
  el.textContent = text;
  el.style.display = 'block';
}
function badge(s) {
  s = (s||'').toLowerCase();
  if (s === 'approved' || s === 'completed' || s === 'delivered') return `<span class="badge appr">${s}</span>`;
  if (s === 'rejected' || s === 'cancelled') return `<span class="badge rej">${s}</span>`;
  return `<span class="badge pend">${s}</span>`;
}
function needLogin() {
  if (!tok()) { location.href = 'index.html'; return true; }
  return false;
}
function guard(role) {
  const u = me();
  if (!u) { location.href = 'index.html'; return null; }
  if (role === 'manager' && u.role !== 'manager') { location.href = 'worker.html'; return null; }
  if (role === 'worker' && u.role === 'manager') { location.href = 'manager.html'; return null; }
  return u;
}
function logout() {
  dropToken();
  dropCreds();
  location.href = 'index.html';
}
function toggleMenu() {
  const s = $('#side');
  if (s) s.classList.toggle('open');
}
function money(n) { return 'GH₵ ' + Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2}); }
function toCSV(rows, filename) {
  if (!rows.length) { alert('Nothing to export.'); return; }
  const keys = Object.keys(rows[0]);
  const lines = [keys.join(',')].concat(rows.map(r => keys.map(k => `"${String(r[k]??'').replace(/"/g,'""')}"`).join(',')));
  const blob = new Blob([lines.join('\n')], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = filename; a.click();
}
