from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    openrouter_site_url: str
    openrouter_app_name: str
    llm_temperature: float
    slack_webhook_url: str
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str
    jira_issue_type: str
    max_upload_mb: int
    max_log_rows: int
    rag_top_k: int

    @property
    def jira_is_configured(self) -> bool:
        return all((self.jira_base_url, self.jira_email, self.jira_api_token, self.jira_project_key))


def get_settings() -> Settings:
    try:
        temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
    except ValueError:
        temperature = 0.0
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip(),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL", "http://localhost:7860").strip(),
        openrouter_app_name=os.getenv("OPENROUTER_APP_NAME", "DevOps Incident Analysis Suite").strip(),
        llm_temperature=temperature,
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", "").strip(),
        jira_base_url=os.getenv("JIRA_BASE_URL", "").rstrip("/"),
        jira_email=os.getenv("JIRA_EMAIL", "").strip(),
        jira_api_token=os.getenv("JIRA_API_TOKEN", "").strip(),
        jira_project_key=os.getenv("JIRA_PROJECT_KEY", "").strip(),
        jira_issue_type=os.getenv("JIRA_ISSUE_TYPE", "Task").strip() or "Task",
        max_upload_mb=_int_env("MAX_UPLOAD_MB", 10),
        max_log_rows=_int_env("MAX_LOG_ROWS", 5000),
        rag_top_k=_int_env("RAG_TOP_K", 4),
    )
