from __future__ import annotations

import os
from pathlib import Path

IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "target", ".cache"}
IMPORTANT_FILES = {"README.md", "pyproject.toml", "package.json", "go.mod", "Cargo.toml", "requirements.txt"}


def collect_project_context(cwd: Path | None = None, *, max_files: int = 80) -> str:
    cwd = cwd or Path.cwd()
    lines = [f"Current directory: {cwd}", "", "Files:"]
    count = 0
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in sorted(dirs) if d not in IGNORE_DIRS]
        rel_root = Path(root).relative_to(cwd)
        depth = 0 if str(rel_root) == "." else len(rel_root.parts)
        if depth > 3:
            dirs[:] = []
            continue
        for fname in sorted(files):
            if fname.startswith(".") and fname not in {".gitignore"}:
                continue
            rel = Path(root, fname).relative_to(cwd)
            lines.append(f"- {rel}")
            count += 1
            if count >= max_files:
                lines.append(f"... truncated at {max_files} files")
                return "\n".join(lines)
    for imp in IMPORTANT_FILES:
        p = cwd / imp
        if p.exists() and p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:4000]
                lines.extend(["", f"--- {imp} ---", text])
            except OSError:
                pass
    return "\n".join(lines)
