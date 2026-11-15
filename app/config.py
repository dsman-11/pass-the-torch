import os
import re
from dataclasses import dataclass
from pathlib import Path


def load_local_env():
    """Small, literal KEY=VALUE loader; never evaluates shell expressions."""
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def setting(name, default=""):
    """New branding takes precedence; existing installations keep their settings."""
    return os.getenv("PASS_THE_TORCH_"+name, os.getenv("COURSEWISE_"+name, default))


def default_database():
    # Do not strand the previous default database when upgrading the source.
    legacy = Path("data/coursewise.sqlite3")
    return str(legacy) if legacy.is_file() else "data/pass-the-torch.sqlite3"


@dataclass
class Settings:
    db_path: str = "data/pass-the-torch.sqlite3"
    api_key: str = ""
    model: str = ""
    secure_cookie: bool = False
    provider: str = "openai"
    demo_enabled: bool = True
    demo_db_path: str = ""

    @property
    def ai_configured(self):
        return bool(self.api_key and self.model and self.provider in ("openai", "gemini"))

    @classmethod
    def from_env(cls):
        load_local_env()
        provider = setting("AI_PROVIDER").strip().lower()
        if not provider:
            provider = "gemini" if os.getenv("GEMINI_API_KEY", "").strip() else "openai"
        if provider not in ("openai", "gemini"):
            raise ValueError("PASS_THE_TORCH_AI_PROVIDER must be gemini or openai")
        key_name, model_name = (("GEMINI_API_KEY", "GEMINI_MODEL") if provider == "gemini"
                                else ("OPENAI_API_KEY", "OPENAI_MODEL"))
        model = os.getenv(model_name, "").strip().removeprefix("models/")
        if provider == "gemini" and model and not re.fullmatch(r"gemini-[a-zA-Z0-9._-]+", model):
            raise ValueError("GEMINI_MODEL must be a Gemini model ID, such as gemini-3.5-flash-lite")
        return cls(db_path=setting("DB", default_database()),
                   api_key=os.getenv(key_name, "").strip(), model=model,
                   secure_cookie=setting("SECURE_COOKIE", "false").lower() == "true",
                   provider=provider,
                   demo_enabled=setting("DEMO_ENABLED", "true").lower() == "true",
                   demo_db_path=setting("DEMO_DB"))
