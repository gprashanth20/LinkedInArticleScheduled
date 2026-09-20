#!/usr/bin/env python3
"""
Weekly LinkedIn article writing brief generator + emailer.

Every Tuesday at 7:00 PM IST, this emails a structured writing brief
covering six angles suited to a consulting / support & operations
professional's visibility (enterprise tech trend, GCC/India support
story, an opinion take, a personal case study, a myth-bust, and a
fintech/banking story), each backed by one real, freshly-fetched news
item pulled via free RSS/Google News (no API key required).

This does NOT write or post the article for you. It hands you a
one-page brief — topic, angle, a real supporting story with a link,
and your own case-study data — so a 600-1000 word (5-10 min read) post
takes a fraction of the usual writing effort, but the actual drafting
and posting to LinkedIn stays in your hands.

Required environment variables:
  GMAIL_ADDRESS        - Gmail address used to send (e.g. yourname@gmail.com)
  GMAIL_APP_PASSWORD   - Gmail app password (not your normal password)
  RECIPIENT_EMAIL      - Destination email address (defaults to g20.pras@gmail.com)
"""

import html
import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from time import mktime
from zoneinfo import ZoneInfo

import feedparser

DEFAULT_RECIPIENT = "g20.pras@gmail.com"
CASE_STUDIES_FILE = Path(__file__).parent / "case_studies.json"

BOILERPLATE_MARKERS = [
    "careers", "contact us", "about us", "disclaimer", "terms of service",
    "terms and conditions", "privacy policy", "advertise with us",
    "sitemap", "subscribe", "newsletter sign", "market research report",
    "market size", "market share", "appoints", "appointed", "to lead",
    "joins as", "named as", "elected as", "press release",
    "expands", "opens global capability", "announces", "launches",
    "concludes", "conclave", "establishes",
]


# The six recurring angles for the post, each with its own feeds,
# required keywords, and a short writing prompt to steer the outline.
ANGLES = [
    {
        "key": "tech_trend",
        "label": "Enterprise Technology Trend",
        "prompt": (
            "Take a position on what this development means for enterprise "
            "IT/consulting delivery over the next 12-18 months. Tie it back "
            "to something concrete you've seen in a client engagement."
        ),
        "feeds": [
            ("Google News", "https://news.google.com/rss/search?q=(Oracle+OR+middleware+OR+%22Java+enterprise%22+OR+WebLogic)&hl=en-US&gl=US&ceid=US:en"),
        ],
        "keywords": [
            "oracle", "middleware", "java", "weblogic", "enterprise software",
            "application server", "integration platform",
        ],
    },
    {
        "key": "gcc_support_story",
        "label": "GCC / India Support Business Story",
        "prompt": (
            "Use this as a jumping-off point to describe a trend you're "
            "seeing first-hand in how GCCs structure support & operations "
            "work in India."
        ),
        "feeds": [
            ("Google News", "https://news.google.com/rss/search?q=(%22global+capability+centre%22+OR+%22global+capability+center%22+OR+GCC)+(support+OR+operations+OR+%22shared+services%22)&hl=en-IN&gl=IN&ceid=IN:en"),
        ],
        "keywords": [
            "gcc", "global capability", "capability centre", "capability center",
            "shared services", "support", "operations",
        ],
    },
    {
        "key": "opinion",
        "label": "Opinion",
        "prompt": (
            "Example angle: \"Why BOT (Build-Operate-Transfer) is replacing "
            "pure outsourcing in 2026.\" Write a confident, specific opinion — "
            "not a survey of both sides. Back it with one client-facing "
            "observation."
        ),
        "feeds": [
            ("Google News", "https://news.google.com/rss/search?q=(%22build-operate-transfer%22+OR+%22build+operate+transfer%22+OR+BOT+model)+outsourcing&hl=en-US&gl=US&ceid=US:en"),
        ],
        "keywords": [
            "build-operate-transfer", "build operate transfer", "bot model",
            "outsourcing", "captive",
        ],
    },
    {
        "key": "case_study",
        "label": "Case Study (anonymised, with measurable outcome)",
        "prompt": (
            "Use the case-study entry below as the backbone: challenge → "
            "approach → measurable outcome. Keep the client anonymised "
            "exactly as written."
        ),
        "feeds": [],
        "keywords": [],
    },
    {
        "key": "myth_bust",
        "label": "Myth-Busting",
        "prompt": (
            "Example angle: \"GCCs are not just about cost anymore.\" Name "
            "the myth explicitly, then dismantle it with a specific "
            "counter-example from current market behavior."
        ),
        "feeds": [
            ("Nasscom Community", "https://news.google.com/rss/search?q=site:community.nasscom.in+GCC&hl=en-IN&gl=IN&ceid=IN:en"),
        ],
        # Nasscom Community publishes analytical GCC pieces (not investment
        # press releases), so a light keyword check is enough here.
        "keywords": [
            "gcc", "global capability", "capability centre", "capability center",
        ],
    },
    {
        "key": "fintech_banking",
        "label": "FinTech / Banking Story",
        "prompt": (
            "Relevant to your NMB/Intuit experience. Connect this story to "
            "a specific operational or support challenge you've helped a "
            "banking/fintech client solve."
        ),
        "feeds": [
            ("Google News", "https://news.google.com/rss/search?q=(fintech+OR+banking)+(automation+OR+%22digital+transformation%22+OR+AI)&hl=en-IN&gl=IN&ceid=IN:en"),
        ],
        "keywords": [
            "fintech", "bank", "banking", "digital transformation",
            "automation", "core banking", "payments",
        ],
    },
]


def is_boilerplate(title: str) -> bool:
    lowered = title.lower()
    return any(marker in lowered for marker in BOILERPLATE_MARKERS)


