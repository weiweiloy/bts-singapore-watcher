"""
Compares the two latest snapshots in snapshots/ and sends a Telegram
status message every run:

  - If a relevant change is detected (Singapore/ticket/Weverse/etc.
    appears in the diff), send a TICKET ALERT message describing
    which Singapore dates appear to have changed.
  - If no relevant change is detected, send a plain status message
    confirming Singapore is still "stay tuned".

Reads two env vars:
  TELEGRAM_BOT_TOKEN  — the bot's API token
  TELEGRAM_CHAT_IDS   — comma-separated list of chat IDs

Designed to be run by GitHub Actions after the fetcher.
"""

import datetime
import difflib
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

SNAPSHOT_DIR = pathlib.Path(__file__).parent.parent / "snapshots"

# Keywords that make a diff line worth alerting on.
ALERT_KEYWORDS = [
    "singapore",
    "ticket",
    "weverse",
    "interpark",
    "klook",
    "on sale",
    "on-sale",
    "pre-sale",
    "presale",
    "national stadium",
    "indoor stadium",
]

# Singapore dates we are watching.
SINGAPORE_DATES = [
    "DECEMBER 17, 2026",
    "DECEMBER 19, 2026",
    "DECEMBER 20, 2026",
    "DECEMBER 22, 2026",
]


def latest_two_snapshots() -> list[pathlib.Path]:
    files = sorted(SNAPSHOT_DIR.glob("*.txt"))
    return files[-2:] if len(files) >= 2 else files


def relevant_diff_lines(old_lines: list[str], new_lines: list[str]) -> list[str]:
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
    relevant = []
    for line in diff:
        if not (line.startswith("+") or line.startswith("-")):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in ALERT_KEYWORDS):
            relevant.append(line)
    return relevant


def changed_singapore_dates(new_text: str) -> list[str]:
    """Return Singapore dates whose entry no longer says STAY TUNED."""
    changed = []
    for date in SINGAPORE_DATES:
        # Look for the date, then capture what follows up to the next blank
        # line or end of relevant block. The site lists each entry as:
        #   DECEMBER 17, 2026
        #   SINGAPORE
        #   STAY TUNED  (or, when tickets are live, something else)
        pattern = re.compile(
            re.escape(date) + r"\s*\n\s*SINGAPORE\s*\n\s*([^\n]+)",
            re.IGNORECASE,
        )
        match = pattern.search(new_text)
        if match:
            status = match.group(1).strip()
            if status.upper() != "STAY TUNED":
                changed.append(f"{date}: {status}")
    return changed


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        response.read()


def build_status_message(snapshot_date: str) -> str:
    return (
        f"📅 {snapshot_date}\n"
        f"BTS Singapore tickets: still 'STAY TUNED' across all four dates "
        f"(17, 19, 20, 22 Dec 2026)."
    )


def build_alert_message(
    snapshot_date: str,
    changed_dates: list[str],
    diff_lines: list[str],
) -> str:
    if changed_dates:
        # A Singapore date has actually flipped on the live page right now.
        lines = [
            "🚨🚨🚨 TICKET ALERT 🚨🚨🚨",
            "🎟️🎟️🎟️ BTS SINGAPORE 🎟️🎟️🎟️",
            "",
            f"📅 Snapshot: {snapshot_date}",
            "",
            "✨ Dates no longer 'STAY TUNED':",
        ]
        for entry in changed_dates:
            lines.append(f"  🎉 {entry}")
        lines.append("")
        lines.append("💜 Go check Claude for the full analysis. 💜")
    else:
        # The page changed in some keyword-relevant way, but no Singapore
        # date is currently showing anything other than STAY TUNED.
        lines = [
            "👀 Heads up",
            "",
            f"📅 Snapshot: {snapshot_date}",
            "",
            "Something on the BTS tour page changed (a ticket-related word "
            "appeared or disappeared in today's snapshot), but all four "
            "Singapore dates still say 'STAY TUNED'.",
            "",
            "Could be a change elsewhere on the page (another city flipped, "
            "or wording was updated). Worth a quick look:",
            "https://ibighit.com/en/bts/tour/",
        ]
    return "\n".join(lines)[:3800]

def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids_raw = os.environ.get("TELEGRAM_CHAT_IDS", "")
    if not token or not chat_ids_raw:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_IDS not set.", file=sys.stderr)
        return 1
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]

    snapshots = latest_two_snapshots()
    if not snapshots:
        print("No snapshots at all; nothing to do.")
        return 0

    new_path = snapshots[-1]
    new_text = new_path.read_text(encoding="utf-8")
    snapshot_date = new_path.stem  # e.g. "2026-05-17"

    # If we don't have two snapshots yet, just send the status message.
    if len(snapshots) < 2:
        message = build_status_message(snapshot_date)
    else:
        old_path = snapshots[-2]
        old_lines = old_path.read_text(encoding="utf-8").splitlines()
        new_lines = new_text.splitlines()
        diff_lines = relevant_diff_lines(old_lines, new_lines)

        if not diff_lines:
            message = build_status_message(snapshot_date)
        else:
            changed = changed_singapore_dates(new_text)
            message = build_alert_message(snapshot_date, changed, diff_lines)

    for chat_id in chat_ids:
        try:
            send_telegram_message(token, chat_id, message)
            print(f"Message sent to {chat_id}.")
        except Exception as exc:
            print(f"Failed to send to {chat_id}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())