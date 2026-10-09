"""Guards for the static front end (no browser needed)."""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_css_colour_tokens_are_valid_and_opaque():
    # A stray 8-digit hex once made the main text colour ~7% opaque (unreadable).
    css = (STATIC / "app.css").read_text()
    for name, value in re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]+)\s*;", css):
        assert len(value) in (4, 7), f"{name}: {value} is not a 3- or 6-digit hex colour"


def test_every_page_has_a_renderer():
    js = (STATIC / "app.js").read_text()
    for page in re.findall(r"render: (render\w+)", js):
        assert re.search(rf"function {page}\b|const {page}\b", js), f"{page} is not defined"
