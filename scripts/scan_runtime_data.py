#!/usr/bin/env python3
"""Find runtime data files (JSON / JS storage) in a VicroCode upload tree.

Run this before uploading a project that keeps records in plain files instead of SQLite.
It reports the paths that would be delivered to buyers/clones together with the author's
real data, and can write the `vicrocode.project.json` declaration for you.

Usage::

    # report only
    python scripts/scan_runtime_data.py path/to/project

    # report + write/merge vicrocode.project.json
    python scripts/scan_runtime_data.py path/to/project --write

    # also fail (exit 1) when undeclared data files are found, for CI use
    python scripts/scan_runtime_data.py path/to/project --strict
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

MANIFEST_FILENAME = "vicrocode.project.json"
MANIFEST_SCHEMA = "vicrocode.project.v1"

EXCLUDED_DIR_NAMES = {
    "runtime", "sourdown", ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", ".idea", ".vscode", "venv", ".venv",
    "env", "logs", "log", "tmp", "temp", ".cache", "dist", "build",
    # 智能体本地记录目录（存智能部署令牌与项目 ID）：不是运行期数据，跳过
    ".vicrocode",
}

DATA_FILE_STEMS = {
    "data", "db", "database", "store", "storage", "records", "record",
    "users", "user", "accounts", "account", "members", "customers", "contacts", "subscribers",
    "orders", "order", "transactions", "payments", "products", "inventory", "items",
    "messages", "message", "comments", "comment", "posts", "post", "articles", "article",
    "tasks", "task", "todos", "todo", "notes", "note", "feedback", "bookings", "appointments",
    "cart", "history", "sessions", "news", "banners", "dataset", "collection",
    "leaderboard", "scores", "results", "votes", "likes", "favorites", "stats",
}

DATA_DIR_NAMES = {
    "data", "db", "database", "storage", "store", "jsondb", "json_db", "db_json",
    "datasets", "dataset", "localdata", "local_data", "appdata", "app_data",
}

DEPENDENCY_HINTS = (
    "lowdb", "json-server", "nedb", "node-json-db", "electron-store", "simple-json-db",
    "fs-json-store", "configstore", "tinydb", "jsonstore", "shelve", "sqlitedict", "diskcache",
)

STATIC_DIR_HINTS = {
    "static", "assets", "asset", "public", "templates", "template", "vendor",
    "locale", "locales", "i18n", "lang",
}

SOURCE_CODE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".php", ".rb", ".go"}
JSON_SUFFIXES = {".json", ".jsonl", ".ndjson"}
SCRIPT_SUFFIXES = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}
RECORD_KEY_HINTS = {
    "id", "_id", "uuid", "created_at", "createdat", "create_time", "updated_at",
    "timestamp", "time", "user_id", "username", "email", "status",
}

QUOTE = "['\"]"
PATH_LITERAL_RE = re.compile(
    QUOTE + r"([^" + QUOTE[1:-1] + r"\r\n]{1,200}?\.(?:json|jsonl|ndjson|csv|tsv|txt|dat|log))" + QUOTE,
    re.IGNORECASE,
)
WRITE_HINT_RE = re.compile(
    r"(?i)("
    r"writefile|writefilesync|appendfile|appendfilesync|createwritestream|"
    r"fs\.write|json\.dump|to_json|to_csv|writerow|writerows|"
    r"\.writelines?\s*\(|\.write_text\s*\(|\.write_bytes\s*\(|"
    r"open\s*\([^)\n]*,\s*" + QUOTE + r"[wax]\+?b?" + QUOTE + r"|"
    r"\.persist\s*\(|\.writeJSON\s*\(|"
    r"JSONFilePreset|JSONFile|JSONFileSync|datastore|localStorage"
    r")"
)

MAX_READ_BYTES = 512 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find runtime data files (JSON / JS storage) that would leak author data on clone or download."
    )
    parser.add_argument("project_dir", help="Project source directory that will be uploaded.")
    parser.add_argument("--write", action="store_true", help=f"Write/merge {MANIFEST_FILENAME} into the project.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when undeclared data files are found.")
    parser.add_argument("--json", action="store_true", help="Print the result as JSON.")
    return parser.parse_args()


def iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name.lower() not in EXCLUDED_DIR_NAMES]
        current_path = Path(current)
        for name in sorted(files):
            yield current_path / name


def read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_READ_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def normalized(raw: str) -> str:
    text = str(raw or "").replace("\\", "/").strip().strip("/")
    if not text or ":" in text:
        return ""
    parts = []
    for part in text.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            return ""
        parts.append(part)
    return "/".join(parts)


def looks_like_dataset(payload) -> str:
    sample = []
    if isinstance(payload, list):
        sample = payload[:20]
        if not sample:
            return "顶层是空数组"
    elif isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list) and value:
                sample = value[:20]
                break
        if not sample:
            return ""
        if len(payload) <= 3 and sample and all(isinstance(item, dict) for item in sample):
            return "对象里嵌套了记录数组"
    else:
        return ""

    for item in sample:
        if not isinstance(item, dict):
            continue
        keys = {str(key).lower() for key in item}
        if keys & RECORD_KEY_HINTS:
            return "元素包含 id / 时间戳等记录字段"
    if len(sample) >= 3 and all(isinstance(item, dict) for item in sample):
        return "是多个同构对象组成的列表"
    return ""


def read_manifest(root: Path) -> list[str]:
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    storage = payload.get("storage")
    raw = None
    if isinstance(storage, dict):
        raw = storage.get("paths") or storage.get("runtime_data")
    if raw is None:
        raw = (
            payload.get("runtime_data")
            or payload.get("dynamic_data_paths")
            or payload.get("data_paths")
            or []
        )
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        path = normalized(item if isinstance(item, str) else (item or {}).get("path", ""))
        if path and path not in result:
            result.append(path)
    return result


def write_manifest(root: Path, paths: list[str], storage_type: str) -> Path:
    manifest_path = root / MANIFEST_FILENAME
    payload = {}
    if manifest_path.is_file():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(existing, dict):
                payload = existing
        except (OSError, ValueError):
            payload = {}
    payload["schema"] = payload.get("schema") or MANIFEST_SCHEMA
    if storage_type:
        payload["storage_type"] = payload.get("storage_type") or storage_type
    existing_paths = [normalized(item) for item in (payload.get("runtime_data") or []) if isinstance(item, str)]
    merged = []
    for path in [*existing_paths, *paths]:
        if path and path not in merged:
            merged.append(path)
    payload["runtime_data"] = merged
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    declared = read_manifest(root)

    dependency_hits = []
    for candidate in ("package.json", "requirements.txt", "Pipfile", "pyproject.toml"):
        target = root / candidate
        if target.is_file():
            text = read_text(target).lower()
            for hint in DEPENDENCY_HINTS:
                if hint in text and hint not in dependency_hits:
                    dependency_hits.append(hint)

    write_targets = {}
    for source_file in iter_files(root):
        if source_file.suffix.lower() not in SOURCE_CODE_SUFFIXES:
            continue
        text = read_text(source_file)
        if not text:
            continue
        has_write = bool(WRITE_HINT_RE.search(text))
        for match in PATH_LITERAL_RE.finditer(text):
            path = normalized(match.group(1))
            if not path or path in write_targets:
                continue
            if not (root / path).exists():
                continue
            where = source_file.relative_to(root).as_posix()
            write_targets[path] = (
                f"{where} 中有写入操作" if has_write else f"{where} 引用了该文件"
            )

    candidates: dict[str, tuple[str, str]] = {}
    for path, reason in write_targets.items():
        candidates[path] = ("code_write", reason)

    for file_path in iter_files(root):
        relative = file_path.relative_to(root).as_posix()
        suffix = file_path.suffix.lower()
        if suffix not in JSON_SUFFIXES and suffix not in SCRIPT_SUFFIXES:
            continue
        parts = [part.lower() for part in Path(relative).parts]
        if any(part in STATIC_DIR_HINTS for part in parts[:-1]):
            continue
        stem = file_path.stem.lower()
        by_name = stem in DATA_FILE_STEMS
        in_data_dir = len(parts) >= 2 and parts[0] in DATA_DIR_NAMES
        if not by_name and not in_data_dir:
            continue
        if relative in candidates:
            continue
        if suffix in JSON_SUFFIXES:
            text = read_text(file_path)
            shape = ""
            if text:
                try:
                    shape = looks_like_dataset(json.loads(text))
                except ValueError:
                    shape = ""
            if dependency_hits:
                candidates[relative] = ("dependency", f"依赖清单命中 {'、'.join(dependency_hits[:3])}")
            elif shape:
                candidates[relative] = ("dataset", shape)
            else:
                candidates[relative] = ("filename", f"文件名「{file_path.name}」常见于文件型存储")
        else:
            candidates[relative] = ("filename", f"脚本「{file_path.name}」常见于文件型存储")

    for current, dirs, _files in os.walk(root):
        dirs[:] = [name for name in dirs if name.lower() not in EXCLUDED_DIR_NAMES]
        for name in list(dirs):
            if name.lower() not in DATA_DIR_NAMES:
                continue
            relative = (Path(current) / name).relative_to(root).as_posix()
            if any((Path(current) / name).iterdir()):
                candidates.setdefault(relative, ("directory", f"目录「{name}/」常见于运行期数据目录"))

    # 目录已覆盖的文件不再单独列出，声明更干净
    covered_dirs = [path for path, (kind, _reason) in candidates.items() if kind == "directory"]
    for path in [p for p in candidates if p not in covered_dirs]:
        if any(path.startswith(f"{directory}/") for directory in covered_dirs):
            candidates.pop(path, None)

    declared_set = set(declared)
    undeclared = sorted(
        path for path in candidates
        if path not in declared_set and not any(path.startswith(f"{item}/") for item in declared_set)
    )

    storage_type = "js_module" if any(Path(path).suffix.lower() in SCRIPT_SUFFIXES for path in candidates) else "json_file"

    result = {
        "project_dir": str(root),
        "manifest": MANIFEST_FILENAME if (root / MANIFEST_FILENAME).is_file() else None,
        "declared_paths": declared,
        "dependency_hints": dependency_hits,
        "candidates": [
            {"path": path, "source": kind, "reason": reason}
            for path, (kind, reason) in sorted(candidates.items())
        ],
        "undeclared_paths": undeclared,
        "storage_type": storage_type,
    }

    if args.write:
        written = write_manifest(root, sorted(candidates.keys()), storage_type)
        result["written_manifest"] = str(written)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"project: {root}")
        if declared:
            print(f"declared in {MANIFEST_FILENAME}: {', '.join(declared)}")
        else:
            print(f"declared in {MANIFEST_FILENAME}: (none)")
        if dependency_hits:
            print(f"file-storage dependencies: {', '.join(dependency_hits)}")
        if candidates:
            print("runtime data candidates:")
            for path, (kind, reason) in sorted(candidates.items()):
                mark = "OK " if path in declared_set else "!! "
                print(f"  {mark}{path}  [{kind}] {reason}")
        else:
            print("runtime data candidates: none")
        if args.write:
            print(f"wrote {result['written_manifest']}")
        if undeclared:
            print("")
            print("Undeclared data files detected. Add them to "
                  f"{MANIFEST_FILENAME} (or rerun with --write), and make sure their uploaded "
                  "content is an empty template instead of real records.")
        else:
            print("")
            print("All detected data files are declared.")

    if args.strict and undeclared:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
