"""Lightweight LLM interface and system prompt template enforcing grounding.

This module builds the system + user prompt and calls OpenAI ChatCompletion.
The system prompt is strict: the model MUST only use the provided CONTEXT and
must respond with "I don't know based on the provided sources." if the answer
cannot be confidently produced from the context.
"""
import os
from typing import List, Dict, Any

try:
    import openai
except Exception:
    openai = None
try:
    import requests
except Exception:
    requests = None
try:
    from groq import Groq
except Exception:
    Groq = None


SYSTEM_PROMPT = (
    "You are an assistant that MUST only answer using the provided CONTEXT below. "
    "Do not use any external knowledge or hallucinate. If the answer cannot be "
    "produced fully from the CONTEXT, reply exactly with: I don't know based on the provided sources." 
    "When answering, be concise and factual."
)


def build_messages(query: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    # Context chunks are dicts with keys: id, source, text
    context_texts = []
    for c in context_chunks:
        header = f"SOURCE: {c.get('source')} | CHUNK_ID: {c.get('id')}"
        body = c.get('text')
        context_texts.append(header + "\n" + body)

    context_block = "\n\n----\n\n".join(context_texts)

    # Build a numbered SOURCES mapping so the model can cite sources inline.
    sources_lines = []
    for i, c in enumerate(context_chunks, start=1):
        src = c.get("source")
        cid = c.get("id")
        sources_lines.append(f"[{i}] SOURCE: {src} | CHUNK_ID: {cid}")
    sources_block = "\n".join(sources_lines)

    system = SYSTEM_PROMPT
    user = (
        "You are given the following CONTEXT from authoritative sources. "
        "Answer the user's question using ONLY that context. Do not invent facts.\n\n"
        "CONTEXT:\n" + context_block + "\n\nQUESTION:\n" + query + "\n\n"
        "When you use information from the CONTEXT, append inline numeric citations like [1] "
        "that refer to the SOURCES list below. Place citations immediately after the sentence or clause they support.\n\n"
        "If the context does not contain enough data to answer, respond exactly: I don't know based on the provided sources.\n\n"
        "SOURCES:\n" + sources_block
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_openai_chat(messages: List[Dict[str, str]], model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    if openai is None:
        raise RuntimeError("openai package not installed")
    key = get_api_key("openai")
    if not key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required to call OpenAI")
    openai.api_key = key

    resp = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature)
    # Grab assistant content
    choices = resp.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


def get_api_key(provider: str) -> str:
    """Return the API key for a provider from environment variables.

    Mapping:
      - provider == "openai" -> OPENAI_API_KEY
      - provider == "groq" -> GROQ_API_KEY
      - provider == "grok" -> GROQ_API_KEY (backward compatible typo)
      - otherwise -> look for PROVIDER_API_KEY or PROVIDER_KEY
    """
    prov = provider.strip().lower()
    if prov == "openai":
        return os.environ.get("OPENAI_API_KEY", "")
    if prov in ("groq", "grok"):
                return os.environ.get("GROQ_API_KEY", "") or os.environ.get("GROK_API_KEY", "")
    # fallback
    env_name = f"{prov.upper()}_API_KEY"
    return os.environ.get(env_name, "")


def call_chat(messages: List[Dict[str, str]], model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
    """Auto-select provider: Groq -> OpenAI fallback.

    Groq is preferred when `GROQ_API_KEY` is available. If Groq is not
    configured, this falls back to OpenAI via `OPENAI_API_KEY`.
    """
    groq_key = get_api_key("groq")
    if groq_key:
        if Groq is None:
            raise RuntimeError("groq package not installed")
        groq_client = Groq(api_key=groq_key)
        groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        try:
            resp = groq_client.chat.completions.create(
                model=groq_model,
                messages=messages,
                temperature=temperature,
            )
        except Exception as e:
            # Provide a clearer error for authentication failures
            msg = str(e)
            if "401" in msg or "invalid api key" in msg.lower() or "authenticationerror" in e.__class__.__name__.lower():
                raise RuntimeError(
                    "Groq authentication failed (401). Check your GROQ_API_KEY in environment or .env — ensure it's correct, not expired, and has no surrounding quotes or whitespace."
                ) from e
            raise
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        message = choices[0].message
        return getattr(message, "content", "") or ""

    # fallback to OpenAI
    return call_openai_chat(messages, model=model, temperature=temperature)
