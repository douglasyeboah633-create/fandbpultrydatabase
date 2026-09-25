# How to publish this page and get found on Google

This folder (`docs`) is the **public farm page** — the thing customers will
find on Google. It is completely separate from your farm system. Nothing about your
reports, workers or prices is in here.

---

## PART 1 — Make it yours (5 minutes)

Open `index.html` in Notepad (right-click → Open with → Notepad) and search for the
word **EDIT**. Every place you must change is marked. In short:

1. **Phone number** — replace `YOUR-PHONE` (twice) with your real number,
   e.g. `+233241234567`.
2. **WhatsApp number** — replace `YOUR-WHATSAPP-NUMBER` (twice) with your number in
   full international form, **no + and no spaces**, e.g. `233241234567`.
3. **Farm hours** — change "Monday to Saturday, 7:00am – 6:00pm" to your real hours.
4. **Location** — change "Your Town / District", "Your Region, Ghana" to your real
   place.
5. **Photos (recommended)** — make a folder named `images` inside `docs`, put
   3–6 pictures of your birds, eggs and poultry house in it, then follow the comment
   in the page to swap the emoji boxes for your photos. Real photos help a lot on
   Google.

> ⚠️ Never put your manager login (username/password) in this public page, and do not
> use your login email as the public contact — use a phone number or WhatsApp instead.

To see the page before publishing, just **double-click `index.html`** — it opens in
your browser.

---

## PART 2 — Put it online for free (5 minutes)

Your code is already on GitHub, so the easiest way is **GitHub Pages**.

### Option A — GitHub Pages (easiest — you already have the repository)
1. Open your repository:
   **https://github.com/douglasyeboah633-create/fandbpultrydatabase**
2. Click **Settings** (top menu) → **Pages** (left menu).
3. Under **Source**, choose **Deploy from a branch**.
4. Set **Branch** = `main` and the folder = **/docs**, then click **Save**.
5. Wait 1–2 minutes and refresh that page. GitHub shows your address:
   `https://douglasyeboah633-create.github.io/fandbpultrydatabase/`
   That is your farm's public page — open it and check it looks right.

### Option B — Netlify Drop (also free, nicer name)
1. Go to **https://app.netlify.com/drop**
2. Drag the whole **docs** folder onto the page.
3. You get a live address like `https://sunny-farm-12345.netlify.app`
4. Create a free account so you keep the site, then **Site configuration →
   Change site name** to something like `fbpoultryfarm`.

### Then update these two things with your new address
For GitHub Pages your address is:
`https://douglasyeboah633-create.github.io/fandbpultrydatabase/`
- In `index.html`: the two commented lines `canonical` and `og:url` — remove the
  `<!--` and `-->` around them and put your address in.
- In `sitemap.xml`: replace `YOUR-SITE-ADDRESS` with your real address (no `/` at the end
  inside `<loc>` is fine either way).
- Re-upload / re-deploy after those edits.

---

## PART 3 — Tell Google about it (10 minutes)

1. Go to **https://search.google.com/search-console**
2. Sign in with any Google/Gmail account.
3. Click **Add property → URL prefix** and paste your live address
   (e.g. `https://fbpoultryfarm.netlify.app/`) → **Continue**.
4. **Verify you own it.** Easiest way: choose **HTML file** → download the file Google
   gives you (`googleXXXXXXX.html`) → put it in the same folder as `index.html` →
   upload/re-deploy → click **Verify**.
5. Now submit your sitemap: left menu **Sitemaps** → type `sitemap.xml` → **Submit**.
6. Left menu **URL Inspection** → paste your address → **Request indexing**.
7. Come back after 2–7 days and check the **Pages** report — that shows whether Google
   has listed you. (Searching `site:your-address` on Google also shows if you are in.)

---

## PART 4 — Google Business Profile (THIS is what makes people find you)

Plain web pages get found by people typing your name. A **Business Profile** gets you
found by people searching "poultry farm near me" and puts you on **Google Maps**.

1. Go to **https://business.google.com** and sign in.
2. First search your farm name. If it already exists, click it and claim it.
   If not, click **Add your business**.
3. Fill in:
   - **Name**: F & B Poultry Farm
   - **Category**: *Poultry farm* (add *Egg supplier* and *Chicken hatchery* as extra)
   - **Location**: your real farm address (or choose "service area" if customers do
     not come to the farm — you can add the towns you deliver to)
   - **Phone**: your real number
   - **Website**: your new address from Part 2
   - **Hours**: your real opening hours
4. **Verify** — Google will ask you to prove it is your business. It often asks for a
   short **video** taken at the farm showing your birds, the poultry house, your
   location and anything with the farm name on it. Have that ready before you start.
   (Some places still use a phone call or a postcard.)
5. When it is live, add **photos** (farm, birds, eggs, crates), all 5 **products**, and
   ask a few customers for **reviews** — reviews push you up the list.
6. Post a small update now and then (new batch of chicks, eggs available, etc.).

---

## How long does Google take?

- Search Console indexing: usually **2 days to 2 weeks**.
- Business Profile: goes live a few days after verification (sometimes sooner).
- Google will not place you first straight away — photos, reviews and updates are what
  move you up over the following weeks.

## Quick checklist

- [ ] Phone + WhatsApp numbers replaced
- [ ] Location and hours replaced
- [ ] Photos added
- [ ] Uploaded (Netlify or GitHub Pages) — I have a live address
- [ ] `canonical` + `sitemap.xml` updated with the real address
- [ ] Search Console: property added, verified, sitemap submitted, indexing requested
- [ ] Business Profile created and verified
- [ ] Login details are nowhere on the public page
