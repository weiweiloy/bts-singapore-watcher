"""
Compares the two latest snapshots in snapshots/. If meaningful changes
are detected (additions or removals involving Singapore or other
ticket-release keywords), sends a Telegram alert to all configured
chat IDs.

Reads two env vars:
  TELEGRAM_BOT_TOKEN  — the bot's API token
  TELEGRAM_CHAT_IDS   — comma-separated list of chat IDs

Designed to be run by GitHub Actions after the fetcher.
Exits 0 whether or not an alert was sent (no alert is not an error).
"""

import difflib
import os
import pathlib
import sys
import urllib.parse
import urllib.request

SNAPSHOT_DIR = pathlib.Path(__file__).parent.parent / "snapshots"

# Keywords that make a diff line worth alerting on.
# Case-insensitive matching is applied below.
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


def latest_two_snapshots() -> list[pathlib.Path]:
    files = sorted(SNAPSHOT_DIR.glob("*.txt"))
    return files[-2:] if len(files) >= 2 else files


def relevant_diff_lines(old_lines: list[str], new_lines: list[str]) -> list[str]:
    """Return diff lines containing any alert keyword."""
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
    relevant = []
    for line in diff:
        # Only consider added/removed lines, not headers or context
        if not (line.startswith("+") or line.startswith("-")):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in ALERT_KEYWORDS):
            relevant.append(line)
    return relevant


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        response.read()  # discard, but ensures completion


def main() -> int:
    snapshots = latest_two_snapshots()
    if len(snapshots) < 2:
        print("Fewer than two snapshots; nothing to compare.")
        return 0

    old_path, new_path = snapshots
    old_lines = old_path.read_text(encoding="utf-8").splitlines()
    new_lines = new_path.read_text(encoding="utf-8").splitlines()

    relevant = relevant_diff_lines(old_lines, new_lines)
    if not relevant:
        print(f"No relevant changes between {old_path.name} and {new_path.name}.")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids_raw = os.environ.get("TELEGRAM_CHAT_IDS", "")
    if not token or not chat_ids_raw:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_IDS not set.", file=sys.stderr)
        return 1
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]

    # Cap message length for Telegram (4096-char limit; we leave headroom).
    summary_lines = [
        "girlwithticket: BTS tour page changed.",
        f"Compared {old_path.name} → {new_path.name}.",
        "",
        "Relevant diff lines:",
    ]
    summary_lines.extend(relevant[:40])
    if len(relevant) > 40:
        summary_lines.append(f"...and {len(relevant) - 40} more line(s).")
    summary_lines.append("")
    summary_lines.append("Ask Claude in the project for the full analysis.")

    message = "\n".join(summary_lines)[:3800]

    for chat_id in chat_ids:
        try:
            send_telegram_message(token, chat_id, message)
            print(f"Alert sent to {chat_id}.")
        except Exception as exc:
            print(f"Failed to send to {chat_id}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())