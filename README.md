# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
My project will be a Stdy Abroad Preparation Guide.
     Why is this knowledge valuable, and why is it hard to find through official channels?

This knowledge is very valuable because a lot of colleges don't have resources currently set up to best prepare students for this opportunity. 

     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | HBCU Lifestyle: Study Abroad Resources | Article | https://hbculifestyle.com/study-abroad-hbculifestyle-resources/ |
| 2 | Gilman International Scholarship Program | Official Program | https://www.gilmanscholarship.org/ |
| 3 | "If Not Us Then Who?" — Megan Covington | Academic Paper | https://independent.academia.edu/MeganCovington |
| 4 | The HBCU Career Center: Study Abroad | Career Resource | https://www.thehbcucareercenter.com/college-student-career-planning/study-abroad/ |
| 5 | Green Book Global: Ultimate Guide to Black Travel | Guide / Tool | https://greenbookglobal.com/travel-the-world/ultimate-guide-to-black-travel/ |
| 6 | Melanin Base Camp: Hair & Skin Care Abroad | Blog / Personal | https://www.melaninbasecamp.com/trip-reports/2024/10/20/traveling-while-black-how-i-care-for-my-hair-and-skin-while-abroad |
| 7 | Joy Worldwide: Best Study Abroad Destinations for HBCU Students | Article | https://www.joyworldwideinc.com/blog/the-best-study-abroad-destinations-for-hbcu-students |
| 8 | Northwestern: Black History Month Global Week | University Resource | https://www.northwestern.edu/abroad/events/black-history-month |
| 9 | USC Dissertation: Black Students & Career Readiness Abroad (2023) | Dissertation | https://scholarcommons.sc.edu/etd/7274 |
| 10 | TikTok: #GilmanScholarship + #HBCU Study Abroad | Social / Short Video | https://www.tiktok.com/discover/gilman-scholarship-essay-tips |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**

**Overlap:**

**Why these choices fit your documents:**

**Final chunk count:**

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
