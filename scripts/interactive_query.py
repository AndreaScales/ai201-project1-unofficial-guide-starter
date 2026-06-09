"""Interactive query runner for retrieval + LLM pipeline.

Run:
  python3.11 scripts/interactive_query.py

Type a question and press Enter. Leave blank or type 'quit' to exit.
"""
import sys
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv('.env')

from src.generator import answer_with_sources


def rate_result(out: dict) -> str:
    raw = (out.get('raw_answer') or '').strip()
    annotated = (out.get('answer') or '').strip()
    sources = out.get('sources') or []

    if raw == "I don't know based on the provided sources.":
        return 'BAD'
    if not sources:
        return 'BAD'
    if '[' in annotated and ']' in annotated:
        return 'GOOD'
    return 'BAD'


def print_result(out: dict):
    print('\nANNOTATED ANSWER:\n')
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
    print('Interactive retrieval+LLM. Type your question and press Enter. Type quit or empty to exit.')
    try:
        while True:
            q = input('\nQuestion> ').strip()
            if not q or q.lower() in ('quit', 'exit'):
                print('Exiting.')
                break
            print('Running retrieval and LLM... (may take a few seconds)')
            try:
                out = answer_with_sources(q, k=5)
                print_result(out)
            except Exception as e:
                print('Error running query:')
                traceback.print_exc()
    except (KeyboardInterrupt, EOFError):
        print('\nExiting.')


if __name__ == '__main__':
    main()
