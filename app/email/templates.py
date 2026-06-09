from __future__ import annotations

import os
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings

settings = get_settings()

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

_env = Environment(
    loader=FileSystemLoader(_templates_dir),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, **context) -> str:
    template = _env.get_template(template_name)
    return template.render(**context)
