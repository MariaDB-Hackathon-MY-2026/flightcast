# Full Presentation Script — FlightCast

**Built by:** Low Yan Cheng (TP070056), APU Malaysia
**Submission:** MariaDB Hackathon Malaysia 2026 · Innovation Track
**Total runtime target:** 9 to 11 minutes
**Audience:** general (no technical background assumed)
**Recording:** Loom or OBS Studio, 1920 × 1080, voice-over live
**Dashboard:** http://localhost:3000

---

## How to use this script

1. Open this file on a second screen (or print page 1).
2. Open the dashboard at `http://localhost:3000/time-travel`. Confirm everything is loaded.
3. Click **Start Pitch Tour** when the recording starts. The tour walks all 19 steps in order; click **Next** between segments.
4. The script tells you exactly when to act (drag, click, switch tab) — those moments are highlighted in **bold**.
5. Voice-over is plain English. If you stumble, mute, restart from the same step boundary, and edit the cut in post.

---

## Pre-recording checklist (10 min)

| Check | How |
|---|---|
| All four services healthy | `docker compose ps` shows db, api, app, web all `Up (healthy)` |
| Dashboard loads | Browser at `http://localhost:3000/time-travel`, Plotly chart already mounted |
| Forecast Explorer pre-warm | Click "All history" once on `/forecast-explorer`, then go back to `/time-travel` so the rainbow chart is cached |
| Numbers correct | Coverage page: `92.1 / 92.2 / 91.7 / 92.6 / 57.1 / 60.2`. Winkler section visible. |
| Clean download folder | Empty `Downloads` so the CSV file is the only one visible when you open it |
| Excel open in advance | Have Excel running so the CSV opens instantly without a "What program?" prompt |
| Notifications off | Slack, Outlook, system tray, phone all silenced |
| Browser zoom | Ctrl+0 → 100% |
| Mic check | 30-second test recording, set gain |

---

## Opening (00:00 – 00:25) — before you click Start Pitch Tour

**Visible:** the Time Travel page, with the FlightCast title and four status pills at the top.
**Action:** none — just speak.

**Voice-over (~25 seconds):**

> "Hi, I'm Low Yan Cheng from APU Malaysia. This is FlightCast. It solves a problem most companies have, but nobody talks about. When AI makes predictions about your business — sales next month, demand next week — those predictions usually disappear when the AI is updated. So if anyone ever asks 'what did your AI think last quarter?', you can't answer. FlightCast fixes that, using one feature only MariaDB has natively. Let me show you. I'll click Start Pitch Tour on the left."

**Then:** click **Start Pitch Tour** in the sidebar.

---

## Step 1 — The ML audit problem (00:25 – 00:55)

**Visible:** popover lands on the page header.
**Action:** none.

**Voice-over (~30 seconds):**

> "Imagine you run an airline. Every week, your AI looks at all the data and gives you a fresh 30-day forecast: how many passengers will book each route. You make real decisions from it — pricing, crew rosters, fuel orders. Three months later, an auditor asks: 'what was your forecast for January 15th?'. Most companies can't answer. The AI overwrote it during retraining. FlightCast solves this by keeping every prediction the AI ever made, automatically, inside the database itself."

**Then:** click Next.

---

## Step 2 — Ask MariaDB (00:55 – 01:25)

**Visible:** the violet "Ask MariaDB" hero callout with the SQL keyword chip.
**Action:** mouse-hover the `FOR SYSTEM_TIME AS OF` chip while you speak.

**Voice-over (~30 seconds):**

> "Here's how. MariaDB has a feature called system-versioned tables. Every time the AI saves a prediction, the database remembers exactly when it was saved, and never throws away the old version. To go back in time, we just type five English-like words: FOR SYSTEM TIME AS OF a date. MySQL — what most companies use — gives you a syntax error if you try this. PostgreSQL needs a third-party add-on. SQLite can't do it at all. MariaDB is the only mainstream database that ships this out of the box."

**Then:** click Next.

---

## Step 3 — Drag the audit slider (01:25 – 02:05) · LIVE INTERACTION

**Visible:** popover on the "Audit point in time" card.
**Action:** **drag the slider slowly from the right (latest batch) all the way to the left (earliest), then back to the right.** Watch the chart below update with each step.

**Voice-over (~40 seconds — pace it to your dragging):**

> "Now let's actually time-travel. I'm going to drag this slider from today, all the way back to the earliest forecast we have. Each tick is a real moment in history — a real timestamp from when the AI committed a prediction. As I drag … the chart below updates every step. Each position is a different version of the AI making different predictions. We are literally watching the model's mind change over time. No backup files, no log scraping, no extra software — just one slider talking directly to the database."

**Then:** leave the slider on the latest batch (right side), click Next.

---

## Step 4 — Pick the route to audit (02:05 – 02:35) · LIVE INTERACTION

