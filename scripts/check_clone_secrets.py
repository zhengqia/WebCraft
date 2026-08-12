#!/usr/bin/env python3
"""Preflight a VicroCode upload tree for files and literals blocked by clone scanning."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


SENSITIVE_FILE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".npmrc", ".pypirc",
    "credentials", "credentials.json", "service-account.json", "service_account.json",
    "id_rsa", "id_ed25519",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".php", ".java", ".go", ".rb", ".rs",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".htm",
    ".sh", ".ps1", ".bat", ".cmd", ".properties", ".txt", ".md",
}
EXCLUDED_DIR_NAMES = {
    "runtime", "sourdown", ".git", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".idea", ".vscode", "logs", "log", "tmp", "temp",
}
KNOWN_SECRET_PATTERNS = (
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("Stripe secret", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    (
        "hard-coded credential",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|client[_-]?secret|password)\b"
            r"\s*[:=]\s*[\"']([^\"']{12,})[\"']"
        ),
    ),
)
SAFE_PLACEHOLDER_PARTS = {
    "your_api_key", "your-api-key", "replace_me", "replace-me", "example", "placeholder",
    "请填入您的apikey", "process.env", "os.getenv", "getenv(", "${", "{{",
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find sensitive files and likely hard-coded credentials before VicroCode clone scanning."
    )
    parser.add_argument("project_dir", help="Project source directory that will be uploaded.")
    return parser.parse_args()


def masked(value: str) -> str:
    value = str(value or "")
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name.lower() not in EXCLUDED_DIR_NAMES]
        current_path = Path(current)
        for filename in files:
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            lower_name = filename.lower()
            suffix = path.suffix.lower()
            if lower_name in SENSITIVE_FILE_NAMES or lower_name.startswith(".env.") or suffix in SENSITIVE_SUFFIXES:
                findings.append(f"{relative}: sensitive file must not be uploaded")
                continue
            if suffix not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 2 * 1024 * 1024:
                    continue
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                findings.append(f"{relative}: could not inspect ({exc})")
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                for label, pattern in KNOWN_SECRET_PATTERNS:
                    match = pattern.search(line)
                    if not match:
                        continue
                    value = match.group(1) if match.lastindex else match.group(0)
                    normalized = value.strip().lower()
                    if any(part in normalized for part in SAFE_PLACEHOLDER_PARTS):
                        continue
                    findings.append(f"{relative}:{line_number}: {label}: {masked(value)}")
                    break
    return findings


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: project directory does not exist: {root}", file=sys.stderr)
        return 2
    findings = scan(root)
    if findings:
        print("Clone secret preflight failed:")
        for finding in findings:
            print(f"- {finding}")
        print("Remove sensitive files/literals and use the VicroCode Credential Vault proxy, then run again.")
        return 1
    print(f"Clone secret preflight passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
