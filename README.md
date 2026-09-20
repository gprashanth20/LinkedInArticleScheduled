# LinkedIn Article Brief — Tuesdays 7:00 PM IST

**This does not write or post your LinkedIn article for you.** It emails
you a one-page writing brief every Tuesday at 7:00 PM IST, cutting the
research/topic-picking effort so a 600-1000 word (5-10 min read) post
takes a fraction of the usual time. You still write and post it — that
part is intentionally kept in your hands, since a consistent, credible
LinkedIn presence needs your own voice and judgment, and LinkedIn's API
doesn't support unattended third-party posting to a personal profile
anyway.

It's free to run: RSS-based, no API keys or paid services, delivered via
Gmail SMTP.

## What the brief contains

Six angles, each with either a real, freshly-fetched supporting story
(via free Google News RSS — no API key required) or your own rotated
case-study entry:

1. **Enterprise Technology Trend** — Oracle, middleware, Java
2. **GCC / India Support Business Story**
3. **Opinion** — e.g. "Why BOT is replacing pure outsourcing in 2026"
4. **Case Study** — pulled from `case_studies.json` (your own anonymised
   NMB/Intuit anecdotes)
5. **Myth-Busting** — e.g. "GCCs are not just about cost anymore"
6. **FinTech / Banking Story** — relevant to NMB/Intuit experience

Pick one angle, or weave two or three together, personalise with your
own specific examples, write the 600-1000 word post, and publish it to
LinkedIn yourself.

## One-time setup

1. **Create a Gmail App Password** (do NOT use your real Gmail
   password):
   - Enable 2-Step Verification on the sending Gmail account:
     https://myaccount.google.com/security
   - Create an app password: https://myaccount.google.com/apppasswords
   - Copy the 16-character password it gives you.

2. **Add repository secrets** (Settings → Secrets and variables →
   Actions → New repository secret):
   | Secret name | Value |
   |---|---|
   | `GMAIL_ADDRESS` | the Gmail address that will send the email |
   | `GMAIL_APP_PASSWORD` | the 16-character app password from step 1 |
   | `RECIPIENT_EMAIL` | where you want the brief sent |

3. **Fill in your case studies** — edit
   [`case_studies.json`](case_studies.json) and replace the bracketed
   placeholder text with your own real, anonymised NMB/Intuit stories:

   ```json
   {
     "id": "example-1",
     "client_context": "A leading East African bank (anonymised NMB engagement)",
     "challenge": "Support ticket backlog was growing 20% quarter over quarter as transaction volume scaled",
     "approach": "Introduced a BOT-based L1 triage layer with automated categorisation before human handoff",
     "measurable_outcome": "Cut average ticket resolution time by 35% within two quarters",
     "used_count": 0
   }
   ```

   Add as many entries as you like — the script always picks the
   least-recently-used one, and updates `used_count` after each run so
   you don't repeat the same story two weeks running. The workflow
   commits that updated count back to the repo automatically.

   If an entry still contains `[bracketed placeholder text]` when the
   brief runs, the email flags it in red so you know to go fill it in.

4. Done. The workflow runs automatically every Tuesday at 7:00 PM IST.

## Running manually

Go to the repo's **Actions** tab → **LinkedIn Article Brief** → **Run
workflow**. Runs immediately, no code changes needed.

## Running locally

```bash
pip install -r requirements.txt

export GMAIL_ADDRESS=you@gmail.com
export GMAIL_APP_PASSWORD=your16charapppassword
export RECIPIENT_EMAIL=you@example.com

python send_linkedin_brief.py
```

Note: running it locally also updates `case_studies.json`'s usage
counts on disk, same as a real run would.

## Customizing

- **Angles, feeds, and keywords**: edit the `ANGLES` list in
  `send_linkedin_brief.py` — each angle has its own `feeds`, `keywords`,
  and writing `prompt`.
- **Case studies**: edit `case_studies.json` directly — add, remove, or
  rewrite entries any time.
- **Schedule**: edit the cron expression in
  `.github/workflows/linkedin-brief.yml` (cron is in UTC; IST =
  UTC+5:30). Cron day-of-week `2` = Tuesday.
- **Recipient**: change the `RECIPIENT_EMAIL` secret, or the
  `DEFAULT_RECIPIENT` fallback in `send_linkedin_brief.py`.
