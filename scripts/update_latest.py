#!/usr/bin/env python3
"""Refresh LATEST.md with the newest bioRxiv preprints in selected categories.

Runs weekly from .github/workflows/latest.yml. Standard library only.
"""
import datetime as dt
import json
import sys
import urllib.request

CATEGORIES = {
    "genomics": "🧬 Genomics",
    "synthetic biology": "🛠️ Synthetic Biology",
    "bioinformatics": "💻 Bioinformatics",
    "bioengineering": "⚙️ Bioengineering",
    "cancer biology": "🎯 Cancer Biology",
    "immunology": "🛡️ Immunology",
    "microbiology": "🦠 Microbiology",
    "molecular biology": "🔬 Molecular Biology",
}
PER_CATEGORY = 8
MAX_PAGES = 40  # 100 records per page
UA = {"User-Agent": "Awesome-Biotechnology-feed (github.com/Subhadeep998)"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def collect(start, end):
    items, cursor = [], 0
    for _ in range(MAX_PAGES):
        data = fetch(f"https://api.biorxiv.org/details/biorxiv/{start}/{end}/{cursor}/json")
        batch = data.get("collection", [])
        if not batch:
            break
        items.extend(batch)
        total = int(data.get("messages", [{}])[0].get("total", 0) or 0)
        cursor += len(batch)
        if cursor >= total:
            break
    return items


def first_author(authors):
    names = [a.strip() for a in (authors or "").split(";") if a.strip()]
    if not names:
        return "Unknown"
    return names[0] + (" et al." if len(names) > 1 else "")


def render(items, start, end):
    by_cat = {k: [] for k in CATEGORIES}
    seen = set()
    for it in sorted(items, key=lambda x: x.get("date", ""), reverse=True):
        cat = (it.get("category") or "").strip().lower()
        doi = it.get("doi")
        if cat in by_cat and doi not in seen and len(by_cat[cat]) < PER_CATEGORY:
            seen.add(doi)
            by_cat[cat].append(it)

    lines = [
        "# 🆕 Latest in Biotechnology",
        "",
        f"> Newest bioRxiv preprints, **{start} → {end}**. Refreshed automatically every Monday.",
        "> Preprints are **not peer-reviewed** — read critically.",
        "",
        "[← Back to Awesome Biotechnology](README.md)",
        "",
    ]
    for key, label in CATEGORIES.items():
        rows = by_cat[key]
        if not rows:
            continue
        lines += [f"## {label}", "", "| Date | Preprint | First author |", "|:--|:--|:--|"]
        for it in rows:
            title = " ".join((it.get("title") or "").split()).replace("|", "\\|")
            url = f"https://www.biorxiv.org/content/{it.get('doi')}v{it.get('version', 1)}"
            lines.append(f"| {it.get('date', '')} | [{title}]({url}) | {first_author(it.get('authors')).replace('|', '')} |")
        lines.append("")
    lines += ["---", f"<sub>Source: bioRxiv public API · generated {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC</sub>", ""]
    return "\n".join(lines)


def main():
    end = dt.date.today()
    start = end - dt.timedelta(days=7)
    try:
        items = collect(start.isoformat(), end.isoformat())
    except Exception as exc:  # keep the previous file if the API is down
        print(f"bioRxiv fetch failed: {exc}", file=sys.stderr)
        return 0
    if not items:
        print("No items returned; leaving LATEST.md unchanged.")
        return 0
    with open("LATEST.md", "w", encoding="utf-8") as f:
        f.write(render(items, start, end))
    print(f"Wrote LATEST.md from {len(items)} records.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
