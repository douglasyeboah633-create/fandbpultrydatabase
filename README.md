# F & B Poultry Farm Management System

Daily reports (workers) + dashboard, archive, records and workers (manager).
Run locally with `run.bat`, or host the same code online (see Deploy).

## Run on your PC
```
cd backend
pip install -r requirements.txt
python seed.py   # first time only, creates the manager account from backend/.env
python app.py
```
Open http://localhost:5000

Copy `backend/.env.example` to `backend/.env` and put your own values in it.
`.env` is ignored by git and is never uploaded.

## Deploy online (Render)
1. Upload this folder to GitHub (the database, photos and `.env` are excluded by `.gitignore`).
2. On Render: New + → Web Service → pick the repo.
   Build: `pip install -r backend/requirements.txt` · Start: `gunicorn --chdir backend app:app`
3. In Render → Environment, set `MANAGER_NAME`, `MANAGER_USERNAME`,
   `MANAGER_EMAIL`, `MANAGER_PASSWORD` and `JWT_SECRET`.
4. Open the Render URL once, then log in with your manager username/password.

## Deploy online (Vercel)
This repo also contains `wsgi.py`, so Vercel can run the same app.

**You must tell the site ONE secret — its manager password.** The repository
is public, so the password can never be written into the code; without this
setting every fresh server copy has no manager account and the login page
shows *"This hosting site has no manager login yet…"*.

1. On Vercel open your project → **Settings → Environment Variables**.
2. Add at least this one, then press **Save**:
   - Key: `MANAGER_PASSWORD` — Value: a secret word only you know.
   Strongly recommended on the same page:
   - `JWT_SECRET` — long random text. Keeps every server copy agreeing on
     logins (without it the login key is derived from the password instead).
   - `MANAGER_USERNAME` (default `manager`), `MANAGER_NAME`, `MANAGER_EMAIL`.
3. When adding a variable make sure the **Production** environment is ticked
   (tick Preview too if in doubt).
4. **Deployments → newest → ⋯ → Redeploy** — saving a variable does not
   change a deployment that is already running.
5. Open the site and log in with `MANAGER_USERNAME` (default `manager`) and
   the `MANAGER_PASSWORD` you set.

**Shortcut:** if no password has been configured anywhere, the login page
now offers a **first-time set-up form** (Ghana only) where the first visitor
chooses the username and password — no hosting-site settings needed. The
environment variable is still the recommended way (it survives redeploys;
the form reappears on every fresh server copy).

If the page still says there is no manager account, the variable name has a
typo, its value is empty, or its environment is wrong — repeat steps 2–4.

> ⚠️ A free Vercel copy keeps its database only in temporary memory: reports
> disappear when the copy sleeps or when you deploy again, and several copies
> do not share data with each other. For real daily farm use host the site on
> **Render** (section above) — one server with a permanent disk. Whichever
> host you use, press "Download full backup" on the Manager page regularly.

## Worker app (worker.html)
- ONE daily report per day: feeding (bags / kg / birds fed), water (litres),
  eggs collected / broken / crates packed, chickens & crates sold, deaths +
  reason, mortality photo, problems, notes and the amount received (GH₵).
- Nothing may be left empty, and the mortality photo is required when birds died.
- Only one report per worker per day (a second one on the same day is refused).
- The worker can edit or delete his own report and sees the manager's comments.
- After sending, a thank-you popup appears to appreciate the worker.

## Manager app (manager.html)
- Dashboard: today at a glance (money received, eggs, chickens sold, deaths,
  how many workers reported), red warnings (high mortality, low stock),
  last-30-days charts and "This month vs Last month" comparison + CSV.
- Worker Reports: day view, day totals, weekly CSV, and Print / Save as PDF.
- Report Archive: every report the manager has reviewed is kept here (search,
  date filter, CSV, print). Opening a report moves it to the Archive already.
- My Records: the manager's own notebook — goods received, money paid out,
  repairs, reminders or notes, with date, type, title, details and an optional
  amount. Edit, delete, search, filter, CSV and print.
- Download full backup: one click gives a safe copy of the whole database.
- Workers: add, disable/enable, reset password, delete.

## Printing
Print / Save as PDF builds a clean A4 table sheet (farm heading, all columns,
totals box and a printed-by footer) for the current day, the archive list or
the records. In the Windows print window choose "Save as PDF".

## Reminders
- 7 PM: workers who have not sent their daily report get a reminder.
- Manager gets a reminder while reports are still waiting to be checked.

## Reset database
Delete backend/farm.db then run python seed.py again.