**Visible:** popover on the Route card.
**Action:** **click the Route dropdown, scroll, and pick a route different from the default — anything random, ideally a different traffic tier (hub vs mid vs thin).**

**Voice-over (~30 seconds):**

> "Now let me change the route. The dropdown lists fifty real airline routes from a public dataset called OpenFlights. Big hub routes. Medium ones. Small thin routes with low traffic. I'll pick this one at random. Instantly, the chart shows me the AI's predictions for that route, at the same point in time we were viewing. Two questions, one answer: which route, on which day in history. The database does both at once."

**Then:** click Next.

---

## Step 5 — Coverage you can verify (02:35 – 03:05)

**Visible:** the four KPI cards.
**Action:** mouse-hover the second card ("Empirical coverage") while you speak.

**Voice-over (~30 seconds):**

> "These four numbers tell us how trustworthy the AI is. The most important is the second one — empirical coverage. Conformal prediction is a math result that promises this: if my AI says 'I am 90 percent confident', then 90 percent of the time the real number lands inside the predicted range. We don't just claim that — we measure it on real data. When the AI is healthy, we hit 91 to 92 percent. The math is working."

**Then:** click Next.

---

## Step 6 — 30 day forecast and band (03:05 – 04:00) · LIVE INTERACTION

**Visible:** the chart card with the predicted-demand line and the violet confidence band.
**Action sequence:**
1. **Toggle "Show actuals"** in the chart's top-right corner. Amber dots appear inside the band.
2. **Click "Download"** next to it. A CSV file saves to your Downloads folder.
3. **Switch to your file explorer or taskbar, double-click the downloaded CSV** so it opens in Excel.
4. **Pause on the open Excel file for 6–8 seconds** while you describe the columns.
5. **Switch back to the browser dashboard.**

**Voice-over (~55 seconds):**

> "This is the actual forecast. The line is what the AI thinks demand will be each day for the next 30 days. The shaded violet area is the 90 percent confidence range — the AI is saying, 'I am not sure of the exact number, but I am 90 percent sure it sits inside this band.' Now let me prove it works.
>
> [toggle Show actuals]
>
> I just turned on the actual numbers — those orange dots are what really happened, measured AFTER the AI made the prediction. Look — they sit INSIDE the violet band. That is the 90 percent guarantee, working in the real world. Let me also download the data, so an auditor can verify it offline.
>
> [click Download, open the CSV in Excel]
>
> Each row is one day's prediction. Predicted demand. Lower bound. Upper bound. The model version that produced it. The actual number we measured later. And — this is the audit part — a column called row_start showing the exact micro-second when this prediction was committed to the database. Anyone can take this file, run one SQL query, and reproduce my chart on their own machine."

**Then:** switch back to the dashboard tab, click Next.

---

## Step 7 — Live SQL bridge (04:00 – 04:25)

**Visible:** the SQL panel showing the live query.
**Action:** mouse-hover the SQL text. (No copy needed — just point at it.)

**Voice-over (~25 seconds):**

> "This panel shows the actual database query that produced the chart. This is not a render or a screenshot — this is the live SQL that just ran. You could copy this, paste it into any MariaDB client, and get the same answer back. The dashboard is just a pretty wrapper around plain SQL."

**Then:** click Next. The tour will navigate to the Forecast Explorer page.

---

## Step 8 — Six versions, one query (04:25 – 04:50) · LIVE INTERACTION

**Visible:** Forecast Explorer page, the View mode picker visible.
**Action:** **click "All history"** in the View mode picker. The chart switches to the rainbow overlay.

**Voice-over (~25 seconds):**

> "We're now on a different page — Forecast Explorer. I'll click All history. Look at this. Six different versions of the AI, each in a different color, all on the same chart. Every time we retrained the model, we kept that version forever inside the database. So we can see how the AI's thinking has evolved across time."

**Then:** click Next.

---

## Step 9 — What the rainbow shows (04:50 – 05:15)

**Visible:** the rainbow chart still on screen.
**Action:** mouse-trace across the bands, top to bottom.

**Voice-over (~25 seconds):**

> "Each colored ribbon is one model version with its own confidence band. Where the bands stack tightly together, the AI was being consistent — that's healthy. Where they spread apart, the model changed its mind a lot — that's a warning sign. And to draw this picture, the system asked the database for every version ever, with one query. In a normal setup you'd write Python code, make six API calls, stitch the answers together. Here it's one line."

**Then:** click Next.

---

## Step 10 — MariaDB exclusive primitives (05:15 – 05:40)

**Visible:** the MariaDB feature card on the right.
**Action:** mouse-hover the card.

**Voice-over (~25 seconds):**

