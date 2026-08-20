"""Global test isolation settings."""

import os

# Unit tests use deterministic LLM fakes and must not pollute the real LangSmith project.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["APP_ENV"] = "test"
