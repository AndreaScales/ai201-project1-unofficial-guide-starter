"""Run a set of queries through the retrieval+LLM pipeline and rate outputs.

Usage:
  python3.11 scripts/query_eval.py

The script calls `answer_with_sources` and classifies results as:
 - GOOD: contains inline numeric citations and has at least one source
 - BAD: model returned the exact 'I don't know based on the provided sources.'
        or no sources were associated

Adjust `QUERIES` below to test different inputs.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.generator import answer_with_sources

QUERIES = [
    # Likely present in dataset used by the smoke test
    "Name two safety practices the HBCU Career Center recommends before or during travel abroad.",
    # Repository-specific question likely grounded in local docs
    "What is the purpose of the file ingest.py in this project?",
    # Intentionally unanswerable to check fallback
    "What is the capital city of Mars?"
]

def rate_result(out: dict) -> str:
    raw = (out.get('raw_answer') or '').strip()
    annotated = (out.get('answer') or '').strip()
    sources = out.get('sources') or []

    if raw == "I don't know based on the provided sources.":
        return 'BAD'
    if not sources:
        return 'BAD'
    # look for numeric citations like [1]
    if '[' in annotated and ']' in annotated:
        return 'GOOD'
    return 'BAD'


def print_result(q: str, out: dict):
    print('\n' + '='*80)
    print('QUERY:')
    print(q)
    print('\nRAW ANSWER:')
    print(out.get('raw_answer'))
    print('\nANNOTATED ANSWER:')
    print(out.get('answer'))
    print('\nSOURCES:')
    for s in out.get('sources', []):
        print(f"  [{s.get('index')}] {s.get('source')}")
    print('\nRETRIEVED CHUNKS:')
    for r in out.get('retrieved', []):
        meta = r.get('metadata', {})
        print(f"  id={r.get('id')} source={meta.get('source')} dist={r.get('distance')}")
    print('\nRATING:', rate_result(out))


def main():
    for q in QUERIES:
        out = answer_with_sources(q, k=5)
        print_result(q, out)

if __name__ == '__main__':
    main()