> "On the right, this card explains what the database is doing. Two database commands: 'AS OF a timestamp', which we used on the slider page, and 'ALL versions', which we just used for the rainbow. Both are unique to MariaDB. A normal database can't do this without bolting on extra software — which means extra cost, extra bugs, extra failures. MariaDB ships it built in."

**Then:** click Next. The tour will navigate to the Coverage Drift page.

---

## Step 11 — The drift methodology (05:40 – 06:10)

**Visible:** the methodology strip with three chips.
**Action:** mouse-hover the chips left to right as you speak.

**Voice-over (~30 seconds):**

> "We're now on the Coverage Drift page — the most important part of the demo. This strip explains the experiment we ran. We trained the AI on six batches of data. The first four use normal noise — the world is calm and predictable. Batches 5 and 6 use much louder noise, simulating something like a fuel-price shock or a new low-cost airline entering the route. Expected result: the first four hold near 90 percent coverage; the last two collapse. Let's see if that actually happened."

**Then:** click Next.

---

## Step 12 — Drift caught by one query (06:10 – 06:55) · THE PUNCHLINE

**Visible:** the two big headline tiles ("4 of 6 calibrated · 91.2%" vs "2 of 6 drift · 58.7%").
**Action:** scroll down once after the voice-over so the per-batch run cards are visible. Hold for 5 seconds.

**Voice-over (~45 seconds):**

> "Here's the answer in two big tiles. Left tile, blue: four of six batches calibrated, averaging 91.2 percent coverage. Right tile, amber: two of six batches collapsed to 58.7 percent. That's more than thirty percentage points below where they should be. The AI broke. And the database caught it — automatically, with no extra code. One SQL query: 'show me the average coverage for every batch ever made'. Done. No MLflow tracking server. No Weights and Biases. No data engineer building a custom dashboard. The database itself is the auditor."

**Then:** click Next.

---

## Step 13 — Winkler interval score (06:55 – 07:25)

**Visible:** the Winkler section with split groups.
**Action:** mouse-hover the calibrated group, then the drift group.

**Voice-over (~30 seconds):**

> "Coverage is one signal. Winkler is another. Coverage tells you 'did the truth land inside the band'. Winkler tells you 'how good was the band' — narrow bands with hits are rewarded, wide or wrong bands are punished. Lower is better. Look — the first four batches sit around 7,300. Batches 5 and 6 jump to 24,000, more than three times worse. Two independent metrics, both pointing to the same conclusion. Both come from the same database, no extra tools."

**Then:** click Next.

---

## Step 14 — Prediction diff between batches (07:25 – 08:15) · LIVE INTERACTION

**Visible:** the Prediction Diff section with three dropdowns.
**Action sequence:**
1. **Click the "Batch A (earlier)" dropdown, pick Run 1 (the earliest batch).**
2. **Click the "Batch B (later)" dropdown, pick Run 5 or Run 6 (a drifted batch).**
3. **Click the Route dropdown, pick a different random route.**
4. The diff chart updates each time. Wait for the bars to render after the third pick.

**Voice-over (~50 seconds):**

> "Now let me show you another live trick. I'll pick two different model versions — Batch A is from earlier, Batch B is from later, after the drift hit. And let me pick a random route too.
>
> [select Batch A → Run 1]
> [select Batch B → Run 5 or 6]
> [select a different route]
>
> Look at the chart now. Each bar is the difference between what Batch A predicted and what Batch B predicted, day by day, on this route. Green bars mean the new model is more optimistic. Orange bars mean less. This is one query — it asks the database for two different snapshots in time and subtracts them. In a normal AI system, you'd be writing custom Python code for an hour to get this view."

**Then:** click Next. The tour navigates to the How It Works page.

---

## Step 15 — Five layers, zero deps (08:15 – 08:45)

**Visible:** the architecture diagram.
**Action:** none — let the diagram speak.

**Voice-over (~30 seconds):**

> "We're now on the final page — How It Works. This diagram shows the entire architecture in five layers: data input at the top, MariaDB in the middle, the AI training layer, the query layer, and the dashboard you're looking at. What's NOT in this diagram is just as important. There's no MLflow. No Weights and Biases. No DataDog. No Evidently AI. The audit trail is structural, not bolted on after the fact."

**Then:** click Next.

---

## Step 16 — Vs. the standard MLOps stack (08:45 – 09:15)

**Visible:** the comparison table.
**Action:** mouse-trace down the right-hand "FlightCast" column row by row.

**Voice-over (~30 seconds):**

> "This table compares us against what the industry usually does. Right column is FlightCast. Middle column is what most companies build today. External tracking server? We don't need one — versioning happens automatically when we INSERT. Custom drift dashboards? We don't need one — one SQL query tells us. Replay infrastructure? We don't need it — the database IS the replay. Every advantage on the right is a problem the database itself solved."

**Then:** click Next.

---

## Step 17 — Five MariaDB only queries (09:15 – 10:30) · LIVE INTERACTION

