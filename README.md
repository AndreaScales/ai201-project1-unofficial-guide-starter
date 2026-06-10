# The Unofficial Guide — Project 1

## Domain

This system answers questions about study abroad resources for HBCU students and Black travelers, with a focus on funding, destination selection, safety, and the lived experience of traveling while Black.

This domain is valuable because the most useful guidance is scattered across university pages, scholarship sites, academic research, and personal travel stories. Official study abroad materials are often generic and do not address concerns that matter to HBCU students, such as affordability, racism abroad, hair and skin care, and finding Black-friendly support systems.

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | HBCU Lifestyle: Study Abroad Resources | Article | https://hbculifestyle.com/study-abroad-hbcu-resources/ |
| 2 | Gilman International Scholarship Program | Official Program | https://www.gilmanscholarship.org/ |
| 3 | "If Not Us Then Who?" — Megan Covington | Academic Paper | https://independent.academia.edu/MeganCovington |
| 4 | The HBCU Career Center: Study Abroad | Career Resource | https://www.thehbcucareercenter.com/college-student-career-planning/study-abroad/ |
| 5 | Green Book Global: Ultimate Guide to Black Travel | Guide / Tool | https://greenbookglobal.com/travel-the-world/ultimate-guide-to-black-travel/ |
| 6 | Melanin Base Camp: Hair & Skin Care Abroad | Blog / Personal | https://www.melaninbasecamp.com/trip-reports/2024/10/20/traveling-while-black-how-i-care-for-my-hair-and-skin-while-abroad |
| 7 | Joy Worldwide: Best Study Abroad Destinations for HBCU Students | Article | https://www.joyworldwideinc.com/blog/the-best-study-abroad-destinations-for-hbcu-students |
| 8 | Northwestern: Black History Month Global Week | University Resource | https://www.northwestern.edu/abroad/events/black-history-month |
| 9 | USC Dissertation: Black Students & Career Readiness Abroad (2023) | Dissertation | https://scholarcommons.sc.edu/etd/7274 |
| 10 | TikTok: #GilmanScholarship + #HBCU Study Abroad | Social / Short Video | https://www.tiktok.com/discover/gilman-scholarship-essay-tips |

## Chunking Strategy

**Chunk size:** 1000 characters

**Overlap:** 150 characters

**Why these choices fit your documents:** Most of the corpus is made up of short articles, list-heavy guides, and resource pages with clear headings. A 1000-character chunk usually keeps one topic together without swallowing unrelated navigation text, while 150 characters of overlap preserves context when a scholarship detail, safety tip, or destination recommendation crosses a boundary. Before chunking, I strip nav/footer boilerplate, normalize whitespace, and keep headings and bullet lists intact when possible.

**Final chunk count:** 81

## Ingestion and chunking

The ingestion step cleans raw HTML and text sources, then writes chunked documents to `data/chunks.jsonl`.

Run a quick self-test that creates sample chunks:

```bash
python3 src/ingest.py --test
```

To ingest local `documents/` and produce `data/chunks.jsonl`:

```bash
python3 src/ingest.py --out data/chunks.jsonl
```

Note: remote fetching for URLs listed in `data/sources.json` is left as a separate step to avoid introducing network dependencies in tests.

## Embedding and Retrieval

Compute embeddings for `data/chunks.jsonl` and store them in ChromaDB:

```bash
python3 src/embed_and_store.py --chunks data/chunks.jsonl --persist-dir db/chroma --collection chunks
```

Run a quick retrieval test after indexing:

```bash
python3 src/embed_and_store.py --chunks data/chunks.jsonl --persist-dir db/chroma --collection chunks --test-query "What scholarships exist for HBCU students?"
```

## Query Interface

The project includes a Gradio UI for asking questions interactively and reviewing the answer, the raw model output, the cited sources, and the retrieved chunks.

```bash
python3.11 -m src.gradio_app
```

Then open http://127.0.0.1:7860 in your browser.

## Embedding Model

**Model used:** `sentence-transformers/all-MiniLM-L6-v2`

**Production tradeoff reflection:** If cost were not a constraint, I would consider a larger embedding model with better semantic recall on domain-specific and long-form text, and I would likely add a reranker on top of retrieval. The tradeoff is that higher-quality embeddings usually increase latency, memory use, and operational complexity. For this project, the lightweight local model was a good fit because the corpus is relatively small and the main goal is fast, grounded retrieval rather than maximum multilingual coverage.

