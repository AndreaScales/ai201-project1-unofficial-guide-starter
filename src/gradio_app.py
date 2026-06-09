"""Simple Gradio app that wires a query input to the retrieval-backed generator.

Run:
    python3 -m src.gradio_app

Make sure `GROQ_API_KEY` (preferred) or `OPENAI_API_KEY` is set in the environment or in `.env`.
"""
import gradio as gr
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv('.env', override=True)

from src.generator import answer_with_sources


def run_query(query: str, k: int = 5) -> Dict[str, Any]:
    try:
        out = answer_with_sources(query, k=k)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return {"answer": f"Error: {e}\n\nTraceback:\n{tb}", "sources": [], "raw_answer": "", "retrieved": []}
    return out


def make_ui():
    with gr.Blocks() as demo:
        gr.Markdown("## Retrieval-grounded QA (persistent Chroma backend)")
        with gr.Row():
            query = gr.Textbox(label="Question", lines=2, placeholder="Ask something grounded in your docs")
            k = gr.Slider(minimum=1, maximum=10, value=5, step=1, label="top-k")
        btn = gr.Button("Run")
        answer = gr.Textbox(label="Answer (with numeric citations)", lines=6)
        raw = gr.Textbox(label="Raw model output", lines=6)
        sources = gr.Dataframe(headers=["index", "source"], datatype=["number", "str"], interactive=False)
        retrieved = gr.Dataframe(headers=["id", "source", "distance"], datatype=["str", "str", "number"], interactive=False)

        def on_click(q, k_v):
            res = run_query(q, int(k_v))
            # format sources for dataframe
            src_rows = []
            for s in res.get("sources", []):
                src_rows.append([s.get("index"), s.get("source")])
            # format retrieved rows
            ret_rows = []
            for r in res.get("retrieved", []):
                meta = r.get("metadata", {})
                ret_rows.append([r.get("id"), meta.get("source"), r.get("distance")])
            return res.get("answer"), res.get("raw_answer", ""), src_rows, ret_rows

        btn.click(on_click, inputs=[query, k], outputs=[answer, raw, sources, retrieved])

    return demo


if __name__ == "__main__":
    app = make_ui()
    app.launch(server_name="127.0.0.1", server_port=7860)