**Visible:** the Hero SQL section with five collapsed accordions.
**Action sequence:**
1. **Click Query 1 to expand.** Pause for 12 seconds while explaining.
2. **Click Query 1 again to collapse, then click Query 2.** Pause 12 seconds.
3. Repeat for Queries 3, 4, and 5.

**Voice-over (~75 seconds total — pace as you expand each one):**

> "This section shows the five real database queries that power the entire demo. Let me walk through each one.
>
> [click Query 1]
>
> Query 1 — Time travel. Five words: FOR SYSTEM TIME AS OF a date. Returns every prediction the AI made before that date. This is what the slider sends to the database every time you drag it.
>
> [collapse, click Query 2]
>
> Query 2 — Prediction diff. Two AS OF queries joined together. We saw this when we compared Batch A and Batch B.
>
> [collapse, click Query 3]
>
> Query 3 — Full audit log. FOR SYSTEM TIME ALL returns every version of every row, ever. This is what painted the rainbow chart with six model versions.
>
> [collapse, click Query 4]
>
> Query 4 — Calibration drift. The killer demo we just saw. Group every prediction by which batch made it, average the coverage, and you immediately see which batches broke.
>
> [collapse, click Query 5]
>
> Query 5 — Distance. MariaDB has a built-in function that calculates the real-world distance between two airports using their latitude and longitude. We feed this into the AI — longer flights have different demand patterns. Five queries, all unique to MariaDB. None of them run on MySQL or PostgreSQL."

**Then:** click Next.

---

## Step 18 — The conformal math (10:30 – 10:55)

**Visible:** the math section with the formula.
**Action:** mouse-hover the formula box.

**Voice-over (~25 seconds):**

> "Quick math footnote. The formula on screen is what backs the 90 percent guarantee. Don't worry about the symbols — what matters is this: it's a published theorem from 2005, peer-reviewed, used by major banks and insurance companies. We didn't invent it. We applied it on top of MariaDB so the math and the audit trail live in the same place."

**Then:** click Next.

---

## Step 19 — Open infrastructure (10:55 – 11:20)

**Visible:** the closing section with the two judge documents listed.
**Action:** none — let the screen sit.

**Voice-over (~25 seconds):**

> "Final slide. FlightCast is open source — the code is free under the MIT license. Three open issues are listed: per-tier model retraining, real-data prototypes for actual airlines, and Apache Airflow integration. Built by Low Yan Cheng, student ID TP070056, at APU Malaysia, for the MariaDB Hackathon Malaysia 2026. Thanks for watching."

**Then:** click **Finish Tour** in the popover. The tour closes.

---

## Production tips

**Pacing:** if you can read each voice-over comfortably without rushing, you're at the right speed. If you finish before the action is done, hold the silence — silence is professional.

**Don't apologise on camera.** No "sorry, let me find the button". If you fluff a take, mute, restart from the same step. Cuts between steps are invisible in post.

**Mouse cursor:** keep it standard size, don't wave it. When pointing at something, hover near it, not on top of it.

**Audio:** record in a quiet room, mic close to your mouth. Even AirPods Pro outperform a laptop mic if the laptop fan is on.

**Backup take:** record Steps 6 (download flow) and 12 (drift punchline) twice. They're the two most important moments and the hardest to redo cleanly.

**Captions:** add captions in post (Loom does this automatically). International judges skim faster with captions.

---

## What if something breaks live

| Symptom | Recovery |
|---|---|
| Chart doesn't update on slider drag | F5 the page (clears cache, refetches). Re-cue from Step 3. |
| API returns 503 | `docker compose restart api`. Wait 5 seconds. Re-cue. |
| Pitch tour stuck on a step | Click X on the popover, click Start Pitch Tour again, click Next past completed scenes. |
| All-history rainbow doesn't render | Toggle didn't fire — click "All history" again, wait 1 second. |
| Excel takes too long to open the CSV | In post, cut to the Excel screen. Don't apologise on camera. |
| Browser auto-zooms | Ctrl+0 resets. |
| Wrong page when starting a step | Tour will auto-navigate when you click Next. If it doesn't, click the sidebar nav manually — tour state persists. |

---

## Submission package alongside the video

When you upload, include a one-line description and these links:

- **Live demo:** http://localhost:3000 (or your hosted URL)
- **Pitch tour:** click "Start Pitch Tour" in the sidebar — 19 steps, walks the same flow
- **Whitepaper:** `Elegant.md` — the technical paper for stats-literate readers
- **Judge guide:** `docs/JUDGES_TESTING_GUIDE.md` — four time-budget options
- **Demo script (5-min cut):** `docs/DEMO_VIDEO_SCRIPT.md` — the condensed 9-scene version
- **Repo:** https://github.com/MariaDB-Hackathon-MY-2026/flightcast
