#!/usr/bin/env python3
"""Clean raw texts by removing common boilerplate and navigation noise.

Reads JSONL from `--in` (default `data/raw_texts.jsonl`) and writes cleaned
JSONL to `--out` (default `data/clean_texts.jsonl`).
"""
import argparse
import json
import re
from pathlib import Path
from typing import List


BOILERPLATE_PATTERNS = [
    r"skip to content",
    r"subscribe",
    r"join (the )?newsletter",
    r"sign up",
    r"cookie",
    r"privacy policy",
    r"terms of service",
    r"read more",
    r"continue reading",
    r"share( this)?",
    r"share on",
    r"facebook",
    r"twitter",
    r"linkedin",
    r"pinterest",
    r"instagram",
    r"comments",
    r"leave a comment",
    r"related posts",
    r"©",
    r"all rights reserved",
    r"advertis",
    r"sponsored",
    r"powered by",
    r"newsletter",
    r"subscribe to",
    r"get the scoop",
    r"shop",
    r"buy now",
    r"advertisement",
    r"ads by",
    r"click here",
    r"quick links",
    r"search",
    r"menu",
    r"skip to",
    r"cookie policy",
    r"cookie settings",
    r"accept cookies",
    r"comments are closed",
    r"posted on",
    r"last updated",
]


def is_boilerplate_para(p: str) -> bool:
    lp = p.lower()
    # short nav-like paragraphs
    if len(lp) < 40:
        # if it's like 'Home', 'Menu', 'Contact' etc.
        if re.fullmatch(r"[\w\s\-|]{1,40}", lp) and len(lp.split()) <= 3:
            # keep short lines that explicitly look like review metadata
            if re.search(r"professor|dr\.|dr |course|course\s+\d|instructor|rating|review|grade|score|prof\.", lp):
                return False
            return True

    # boilerplate phrases
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, lp):
            return True

    # lines that are just social icons or counters
    if re.search(r"\b\d+ (likes|shares|comments|views)\b", lp):
        return True

    # lines that contain many repeated short tokens (nav bars)
    tokens = re.findall(r"\w+", lp)
    if len(tokens) > 0 and len(set(tokens)) <= 3 and len(tokens) > 8:
        return True

    return False


def keep_short_para(p: str) -> bool:
    """Decide whether to keep a short paragraph even if short."""
    lp = p.lower()
    if re.search(r"professor|dr\.|dr |prof\.|instructor|course\s+\d|course:|course\b|syllabus|assignment|exam|grade", lp):
        return True
    if re.search(r"\b\d{3,}\b", p):
        return True
    # names like 'John Smith' (two capitalized words)
    if re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", p):
        return True
    return False


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Normalize some unicode whitespace
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # split into paragraphs by two or more newlines
    paras: List[str] = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    cleaned: List[str] = []
    for p in paras:
        # Remove common short noisy prefixes
        p = re.sub(r"^\s*(read more[:\-]?|continue reading[:\-]?|posted on[:\-]?|last updated[:\-]?).*", "", p, flags=re.I)
        if not p:
            continue
        if is_boilerplate_para(p):
            # if short but contains course/prof info, keep
            if len(p) < 80 and keep_short_para(p):
                cleaned.append(p)
            else:
                continue
        else:
            # remove share lines inside paragraph
            p = re.sub(r"share( this)?[:]?\s*([A-Za-z0-9\s,]+)?", "", p, flags=re.I)
            # remove 'Continue Reading' trailing fragments
            p = re.sub(r"(continue reading|read more).*$", "", p, flags=re.I)
            # strip excessive whitespace
            p = re.sub(r"\s+", " ", p).strip()
            if p:
                cleaned.append(p)

    # Deduplicate consecutive identical paragraphs
    final: List[str] = []
    for p in cleaned:
        if not final or p != final[-1]:
            final.append(p)

    result = "\n\n".join(final).strip()

    # Fallback: if filtering removed everything, try a looser extraction
    if not result:
        candidates = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
        candidates = [p for p in candidates if len(p) > 80 and not is_boilerplate_para(p)]
        if not candidates:
            # as last resort, take the longest non-empty lines
            candidates = sorted([p for p in re.split(r"\n+", text) if p.strip()], key=lambda x: len(x), reverse=True)
        # take top 5 candidates
        take = candidates[:5]
        result = "\n\n".join(take).strip()

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", default="data/raw_texts.jsonl")
    parser.add_argument("--out", default="data/clean_texts.jsonl")
    args = parser.parse_args()

    infile = Path(args.infile)
    outfile = Path(args.out)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with infile.open("r", encoding="utf-8") as inf, outfile.open("w", encoding="utf-8") as outf:
        for line in inf:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            raw = obj.get("text") or ""
            cleaned = clean_text(raw)
            out = {
                "id": obj.get("id"),
                "source": obj.get("source"),
                "title": obj.get("title"),
                "clean_text": cleaned,
                "fetched": obj.get("fetched", False),
                "status": obj.get("status"),
                "error": obj.get("error"),
            }
            outf.write(json.dumps(out, ensure_ascii=False) + "\n")
            count += 1

    print(f"Wrote {count} cleaned documents to {outfile}")


if __name__ == "__main__":
    main()
