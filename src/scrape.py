#!/usr/bin/env python3
"""Simple scraper: load local documents and fetch URLs from data/sources.json
and write raw text per source to a JSONL file.
"""
import argparse
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path


def clean_html(html: str) -> str:
    """Extract human-readable text from HTML.

    Strategy:
    - Prefer `<article>` if present
    - Otherwise join visible `<p>` tags
    - Fall back to full text with scripts/styles removed
    - Normalize whitespace and unicode
    """
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for s in soup(["script", "style", "noscript"]):
            s.extract()

        # Prefer main/article content
        article = soup.find("article")
        if article:
            paragraphs = [p.get_text(separator=" ") for p in article.find_all("p")]
            if paragraphs:
                text = "\n\n".join(p.strip() for p in paragraphs if p.strip())
            else:
                text = article.get_text(separator=" ")
        else:
            # Gather <p> tags across the page and pick the largest continuous block
            p_tags = [p.get_text(separator=" ").strip() for p in soup.find_all("p")]
            p_tags = [p for p in p_tags if p]
            if p_tags:
                text = "\n\n".join(p_tags)
            else:
                text = soup.get_text(separator=" ")

        # Normalize whitespace and unicode
        text = unicodedata.normalize("NFKC", text)
        # collapse multiple spaces but keep paragraph breaks
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
        return text.strip()
    except Exception:
        # Fallback: rough tag removal
        text = re.sub(r"<(script|style).*?>.*?</\1>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def fetch_url(url: str, headers=None, retries=2, timeout=15):
    """Fetch URL with a user-agent, retries, and fallbacks. Returns dict with
    keys: text, status, error, headers_bytes
    """
    headers = headers or {"User-Agent": "ai201-scraper/1.0 (+https://github.com)"}

    # Try requests + Retry (if available)
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util import Retry

        session = requests.Session()
        retries_policy = Retry(total=retries, backoff_factor=0.5, status_forcelist=[429,500,502,503,504])
        session.mount("https://", HTTPAdapter(max_retries=retries_policy))
        session.mount("http://", HTTPAdapter(max_retries=retries_policy))
        r = session.get(url, headers=headers, timeout=timeout)
        status = getattr(r, 'status_code', None)
        r.raise_for_status()
        return {"text": r.text, "status": status, "error": None, "raw": r.content}
    except Exception as e:
        # Fallback to urllib with simple retries
        last_err = None
        for attempt in range(retries + 1):
            try:
                from urllib.request import Request, urlopen

                req = Request(url, headers=headers or {})
                with urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    status = getattr(resp, 'status', None)
                    try:
                        text = raw.decode('utf-8')
                    except Exception:
                        text = raw.decode('latin-1', errors='ignore')
                    return {"text": text, "status": status, "error": None, "raw": raw}
            except Exception as err:
                last_err = err
                time.sleep(0.5 * (attempt + 1))
        return {"text": "", "status": None, "error": str(last_err), "raw": b""}


def load_local_documents(doc_dir: Path):
    docs = []
    if not doc_dir.exists():
        return docs
    for p in sorted(doc_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".txt", ".md"):
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                text = p.read_text(encoding="latin-1")
            docs.append((str(p), text))
    return docs


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    # Replace Windows newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Trim leading/trailing whitespace on each line
    lines = [ln.strip() for ln in text.split('\n')]
    # Collapse multiple blank lines to two (paragraph separator)
    out_lines = []
    blank = 0
    for ln in lines:
        if ln == "":
            blank += 1
        else:
            if blank > 0:
                out_lines.append("")
            out_lines.append(ln)
            blank = 0
    return "\n\n".join(out_lines).strip()


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="data/sources.json")
    parser.add_argument("--out", default="data/raw_texts.jsonl")
    parser.add_argument("--docs", default="documents")
    parser.add_argument("--fetch", action="store_true", help="Fetch remote URLs")
    parser.add_argument("--save-html", action="store_true", help="Save HTML snapshots to data/raw_html/")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sources = []
    sfile = Path(args.sources)
    if sfile.exists():
        try:
            sources = json.loads(sfile.read_text(encoding="utf-8"))
        except Exception:
            sources = json.loads(sfile.read_text(encoding="latin-1"))

    results = []

    # local docs
    for path, text in load_local_documents(Path(args.docs)):
        normalized = normalize_text(text)
        results.append({
            "id": sha1(path + "\n"),
            "source": path,
            "title": Path(path).name,
            "text": normalized,
            "fetched": False,
            "status": None,
            "error": None,
        })

    # remote sources
    for src in sources:
        if not isinstance(src, str):
            continue
        entry = {"id": sha1(src), "source": src, "title": None, "text": "", "fetched": False, "status": None, "error": None}
        if src.startswith("http"):
            if args.fetch:
                res = fetch_url(src)
                entry["status"] = res.get("status")
                entry["error"] = res.get("error")
                if res.get("text"):
                    text = clean_html(res.get("text"))
                    entry["text"] = normalize_text(text)
                    # try to extract title from the HTML quickly
                    try:
                        from bs4 import BeautifulSoup

                        soup = BeautifulSoup(res.get("text"), "html.parser")
                        title_tag = soup.find("title")
                        if title_tag and title_tag.string:
                            entry["title"] = title_tag.string.strip()
                        else:
                            og = soup.find("meta", property="og:title")
                            if og and og.get("content"):
                                entry["title"] = og.get("content").strip()
                    except Exception:
                        pass
                    entry["fetched"] = True
                    # save raw html snapshot if requested
                    if args.save_html:
                        raw_dir = Path("data/raw_html")
                        raw_dir.mkdir(parents=True, exist_ok=True)
                        html_path = raw_dir / (entry["id"] + ".html")
                        try:
                            html_path.write_bytes(res.get("raw") or b"")
                        except Exception:
                            try:
                                html_path.write_text(res.get("text") or "", encoding='utf-8')
                            except Exception:
                                pass
            else:
                # not fetched: leave placeholder text empty
                pass
        results.append(entry)

    with out_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(results)} raw documents to {out_path}")


if __name__ == "__main__":
    main()
