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

# Months we expect to see as headers in the BTS tour page text.
MONTHS = (
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
)


def find_context_for_line(text: str, target: str) -> str:
    """
    Given the full snapshot text and a target line, find the nearest
    preceding date and city so we can say 'this changed in the
    Singapore December 17 entry'.

    Returns a short context string like 'DECEMBER 17, 2026 — SINGAPORE'
    or an empty string if no context can be found.
    """
    lines = text.splitlines()
    target_clean = target.strip()

    # Find the line in the snapshot
    target_index = None
    for i, line in enumerate(lines):
        if line.strip() == target_clean:
            target_index = i
            break

    if target_index is None:
        return ""

    # Walk backwards looking for a date line, then take the line after it
    # (which is the city per the page's structure: DATE / CITY / STATUS).
    date_line = None
    city_line = None
    for j in range(target_index - 1, max(target_index - 10, -1), -1):
        candidate = lines[j].strip()
        if candidate.upper().startswith(MONTHS):
            date_line = candidate
            # The city is the line immediately after the date
            if j + 1 < len(lines):
                city_line = lines[j + 1].strip()
            break

    if date_line and city_line:
        return f"{date_line} — {city_line}"
    if date_line:
        return date_line
    return ""

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
    old_text: str,
    new_text: str,
) -> str:
    if changed_dates:
        lines = [
            "🚨🚨🚨 TICKET ALERT 🚨🚨🚨",
            "🎟️🎟️🎟️ BTS SINGAPORE 🎟️🎟️🎟️",
            "",
            f"📅 Snapshot: {snapshot_date}",
            "",
            "✨ Singapore dates no longer 'STAY TUNED':",
        ]
        for entry in changed_dates:
            lines.append(f"  🎉 {entry}")
        lines.append("")
        lines.append("💜 Go check Claude for the full analysis. 💜")
        return "\n".join(lines)[:3800]

    added_entries = []
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            text = line[1:].strip()
            context = find_context_for_line(new_text, text)
            if context:
                added_entries.append(f"{context}: {text}")
            else:
                added_entries.append(text)

    removed_entries = []
    for line in diff_lines:
        if line.startswith("-") and not line.startswith("---"):
            text = line[1:].strip()
            context = find_context_for_line(old_text, text)
            if context:
                removed_entries.append(f"{context}: {text}")
            else:
                removed_entries.append(text)

    lines = [
        "👀 Heads up",
        "",
        f"📅 Snapshot: {snapshot_date}",
        "",
        "All four Singapore dates still say 'STAY TUNED' on the live page right now.",
        "",
        "But the page wording changed in a ticket-related way since the last snapshot:",
        "",
    ]
    if added_entries:
        lines.append("➕ Newly appearing:")
        for entry in added_entries[:10]:
            lines.append(f"   {entry}")
        if len(added_entries) > 10:
            lines.append(f"   ...and {len(added_entries) - 10} more.")
        lines.append("")
    if removed_entries:
        lines.append("➖ Disappeared:")
        for entry in removed_entries[:10]:
            lines.append(f"   {entry}")
        if len(removed_entries) > 10:
            lines.append(f"   ...and {len(removed_entries) - 10} more.")
        lines.append("")
    lines.append("Page: https://ibighit.com/en/bts/tour/")
    return "\n".join(lines)[:3800]

    # Otherwise: keywords appeared/disappeared in the diff, but no Singapore
    # date is currently on sale. Show what actually changed so the user can
    # see it for themselves.
    added = [l[1:].strip() for l in diff_lines if l.startswith("+")]
    removed = [l[1:].strip() for l in diff_lines if l.startswith("-")]

    lines = [
        "👀 Heads up",
        "",
        f"📅 Snapshot: {snapshot_date}",
        "",
        "All four Singapore dates still say 'STAY TUNED' on the live page right now.",
        "",
        "But the page wording changed in a ticket-related way since the last snapshot:",
        "",
    ]
    if added:
        lines.append("➕ Newly appearing lines:")
        for entry in added[:10]:
            lines.append(f"   {entry}")
        if len(added) > 10:
            lines.append(f"   ...and {len(added) - 10} more.")
        lines.append("")
    if removed:
        lines.append("➖ Lines that disappeared:")
        for entry in removed[:10]:
            lines.append(f"   {entry}")
        if len(removed) > 10:
            lines.append(f"   ...and {len(removed) - 10} more.")
        lines.append("")
    lines.append("Page: https://ibighit.com/en/bts/tour/")
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
            message = build_alert_message(
                snapshot_date, changed, diff_lines,
                old_text=old_path.read_text(encoding="utf-8"),
                new_text=new_text,
            )

    for chat_id in chat_ids:
        try:
            send_telegram_message(token, chat_id, message)
            print(f"Message sent to {chat_id}.")
        except Exception as exc:
            print(f"Failed to send to {chat_id}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
