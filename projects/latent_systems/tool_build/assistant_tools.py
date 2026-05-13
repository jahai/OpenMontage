"""Tool implementations for the in-app assistant (Claude Code-equivalent).

Mirrors the file/shell/db capabilities Joseph uses in Claude Code, scoped by
AD-5: refuse writes to `projects/latent_systems/{shared,ep1,docs,tools}/` and
the canonical NOTES.md / PROJECT_ARCHITECTURE.md at the project root. Reads
are always allowed (need full project context). Bash is refused if the
command string mentions any canonical-path prefix.

The pre-commit hook at OpenMontage/.git/hooks/pre-commit catches commits that
slip through; this module enforces at write-time so the assistant never
even produces the diff.
"""

from __future__ import annotations

import base64
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Optional


# OpenMontage repo root: tool_build → latent_systems → projects → OpenMontage
REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_BUILD = Path(__file__).resolve().parent

CANONICAL_BLOCKED = [
    "projects/latent_systems/shared/",
    "projects/latent_systems/ep1/",
    "projects/latent_systems/docs/",
    "projects/latent_systems/tools/",
    "projects/latent_systems/NOTES.md",
    "projects/latent_systems/PROJECT_ARCHITECTURE.md",
]


class ToolError(Exception):
    """Tool-level error surfaced to the model as a tool_result error string."""


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _rel_to_repo(p: Path) -> Optional[str]:
    try:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return None


def _is_canonical(path: Path) -> bool:
    rel = _rel_to_repo(path)
    if rel is None:
        return False
    for blocked in CANONICAL_BLOCKED:
        b = blocked.rstrip("/")
        if rel == b or rel.startswith(blocked):
            return True
    return False


def _bash_touches_canonical(command: str) -> bool:
    for blocked in CANONICAL_BLOCKED:
        if blocked in command:
            return True
    return False


# ---- READ TOOLS ----

def read_file(path: str, offset: int = 0, limit: int = 2000) -> str:
    p = _resolve(path)
    if not p.exists():
        raise ToolError(f"File not found: {p}")
    if not p.is_file():
        raise ToolError(f"Not a file: {p}")
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    sliced = lines[offset:offset + limit]
    numbered = "\n".join(
        f"{offset + i + 1:>5}\t{ln}" for i, ln in enumerate(sliced)
    )
    suffix = ""
    if offset + limit < len(lines):
        suffix = f"\n... ({len(lines) - (offset + limit)} more lines)"
    return numbered + suffix


def list_directory(path: str, pattern: str = "*") -> str:
    p = _resolve(path)
    if not p.is_dir():
        raise ToolError(f"Not a directory: {p}")
    items = sorted(p.glob(pattern))
    lines = []
    for item in items[:300]:
        try:
            rel = item.relative_to(p)
        except ValueError:
            rel = item.name
        marker = "/" if item.is_dir() else ""
        lines.append(f"{rel}{marker}")
    out = "\n".join(lines) or "(empty)"
    if len(items) > 300:
        out += f"\n... ({len(items) - 300} more)"
    return out


def search_files(pattern: str, path: str = ".",
                 file_type: Optional[str] = None) -> str:
    p = _resolve(path)
    cmd = ["rg", "--max-count", "20", "--max-columns", "300", "-n", pattern, str(p)]
    if file_type:
        cmd.extend(["-t", file_type])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        return "ripgrep (rg) not on PATH; install or use list_directory + read_file."
    out = result.stdout[:10000]
    if result.returncode == 1 and not out:
        return "(no matches)"
    if not out:
        return result.stderr[:500] or "(no matches)"
    return out


def query_db(sql: str, params: Optional[list] = None) -> str:
    upper = sql.strip().upper()
    if not upper.startswith(("SELECT", "PRAGMA", "WITH ", "EXPLAIN")):
        raise ToolError(
            "query_db is read-only — only SELECT/WITH/PRAGMA/EXPLAIN allowed."
        )
    db_path = TOOL_BUILD / "_data" / "state.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params or []).fetchmany(200)
        if not rows:
            return "(no rows)"
        cols = list(rows[0].keys())
        lines = ["\t".join(cols), "\t".join("-" * 8 for _ in cols)]
        for r in rows:
            vals = []
            for c in cols:
                v = str(r[c])[:120] if r[c] is not None else "NULL"
                vals.append(v.replace("\t", " ").replace("\n", " "))
            lines.append("\t".join(vals))
        suffix = ""
        if len(rows) == 200:
            suffix = "\n(truncated at 200 rows)"
        return "\n".join(lines) + suffix
    finally:
        conn.close()


def see_image(render_id: Optional[str] = None,
              path: Optional[str] = None) -> dict:
    """Returns image data as base64 + media_type for vision tool_result block."""
    if render_id:
        db_path = TOOL_BUILD / "_data" / "state.db"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT filepath FROM renders WHERE id=?", (render_id,)
            ).fetchone()
            if not row:
                raise ToolError(f"render {render_id} not found")
            path = row[0]
        finally:
            conn.close()
    if not path:
        raise ToolError("Provide render_id or path")
    p = _resolve(path)
    if not p.exists():
        raise ToolError(f"file not found: {p}")
    data = p.read_bytes()
    if len(data) > 5 * 1024 * 1024:
        raise ToolError(
            f"image too large ({len(data) // 1024} KB); max 5 MB for vision."
        )
    # Sniff actual content type from magic bytes — file extensions can lie
    # (Anthropic vision strictly validates declared media_type matches bytes).
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        media = "image/png"
    elif data[:2] == b"\xff\xd8":
        media = "image/jpeg"
    elif data[:4] == b"GIF8":
        media = "image/gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        media = "image/webp"
    else:
        ext = p.suffix.lower().lstrip(".")
        media_map = {
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif",
        }
        media = media_map.get(ext)
        if not media:
            raise ToolError(
                f"unsupported image type for vision (ext=.{ext}, "
                f"first bytes={data[:8].hex()})"
            )
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media,
            "data": base64.b64encode(data).decode(),
        },
    }


