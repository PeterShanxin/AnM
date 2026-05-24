"""Tool and category catalog — mirrors common.jsx TOOLS / CATEGORIES."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryDef:
    id: str
    label: str
    icon: str   # Unicode glyph for the category rail


@dataclass(frozen=True)
class ToolDef:
    id: str
    label: str
    cat: str
    desc: str
    icon: str            # Unicode glyph for the tool card
    panel_key: str | None = None  # key used in hub._panels; None = coming soon


CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef("organize", "Organize", "☰"),
    CategoryDef("edit",     "Edit",     "✏"),
    CategoryDef("convert",  "Convert",  "⇄"),
    CategoryDef("secure",   "Secure",   "⊕"),
)

TOOLS: tuple[ToolDef, ...] = (
    # ── Organize ──────────────────────────────────────────────────────────────
    ToolDef("merge",    "Merge",          "organize", "Combine multiple PDFs into one",        "⊕", "annotate_merge"),
    ToolDef("split",    "Split",          "organize", "Break a PDF into parts",                "⋮", "split"),
    ToolDef("reorder",  "Reorder",        "organize", "Rearrange pages in any order",          "↕", "reorder"),
    ToolDef("delete",   "Delete Pages",   "organize", "Remove specific pages",                 "⊖", "delete_pages"),
    ToolDef("rotate",   "Rotate",         "organize", "Rotate pages 90/180/270°",              "↺", "rotate"),
    ToolDef("extract",  "Extract",        "organize", "Pull pages into a new PDF",             "↑", "extract"),
    # ── Edit ──────────────────────────────────────────────────────────────────
    ToolDef("annotate", "Annotate",       "edit",     "Add notes, highlights, shapes",         "✎", None),
    ToolDef("watermark","Watermark",      "edit",     "Stamp text or image over pages",        "◎", None),
    ToolDef("numbers",  "Page Numbers",   "edit",     "Add page numbering",                    "#", None),
    ToolDef("metadata", "Metadata",       "edit",     "Edit title, author, keywords",          "≡", None),
    # ── Convert ───────────────────────────────────────────────────────────────
    ToolDef("images",   "PDF ⇄ Images",   "convert",  "Convert to/from PNG, JPG",              "⇄", None),
    ToolDef("compress", "Compress",       "convert",  "Reduce file size",                      "▽", None),
    ToolDef("ocr",      "OCR",            "convert",  "Recognize text from scans",             "T", None),
    # ── Secure ────────────────────────────────────────────────────────────────
    ToolDef("protect",  "Protect/Unlock", "secure",   "Add or remove a password",              "⊛", None),
    ToolDef("flatten",  "Flatten",        "secure",   "Lock form fields & annotations",        "≡", None),
    ToolDef("compare",  "Compare",        "secure",   "Diff two PDFs side-by-side",            "⊞", None),
)


def tools_by_cat(cat_id: str) -> tuple[ToolDef, ...]:
    return tuple(t for t in TOOLS if t.cat == cat_id)


def get_tool(tool_id: str) -> ToolDef | None:
    return next((t for t in TOOLS if t.id == tool_id), None)


def get_category(cat_id: str) -> CategoryDef | None:
    return next((c for c in CATEGORIES if c.id == cat_id), None)
