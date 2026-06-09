## Secret handling and safe LLM integration

Follow these rules to connect Grok (or any LLM) without leaking secrets into git:

- Never hardcode API keys in code. Use environment variables instead.
- Add a `.env` file locally for convenience and ensure it's in `.gitignore`.
- Add a `.env.example` with placeholder keys (already provided).
- Store secrets in your CI/CD provider's secret store (e.g., GitHub Actions secrets) and reference them in workflows.
- Use OS-level keyrings or a secrets manager (HashiCorp Vault, AWS Secrets Manager) for production.
- Use a secret scanner in CI / pre-commit (e.g., `detect-secrets`, `git-secrets`) to block accidental commits.
- Rotate keys immediately if a secret is exposed.

Quick local setup:

1. Copy the example and fill your keys locally:

```bash
cp .env.example .env
# edit .env and add your keys
```

2. Export env vars for a one-off run (recommended over editing files):

```bash
export GROK_API_KEY="..."
export OPENAI_API_KEY="..."
python3 -m src.gradio_app
```

CI (GitHub Actions) example snippet:

```yaml
env:
  GROK_API_KEY: ${{ secrets.GROK_API_KEY }}
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

If you'd like, I can add a `.pre-commit-config.yaml` that runs `detect-secrets` and instructions to install `pre-commit`.
