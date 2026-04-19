from pathlib import Path
from string import Template

_TEMPLATES_DIR = Path(__file__).parent / "templates"

def render(name: str, **kwargs: str) -> str:
    """Load a prompt template by name and substitute variables."""
    text = (_TEMPLATES_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
    return Template(text).substitute(**kwargs)
