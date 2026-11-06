#!/usr/bin/env python3
"""
Build a clean zip package and release metadata JSON for webcraft.

Example:
  python scripts/build_release_bundle.py --output-dir SKILLS --site-base https://www.vicoco.cn --site-flavor cn
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SKILL_NAME = "webcraft"
IGNORE_PARTS = {"__pycache__", ".git", ".idea", ".vscode"}
IGNORE_SUFFIXES = {".pyc", ".pyo"}

# A SKILL package may only contain these paths. Everything else in the repository
# (.claude-plugin/, marketplace.json, README.md, VERSION, LICENSE, ...) is
# repository metadata and must stay out of the zip.
ALLOWED_ROOT_FILES = {"SKILL.md", "agents/openai.yaml"}
ALLOWED_DIR_PREFIXES = ("scripts/", "references/", "assets/")
ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a clean VicroCode skill release bundle.")
    parser.add_argument("--skill-dir", default=str(Path(__file__).resolve().parents[1]), help="Local skill root.")
    parser.add_argument("--output-dir", required=True, help="Directory to place the zip and JSON metadata.")
    parser.add_argument("--site-base", required=True, help="Public site base URL, such as https://www.vicoco.cn")
    parser.add_argument("--site-flavor", default="cn", choices=["cn", "global"], help="Release site flavor.")
    parser.add_argument("--release-notes", default="", help="Optional release notes stored in metadata.")
    return parser.parse_args()


def read_version(skill_dir: Path) -> str:
    version_file = skill_dir / "VERSION"
    if not version_file.exists():
        raise FileNotFoundError(f"Missing VERSION file: {version_file}")
    return version_file.read_text(encoding="utf-8").strip()


def should_include(name: str) -> bool:
    """Keep the package to the official SKILL layout only."""
    parts = name.split("/")
    if any(part in IGNORE_PARTS for part in parts):
        return False
    if Path(name).suffix.lower() in IGNORE_SUFFIXES:
        return False
    if name in ALLOWED_ROOT_FILES:
        return True
    if not name.startswith(ALLOWED_DIR_PREFIXES):
        return False
    return Path(name).suffix.lower() in ALLOWED_SUFFIXES


def write_zip(skill_dir: Path, zip_path: Path) -> list[str]:
    included: list[str] = []
    skipped: list[str] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_dir():
                continue
            name = path.relative_to(skill_dir).as_posix()
            if not should_include(name):
                skipped.append(name)
                continue
            zf.write(path, f"{skill_dir.name}/{name}")
            included.append(name)
    if "SKILL.md" not in included:
        raise SystemExit("Refusing to build: SKILL.md is missing from the package.")
    return skipped


def verify_zip(zip_path: Path) -> list[str]:
    """Re-read the archive and assert every entry matches the allowed layout."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [item.filename for item in zf.infolist() if not item.is_dir()]
    bad: list[str] = []
    for full in names:
        prefix, _, relative = full.partition("/")
        if not relative or not should_include(relative):
            bad.append(full)
    if bad:
        raise SystemExit("Refusing to release: disallowed entries in zip: " + ", ".join(bad))
    return names


def sha256_of_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_metadata(skill_name: str, version: str, zip_url: str, zip_sha256: str, size_bytes: int, site_flavor: str, release_notes: str) -> dict[str, object]:
    return {
        "skill_name": skill_name,
        "version": version,
        "manifest_schema": "vicrocode.skill.release.v1",
        "published_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "zip_url": zip_url,
        "zip_sha256": zip_sha256,
        "size_bytes": size_bytes,
        "site_flavor": site_flavor,
        "release_notes": release_notes,
    }


def main() -> int:
    args = parse_args()
    skill_dir = Path(args.skill_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    skill_name = skill_dir.name or DEFAULT_SKILL_NAME
    version = read_version(skill_dir)
    zip_path = output_dir / f"{skill_name}.zip"
    json_path = output_dir / f"{skill_name}.json"

    skipped = write_zip(skill_dir, zip_path)
    entries = verify_zip(zip_path)
    zip_sha256 = sha256_of_file(zip_path)
    size_bytes = os.path.getsize(zip_path)
    zip_url = f"{str(args.site_base).rstrip('/')}/skills/{skill_name}.zip"

    metadata = build_metadata(
        skill_name=skill_name,
        version=version,
        zip_url=zip_url,
        zip_sha256=zip_sha256,
        size_bytes=size_bytes,
        site_flavor=args.site_flavor,
        release_notes=args.release_notes,
    )
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"zip={zip_path}")
    print(f"json={json_path}")
    print(f"version={version}")
    print(f"sha256={zip_sha256}")
    print(f"files={len(entries)}")
    for name in entries:
        print(f"  + {name}")
    if skipped:
        visible = [name for name in skipped if not name.startswith(".git/")]
        print(f"skipped={len(skipped)} (.git entries hidden)")
        for name in visible:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
