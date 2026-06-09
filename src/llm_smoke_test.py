"""LLM-backed smoke test.

This will call the configured provider (Grok if `GROK_API_KEY` present, else OpenAI).
Make sure you have set GROK_API_KEY and either GROK_API_BASE or GROK_API_URL (or use OPENAI_API_KEY).
"""
import sys
from pathlib import Path

# ensure project root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.generator import answer_with_sources


def main():
    q = "Name two safety practices the HBCU Career Center recommends before or during travel abroad."
    print("Running LLM-backed smoke test for query:\n", q)
    out = answer_with_sources(q, k=5)
    print("\nRaw model answer:\n", out.get("raw_answer"))
    print("\nAnnotated answer:\n", out.get("answer"))
    print("\nSources:")
    for s in out.get("sources", []):
        print(f" [{s['index']}] {s['source']}")


if __name__ == '__main__':
    main()
