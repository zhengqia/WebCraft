#!/usr/bin/env python3
"""
Check the local WebCraft skill version against a remote zip package.

Usage examples:
  python scripts/check_and_install_update.py
  python scripts/check_and_install_update.py --json
  python scripts/check_and_install_update.py --apply
  python scripts/check_and_install_update.py --url https://www.vicoco.cn/SKILLS/webcraft.zip --apply
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


VERSION_PATTERN = re.compile(r"v(\d{4}-\d{2}-\d{2})(?:\.(\d+))?")
DEFAULT_URL = "https://www.vicoco.cn/SKILLS/webcraft.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check and optionally install the latest WebCraft skill package.")
    parser.add_argument("--skill-dir", default=str(Path(__file__).resolve().parents[1]), help="Local skill directory. Defaults to the current skill root.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Remote zip package URL.")
    parser.add_argument("--metadata-url", default="", help="Optional remote metadata JSON URL. Defaults to the zip URL with .json extension.")
    parser.add_argument("--apply", action="store_true", help="Install the downloaded package if its version is newer than local.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def read_version_from_text(text: str) -> str | None:
    match = VERSION_PATTERN.search(text)
    if not match:
      return None
    return match.group(0)


def read_local_version(skill_dir: Path) -> str | None:
    version_file = skill_dir / "VERSION"
    if version_file.exists():
        text = version_file.read_text(encoding="utf-8", errors="ignore").strip()
        parsed = read_version_from_text(text)
        if parsed:
            return parsed

    for candidate in [
        skill_dir / "references" / "version-and-site-selection.md",
        skill_dir / "SKILL.md",
    ]:
        if candidate.exists():
            parsed = read_version_from_text(candidate.read_text(encoding="utf-8", errors="ignore"))
            if parsed:
                return parsed
    return None


def normalize_version(version: str | None) -> tuple[int, int, int, int] | None:
    if not version:
        return None
    match = VERSION_PATTERN.fullmatch(version.strip())
    if not match:
        return None
    y, m, d = match.group(1).split("-")
    revision = int(match.group(2) or 0)
    return int(y), int(m), int(d), revision


def derive_metadata_url(zip_url: str) -> str:
    if zip_url.lower().endswith(".zip"):
        return f"{zip_url[:-4]}.json"
    return f"{zip_url}.json"


def find_skill_root(root: Path) -> Path | None:
    if (root / "SKILL.md").exists():
        return root
    for path in root.rglob("SKILL.md"):
        return path.parent
    return None


def read_remote_zip(url: str, temp_dir: Path) -> tuple[Path, str | None]:
    zip_path = temp_dir / "skill.zip"
    urllib.request.urlretrieve(url, zip_path)
    extract_dir = temp_dir / "extract"
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    skill_root = find_skill_root(extract_dir)
    if skill_root is None:
        raise RuntimeError("Remote package does not contain SKILL.md")
    remote_version = read_local_version(skill_root)
    return skill_root, remote_version


def read_remote_metadata(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url) as response:
        data = response.read().decode("utf-8")
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise RuntimeError("Remote metadata is not a JSON object")
    return payload


def install_skill(src_root: Path, dest_root: Path) -> None:
    backup_dir = dest_root.parent / f"{dest_root.name}.bak"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if dest_root.exists():
        shutil.move(str(dest_root), str(backup_dir))
    shutil.copytree(src_root, dest_root)


def main() -> int:
    args = parse_args()
    skill_dir = Path(args.skill_dir).resolve()
    local_version = read_local_version(skill_dir)
    result: dict[str, object] = {
        "skill_dir": str(skill_dir),
        "remote_url": args.url,
        "metadata_url": args.metadata_url or derive_metadata_url(args.url),
        "local_version": local_version,
        "remote_version": None,
        "update_available": False,
        "updated": False,
        "message": "",
    }

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            metadata_url = str(result["metadata_url"])
            remote_zip_url = args.url
            remote_version = None

            try:
                metadata = read_remote_metadata(metadata_url)
                remote_version = str(metadata.get("version") or "").strip() or None
                remote_zip_url = str(metadata.get("zip_url") or args.url).strip() or args.url
                result["remote_manifest"] = metadata
            except Exception as exc:
                result["metadata_warning"] = f"metadata_fetch_failed: {exc}"

            remote_root, zip_version = read_remote_zip(remote_zip_url, tmp_path)
            if remote_version is None:
                remote_version = zip_version
            result["remote_version"] = remote_version
            result["remote_url"] = remote_zip_url

            local_norm = normalize_version(local_version)
            remote_norm = normalize_version(remote_version)

            if local_norm is None or remote_norm is None:
                result["message"] = "Could not compare versions reliably."
            elif remote_norm > local_norm:
                result["update_available"] = True
                result["message"] = f"Newer version available: {remote_version} > {local_version}"
                if args.apply:
                    install_skill(remote_root, skill_dir)
                    result["updated"] = True
                    result["message"] = f"Updated skill from {local_version} to {remote_version}"
            else:
                result["message"] = f"Local skill is up to date ({local_version})"

    except Exception as exc:
        result["message"] = f"Update check failed: {exc}"
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["message"])
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
        print(f"local_version={result['local_version']}")
        print(f"remote_version={result['remote_version']}")
        print(f"update_available={str(result['update_available']).lower()}")
        print(f"updated={str(result['updated']).lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