# ---- WRITE TOOLS (AD-5 enforced) ----

def write_file(path: str, content: str) -> str:
    p = _resolve(path)
    if _is_canonical(p):
        raise ToolError(
            f"REFUSED: {_rel_to_repo(p)} is under AD-5 canonical paths "
            "(Joseph's creative work). The assistant cannot write here. "
            "Surface what you wanted to change to Joseph instead."
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {_rel_to_repo(p) or p}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    p = _resolve(path)
    if _is_canonical(p):
        raise ToolError(
            f"REFUSED: {_rel_to_repo(p)} is under AD-5 canonical paths."
        )
    if not p.exists():
        raise ToolError(f"file not found: {p}")
    text = p.read_text(encoding="utf-8")
    if old_string not in text:
        raise ToolError(
            "old_string not found. Use read_file first to confirm exact content "
            "(including whitespace and line breaks)."
        )
    n = text.count(old_string)
    if n > 1:
        raise ToolError(
            f"old_string is not unique ({n} occurrences). "
            "Provide more surrounding context to make it unique."
        )
    new_text = text.replace(old_string, new_string)
    p.write_text(new_text, encoding="utf-8")
    return (f"Edited {_rel_to_repo(p) or p}: replaced "
            f"{len(old_string)} → {len(new_string)} chars")


# ---- BASH ----

def run_bash(command: str, cwd: Optional[str] = None) -> str:
    if _bash_touches_canonical(command):
        raise ToolError(
            "REFUSED: command mentions an AD-5 canonical path. "
            "Joseph commits canonical work himself. "
            "Adjust the command to operate via tool_build/ or surface to Joseph."
        )
    if cwd:
        cwd_p = _resolve(cwd)
        if not cwd_p.is_dir():
            raise ToolError(f"cwd not a directory: {cwd_p}")
    else:
        cwd_p = REPO_ROOT
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            cwd=str(cwd_p), timeout=60, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise ToolError("Command timed out after 60s")
    parts = []
    if result.stdout:
        parts.append(f"STDOUT:\n{result.stdout[:8000]}")
    if result.stderr:
        parts.append(f"STDERR:\n{result.stderr[:2000]}")
    parts.append(f"EXIT: {result.returncode}")
    return "\n\n".join(parts)


# ---- TOOLS LIST FOR ANTHROPIC API ----

ANTHROPIC_TOOLS: list[dict] = [
    {
        "name": "read_file",
        "description": (
            "Read a file from disk. Returns content with line numbers. "
            "Use this BEFORE proposing edits — never guess at file content. "
            "Path is relative to OpenMontage repo root or absolute."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "offset": {"type": "integer",
                           "description": "0-indexed line offset"},
                "limit": {"type": "integer",
                          "description": "max lines to return (default 2000)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories. Optional glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string",
                            "description": "glob (e.g., '*.py' or '**/*.html')"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_files",
        "description": (
            "Ripgrep across files for a regex pattern. Returns matching lines "
            "with file:line prefixes. Faster and more accurate than reading files "
            "one-by-one when looking for symbols/strings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "file_type": {"type": "string",
                              "description": "rg type (py, js, html, md, ...)"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "query_db",
        "description": (
            "Read-only SQL against state.db. SELECT / WITH / PRAGMA / EXPLAIN only. "
            "Tables: concepts, prompts, generation_attempts, renders, verdicts, "
            "ai_consultations, hero_promotions, audit_sessions, api_calls, "
            "lineage_edges, cross_ai_captures."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
                "params": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "see_image",
        "description": (
            "Load an image so you can analyze it visually. Either render_id "
            "(looks up filepath from state.db) or absolute path. Use for "
            "evaluating hero candidates, debugging visual issues, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "render_id": {"type": "string"},
                "path": {"type": "string"},
            },
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write a file (creates new or overwrites). REFUSED for AD-5 "
            "canonical paths: projects/latent_systems/{shared,ep1,docs,tools}/. "
            "Use for tool_build/ work, or any path outside latent_systems."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace one exact string in a file. old_string must be unique. "
            "Use read_file first to get exact content. "
            "REFUSED for AD-5 canonical paths."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "run_bash",
        "description": (
            "Execute a bash command (60s timeout). REFUSED if the command string "
            "contains an AD-5 canonical path. Useful for: running tests, "
            "restarting the server (python serve.py --stop && python serve.py), "
            "git status / log, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
            },
            "required": ["command"],
        },
    },
]


def execute_tool(name: str, args: dict) -> tuple[Any, bool]:
    """Returns (result, is_image_block).

    result is a string for normal tools; for see_image, it's the image dict
    that goes into a tool_result content block (Anthropic vision input shape).
    """
    impls = {
        "read_file": read_file,
        "list_directory": list_directory,
        "search_files": search_files,
        "query_db": query_db,
        "see_image": see_image,
        "write_file": write_file,
        "edit_file": edit_file,
        "run_bash": run_bash,
    }
    fn = impls.get(name)
    if not fn:
        return f"ERROR: unknown tool {name}", False
    try:
        result = fn(**args)
        if isinstance(result, dict) and result.get("type") == "image":
            return result, True
        return result, False
    except ToolError as e:
        return f"ERROR: {e}", False
    except TypeError as e:
        return f"ERROR (bad args): {e}", False
    except Exception as e:
        return f"ERROR ({type(e).__name__}): {e}", False