def split_source_suffix(title: str, fallback_source: str):
    if " - " in title:
        head, _, tail = title.rpartition(" - ")
        if head and len(tail) <= 40 and "?" not in tail and "!" not in tail:
            return head.strip(), tail.strip()
    return title, fallback_source


def entry_timestamp(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            try:
                return mktime(value)
            except (OverflowError, ValueError):
                continue
    return 0


def pick_supporting_story(angle):
    """Returns (title, link, source) for the freshest matching item, or
    None if the angle has no feeds (e.g. the case-study angle) or nothing
    matched."""
    if not angle["feeds"]:
        return None

    candidates = []
    for source, url in angle["feeds"]:
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            print(f"WARN: failed to fetch {source} feed {url}: {exc}", file=sys.stderr)
            continue

        for entry in parsed.entries[:25]:
            raw_title = html.unescape(getattr(entry, "title", "").strip())
            if not raw_title or is_boilerplate(raw_title):
                continue
            title, resolved_source = split_source_suffix(raw_title, source)
            if not title:
                continue

            summary = html.unescape(getattr(entry, "summary", "")).strip()
            text = f"{title} {summary}".lower()
            if not any(kw in text for kw in angle["keywords"]):
                continue

            link = getattr(entry, "link", "")
            candidates.append((entry_timestamp(entry), title, link, resolved_source))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0], reverse=True)
    _, title, link, source = candidates[0]
    return title, link, source


def load_next_case_study():
    """Returns the least-recently-used case study entry, or None."""
    if not CASE_STUDIES_FILE.exists():
        return None

    try:
        data = json.loads(CASE_STUDIES_FILE.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARN: could not read case_studies.json: {exc}", file=sys.stderr)
        return None

    entries = data.get("case_studies", [])
    if not entries:
        return None

    entries.sort(key=lambda e: e.get("used_count", 0))
    chosen = entries[0]
    chosen["used_count"] = chosen.get("used_count", 0) + 1

    try:
        CASE_STUDIES_FILE.write_text(json.dumps(data, indent=2) + "\n")
    except OSError as exc:
        print(f"WARN: could not update case_studies.json usage count: {exc}", file=sys.stderr)

    return chosen


def build_brief():
    """Returns list of dicts, one per angle, with story/case-study data."""
    results = []
    for angle in ANGLES:
        entry = {
            "label": angle["label"],
            "prompt": angle["prompt"],
            "story": None,
            "case_study": None,
        }

        if angle["key"] == "case_study":
            entry["case_study"] = load_next_case_study()
        else:
            entry["story"] = pick_supporting_story(angle)

        results.append(entry)

    return results


def build_html_body(brief) -> str:
    parts = []
    for entry in brief:
        parts.append(f"<h2>{html.escape(entry['label'])}</h2>")
        parts.append(f"<p style=\"color:#444;\"><i>{html.escape(entry['prompt'])}</i></p>")

        if entry["case_study"] is not None:
            cs = entry["case_study"]
            parts.append(
                f"<p><b>Context:</b> {html.escape(str(cs.get('client_context', '')))}<br>"
                f"<b>Challenge:</b> {html.escape(str(cs.get('challenge', '')))}<br>"
                f"<b>Approach:</b> {html.escape(str(cs.get('approach', '')))}<br>"
                f"<b>Measurable outcome:</b> {html.escape(str(cs.get('measurable_outcome', '')))}</p>"
            )
            if "[" in str(cs.get("challenge", "")):
                parts.append(
                    '<p style="color:#b00;">This case study entry still has '
                    "placeholder text — fill in case_studies.json with your "
                    "real anonymised details.</p>"
                )
        elif entry["story"] is not None:
            title, link, source = entry["story"]
            safe_title = html.escape(title)
            safe_source = html.escape(source)
            if link:
                parts.append(f'<p><b><a href="{html.escape(link)}">{safe_title}</a></b></p>')
            else:
                parts.append(f"<p><b>{safe_title}</b></p>")
            parts.append(f'<p style="color:#888; font-size:12px;">Source: {safe_source}</p>')
        else:
            parts.append('<p style="color:#aaa; font-style:italic;">No fresh supporting story found this week — use your own current example.</p>')

    return "\n".join(parts)


def send_email(html_body: str, today_str: str) -> None:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", DEFAULT_RECIPIENT)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"LinkedIn Article Brief - {today_str}"
    msg["From"] = gmail_address
    msg["To"] = recipient

    full_html = f"""\
<html>
  <body style="font-family: Georgia, 'Times New Roman', serif; max-width: 800px; margin: auto; color: #222;">
    <h1 style="border-bottom: 2px solid #333; padding-bottom: 8px;">LinkedIn Article Brief</h1>
    <p style="color: #666;">{today_str} &middot; write and post a 600-1000 word (5-10 min read) article this week</p>
    <p style="color:#666;">
      Six angles below, each with a real, current supporting story (or your
      own case study). Pick one, or weave two or three together, personalise
      with your own NMB/Intuit examples, and post to LinkedIn yourself.
    </p>
    {html_body}
    <hr>
    <p style="font-size: 12px; color: #999;">
      Supporting stories via Google News RSS. Case study rotated from
      case_studies.json. Generated automatically by a scheduled GitHub
      Actions workflow — this is a writing brief, not a finished draft.
    </p>
  </body>
</html>
"""

    msg.attach(MIMEText(full_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [recipient], msg.as_string())


def main() -> int:
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    today_str = ist_now.strftime("%A, %d %B %Y")

    print("Building LinkedIn article brief...")
    brief = build_brief()

    html_body = build_html_body(brief)

    print("Sending email...")
    send_email(html_body, today_str)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
