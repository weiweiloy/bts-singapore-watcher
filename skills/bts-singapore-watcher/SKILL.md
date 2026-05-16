---
name: bts-singapore-watcher
description: Use this skill when the user asks whether BTS have updated their Singapore tour status, whether tickets have gone on sale for any of the Singapore dates (17, 19, 20, or 22 December 2026), or for a summary of what's changed on the Big Hit Entertainment tour page. The skill reads daily text snapshots of https://ibighit.com/en/bts/tour/ stored in the snapshots/ folder and compares the most recent snapshot to the previous one to identify changes, with particular attention to the Singapore tour status.
---

# BTS Singapore Watcher

## Context

The user is watching for BTS to release ticket sale details for their Singapore tour dates as part of the 2026 BTS World Tour 'ARIRANG'. As of the start of this watch, the Big Hit tour page lists four Singapore dates — 17, 19, 20, and 22 December 2026 — all marked "STAY TUNED" rather than showing ticket sale information. The user wants to know the moment any of those four entries changes.

Other Asian-leg dates also marked "STAY TUNED" at the start of the watch include: Kaohsiung (Nov 19, 21, 22), Bangkok (Dec 3, 5, 6), Kuala Lumpur (Dec 12, 13), Jakarta (Dec 26, 27), Melbourne (Feb 12, 13 2027), Sydney (Feb 20, 21 2027), Hong Kong (Mar 4, 6, 7 2027), and Manila (Mar 13, 14 2027). The skill focuses on Singapore but may mention changes to other STAY TUNED cities in passing.

## How to respond

1. Look in the `snapshots/` folder for the two most recently dated `.txt` files.
2. Read both in full.
3. Compare them. Identify:
   - Any text present in the most recent snapshot that was not in the previous one.
   - Any text that was in the previous snapshot but is now gone.
   - Specifically, any change to the entries for Singapore (17, 19, 20, or 22 December 2026).
4. Report findings as follows:
   - If all four Singapore entries still say "STAY TUNED", say plainly: no change, still stay tuned across all four dates.
   - If any Singapore entry has changed, quote the new text briefly (under 15 words) and flag it as a potential ticket release signal.
   - If other STAY TUNED cities have flipped, mention them in a single line at the end.
5. Always state the date of the snapshot you are reporting from.

## Guardrails

- Do not invent excitement. If nothing has changed, say nothing has changed.
- Do not speculate about when tickets will be released. Only report what the snapshots actually say.
- If you can only find one snapshot file (i.e. this is the first run), report the current Singapore status without claiming a change.
- If the snapshot file is empty or looks malformed, say so — do not guess at the content.
- The site renders every entry twice (a quirk of the page's HTML). Treat consecutive duplicate lines as one entry, not two.

## Reference material

See `reference/known-tour-patterns.md` for notes on how Big Hit typically signals a transition from "STAY TUNED" to actual ticket sales.
