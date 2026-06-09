"""Smoke test: retrieve top-k chunks for a sample query (no external API keys required).

Run with:
  python3 src/smoke_test.py

This tests local embedding + Chroma retrieval only, so it doesn't require OpenAI/Grok keys.
"""
import sys
from pathlib import Path

# ensure project root is on PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.generator import retrieve_top_k


def main():
    q = "Name two safety practices the HBCU Career Center recommends before or during travel abroad."
    print(f"Running retrieval smoke test for query: {q}\n")
    res = retrieve_top_k(q, k=5, persist_dir="db/chroma", collection="chunks")
    for i, r in enumerate(res, start=1):
        print(f"Rank {i}: id={r['id']} distance={r['distance']:.4f} source={r['metadata'].get('source')}")
        text = r['text']
        print(text[:400].replace('\n', ' ') + ('...' if len(text) > 400 else ''))
        print('\n' + '-'*60 + '\n')


if __name__ == '__main__':
    main()