## Grounded Generation

**System prompt grounding instruction:** The model is instructed to use only the provided CONTEXT, avoid external knowledge, and reply exactly with "I don't know based on the provided sources." when the context is insufficient. The user message also includes a numbered SOURCES block so the model can cite specific retrieved chunks with inline markers like `[1]`.

**How source attribution is surfaced in the response:** The response layer preserves model citations when present and also performs sentence-level citation assignment against the retrieved chunks. The final output shows an annotated answer, a numbered source list, and the retrieved chunk metadata so the user can trace where each answer came from.

**Query interface behavior:** If the model cannot answer from the retrieved context, the app shows the refusal message rather than inventing an answer.

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | According to the Gilman program website, what is the full program name and which U.S. government office funds it? | Benjamin A. Gilman International Scholarship Program; funded by the U.S. Department of State's Bureau of Educational and Cultural Affairs. | The full program name is the Benjamin A. Gilman International Scholarship Program, and it is funded by the U.S. Department of State's Bureau of Educational and Cultural Affairs. | Relevant | Accurate |
| 2 | Which specific HBCUs are explicitly listed on the HBCU Lifestyle page as having established international exchange programs? (List the institutions named.) | Howard University; Morehouse College; Spelman College. | The system returned Howard University, Morehouse College, and Spelman College. | Relevant | Accurate |
| 3 | List two concrete safety recommendations given by The HBCU Career Center's "Stay Safe Abroad" guidance. (Provide the exact practices.) | Examples: "Be alert"; "Make and secure copies of your important papers." | The system returned practices such as being alert, trusting your instincts, and keeping a routine for communicating with family. | Relevant | Accurate |
| 4 | What filtering criteria does Green Book Global's destination tool provide? (Name at least two criteria used by the tool.) | Examples: "travelingWhileBlackScore"/threat-of-racism metric and filters for affordability, adventure, romance, and local-food scores. | The system returned criteria including threat of racism, romance, affordability, and adventure. | Relevant | Accurate |
| 5 | According to the Melanin Base Camp article, name two recommended hair or skin care strategies travelers should prepare before departure. | Examples: protective styles (e.g., knotless braids) and packing moisturizers/oils and non-whitening sunscreen. | The system returned advice such as packing moisturizers, oils, leave-in conditioners, and preparing for mineral-heavy water. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

## Failure Case Analysis

**Question that failed:**
"What is the purpose of the file ingest.py in this project?"

**What the system returned:**
"I don't know based on the provided sources."

**Root cause (tied to a specific pipeline stage):** The retrieval corpus does not include repository files like `src/ingest.py`; it is built from the study-abroad source collection. Because the query asked about a local project file, retrieval returned no supporting chunk, and the grounded generation step correctly refused to invent an answer.

**What you would change to fix it:** Add a second retrieval corpus for repository documentation or ingest local project files into the same vector store, then route technical questions like this to that corpus instead of the external study-abroad sources.

## Spec Reflection

**One way the spec helped you during implementation:** `planning.md` gave me a concrete domain, document list, chunking plan, retrieval strategy, and evaluation questions before I started coding. That kept the implementation focused on the right source set and made it easy to verify the pipeline against the five planned questions instead of improvising around an undefined project scope.

**One way your implementation diverged from the spec, and why:** I added a stronger citation pipeline and a Gradio-based query interface after the initial plan. The citation merge was necessary because model-generated citations were useful but not always reliable on their own, and the UI made it easier to demonstrate the system without requiring a terminal prompt.

## AI Usage

**Instance 1**

- *What I gave the AI:* The Domain, Documents, and Chunking Strategy sections from `planning.md`, plus the implementation requirements.
- *What it produced:* The first version of the ingestion, chunking, embedding, and retrieval pipeline.
- *What I changed or overrode:* I adjusted the provider selection to prefer Groq, fixed environment-variable handling for `GROQ_API_KEY`, and added programmatic citation assignment so answers stayed grounded.

**Instance 2**

- *What I gave the AI:* The architecture notes and the evaluation requirement for a user-facing query interface.
- *What it produced:* A first-pass Gradio app that connected a question box to the retrieval-backed generator.
- *What I changed or overrode:* I expanded it to show the raw model output, cited answer, source table, retrieved chunks, and error tracebacks so failures are easier to inspect during a demo.