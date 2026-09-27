#!/usr/bin/env python3
"""Upload / update a project on VicroCode from the command line, and deploy it.

This script is the agent-facing entry point for the "智能部署" (agent deploy)
token. It talks to ``/api/agent-deploy/v1/*`` with a ``vco-wc-...`` token, so no
browser login is needed.

It keeps a local record file (``<project>/.vicrocode/deploy.json``) with the
token, project id and site, so later runs only need ``deploy --dir .``.

The record file MUST never be uploaded: the platform rejects it too, but this
script filters it out before building the request.

Only the Python standard library is used.

Usage::

    python scripts/vicrocode_deploy.py whoami   --dir . --token vco-wc-xxxx
    python scripts/vicrocode_deploy.py preflight --dir .
    python scripts/vicrocode_deploy.py deploy   --dir . --manifest manifest.json
    python scripts/vicrocode_deploy.py deploy   --dir . --title "AI 去水印工具"
    python scripts/vicrocode_deploy.py deploy   --dir . --id 1234   # 只升级 #1234
    python scripts/vicrocode_deploy.py sync     --dir . --summary "改了什么" --files a.html,b.js
    python scripts/vicrocode_deploy.py log      --dir . --summary "只记一笔开发记录"
    python scripts/vicrocode_deploy.py run      --dir .      # start Python deploy
    python scripts/vicrocode_deploy.py status   --dir .      # deploy status
    python scripts/vicrocode_deploy.py stop     --dir .      # stop the app

Every develop/upload action is also appended to the project-local dev log
(``<project>/.vicrocode/dev-log.md`` and ``.vicrocode/dev-log.jsonl``), which is
never uploaded.

Exit codes::

    0  success
    1  platform rejected the request (the error code is printed)
    2  usage / local environment problem (missing token, bad directory, ...)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RECORD_DIR = ".vicrocode"
RECORD_FILE = "deploy.json"
RECORD_SCHEMA = "vicrocode.agent-deploy.v1"
MANIFEST_FILENAME = "vicrocode.project.json"
DEVLOG_FILE = "dev-log.md"
DEVLOG_JSONL = "dev-log.jsonl"
DEVLOG_MAX_FILES = 40

SITE_BASES = {
    "cn": "https://www.vicoco.cn",
    "global": "https://www.vicrocode.com",
}
DEFAULT_SITE = "cn"
DEFAULT_TIMEOUT = 300
NETWORK_RETRIES = 3
LOG_TAIL_LINES = 100

# Mirrors backend/api/services/project_intake_service.py
IGNORED_DIR_PARTS = {
    ".vicrocode", ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules",
    "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".next", ".nuxt", "runtime", "sourdown", "logs", "log",
}
IGNORED_FILE_NAMES = {
    ".ds_store", "thumbs.db", "desktop.ini", ".npmrc", ".pypirc", ".netrc",
}
IGNORED_FILE_SUFFIXES = (".pyc", ".pyo", ".pyd", ".log")
SECRET_FILE_SUFFIXES = (".pem", ".key", ".pfx", ".p12", ".keystore", ".jks")
SECRET_FILE_PREFIXES = ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")

MAX_SINGLE_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 90 * 1024 * 1024


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def die(message: str, code: int = 2) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def info(message: str) -> None:
    print(message)


def normalize_rel_path(raw: str) -> str:
    text = str(raw or "").replace("\\", "/").strip()
    if text.startswith("./"):
        text = text[2:]
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return ""
    if re.match(r"^[a-zA-Z]:", parts[0]):
        return ""
    return "/".join(parts)


def is_ignored(relative: str) -> bool:
    parts = [part.lower() for part in relative.split("/")]
    if any(part in IGNORED_DIR_PARTS for part in parts[:-1]):
        return True
    if parts[-1] in IGNORED_DIR_PARTS:
        return True
    name = parts[-1]
    if name in IGNORED_FILE_NAMES:
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    if name.endswith(SECRET_FILE_SUFFIXES):
        return True
    if any(name.startswith(prefix) for prefix in SECRET_FILE_PREFIXES):
        return True
    if name.endswith(IGNORED_FILE_SUFFIXES):
        return True
    return False


def ascii_filename(basename: str, index: int) -> str:
    """HTTP headers must stay ASCII; the real path travels in online_files_paths."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", basename).strip("._")
    if not cleaned:
        cleaned = f"file{index}"
    return cleaned[:120]


# ---------------------------------------------------------------------------
# record file
# ---------------------------------------------------------------------------

def record_path(project_dir: Path) -> Path:
    return project_dir / RECORD_DIR / RECORD_FILE


def read_json_file(path: Path) -> dict:
    """读取 JSON 文件（容忍 Windows 工具写出的 UTF-8 BOM）。"""
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig", errors="ignore"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_record(project_dir: Path) -> dict:
    return read_json_file(record_path(project_dir))


def save_record(project_dir: Path, record: dict) -> Path:
    path = record_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def warn_if_not_gitignored(project_dir: Path) -> None:
    """The record file holds a token; remind the user to keep it out of git."""
    gitignore = project_dir / ".gitignore"
    if not (project_dir / ".git").is_dir() and not gitignore.is_file():
        return
    try:
        text = gitignore.read_text(encoding="utf-8", errors="ignore") if gitignore.is_file() else ""
    except OSError:
        text = ""
    if RECORD_DIR not in text:
        info(f"提示：建议把 {RECORD_DIR}/ 加入 .gitignore，避免令牌被提交到代码仓库。")


# ---------------------------------------------------------------------------
# project-local development log
# ---------------------------------------------------------------------------

def devlog_paths(project_dir: Path) -> tuple[Path, Path]:
    directory = project_dir / RECORD_DIR
    return directory / DEVLOG_FILE, directory / DEVLOG_JSONL


def split_list(raw: object) -> list[str]:
    """逗号 / 中文逗号 / 空白分隔的字符串转成去重后的列表。"""
    if raw in (None, ""):
        return []
    if isinstance(raw, (list, tuple)):
        items = [str(item) for item in raw]
    else:
        items = re.split(r"[,，\s]+", str(raw))
    result: list[str] = []
    for item in items:
        value = normalize_rel_path(item) or str(item).strip()
        if value and value not in result:
            result.append(value)
    return result


def append_dev_log(
    project_dir: Path,
    *,
    action: str,
    summary: str = "",
    files: list[str] | None = None,
    project_id: int = 0,
    run_url: str = "",
    result: str = "ok",
    detail: str = "",
) -> None:
    """把一次开发 / 修改 / 上传动作追加到项目目录内的开发记录。

    记录只写在 ``.vicrocode/`` 里（不会上传、不会随项目交付），用来回答
    「这个项目什么时候改过、改了什么、有没有传上去」。
    """
    markdown_path, jsonl_path = devlog_paths(project_dir)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S%z")
    file_list = [str(item) for item in (files or []) if str(item).strip()][:DEVLOG_MAX_FILES]
    entry = {
        "at": stamp,
        "action": action,
        "summary": summary,
        "project_id": int(project_id or 0),
        "run_url": run_url,
        "result": result,
        "files": file_list,
    }
    if detail:
        entry["detail"] = detail
    lines = [f"## {stamp} — {action} [{result}]"]
    if summary:
        lines.append(f"- 说明：{summary}")
    if entry["project_id"]:
        target = f"- 项目：#{entry['project_id']}"
        if run_url:
            target += f"  {run_url}"
        lines.append(target)
    elif run_url:
        lines.append(f"- 网址：{run_url}")
    if file_list:
        lines.append(f"- 涉及文件（{len(file_list)}）：" + "、".join(file_list))
    if detail:
        lines.append(f"- 备注：{detail}")
    lines.append("")
    try:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        is_new = (not markdown_path.exists()) or markdown_path.stat().st_size == 0
        with markdown_path.open("a", encoding="utf-8") as handle:
            if is_new:
                handle.write("# WebCraft 开发与修改记录\n\n")
                handle.write(
                    "本文件由 scripts/vicrocode_deploy.py 自动追加，只保存在本地"
                    "（.vicrocode/ 不会上传、不会随项目交付）。\n\n"
                )
            handle.write("\n".join(lines) + "\n")
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        info(f"[提示] 开发记录写入失败（不影响本次结果）：{exc}")


def parse_project_id(raw: object) -> int:
    """把 --id / manifest.project_id 之类的输入转成正整数，非法时直接报错退出。"""
    text = str(raw or "").strip().lstrip("#").strip()
    if not text:
        return 0
    if not text.isdigit():
        raise SystemExit(die(f"--id 必须是数字项目 ID，收到的是：{raw}"))
    value = int(text)
    return value if value > 0 else 0


# ---------------------------------------------------------------------------
# local manifest
# ---------------------------------------------------------------------------

def read_project_manifest(project_dir: Path) -> dict:
    """Read vicrocode.project.json (runtime data declaration)."""
    return read_json_file(project_dir / MANIFEST_FILENAME)


def declared_runtime_data(manifest: dict) -> list[str]:
    if not isinstance(manifest, dict):
        return []
    storage = manifest.get("storage")
    raw = None
    if isinstance(storage, dict):
        raw = storage.get("paths") or storage.get("runtime_data")
    if raw is None:
        raw = (
            manifest.get("runtime_data")
            or manifest.get("dynamic_data_paths")
            or manifest.get("data_paths")
            or []
        )
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        value = item if isinstance(item, str) else (item or {}).get("path", "")
        path = normalize_rel_path(value)
        if path and path not in result:
            result.append(path)
    return result


# ---------------------------------------------------------------------------
# file scan
# ---------------------------------------------------------------------------

def collect_files(project_dir: Path, explicit: list[str] | None = None) -> tuple[list[tuple[str, Path]], list[str]]:
    """Return (files, skipped) where files is [(relative, absolute)]."""
    files: list[tuple[str, Path]] = []
    skipped: list[str] = []
    if explicit:
        for raw in explicit:
            relative = normalize_rel_path(raw)
            if not relative or is_ignored(relative):
                skipped.append(raw)
                continue
            absolute = project_dir / relative
            if absolute.is_file():
                files.append((relative, absolute))
            else:
                skipped.append(f"{raw} (不存在)")
        return sorted(files, key=lambda item: item[0]), skipped

    for current, dirs, names in os.walk(project_dir):
        dirs[:] = [name for name in dirs if name.lower() not in IGNORED_DIR_PARTS]
        current_path = Path(current)
        for name in sorted(names):
            absolute = current_path / name
            relative = normalize_rel_path(str(absolute.relative_to(project_dir).as_posix()))
            if not relative:
                continue
            if is_ignored(relative):
                skipped.append(relative)
                continue
            files.append((relative, absolute))
    return sorted(files, key=lambda item: item[0]), skipped


def package_hash(files: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for relative, absolute in files:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        try:
            with absolute.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"


def check_sizes(files: list[tuple[str, Path]]) -> list[str]:
    problems: list[str] = []
    total = 0
    for relative, absolute in files:
        try:
            size = absolute.stat().st_size
        except OSError:
            continue
        total += size
        if size > MAX_SINGLE_FILE_BYTES:
            problems.append(f"{relative} 单文件超过 20MB，请改用外部资源或不放入该项目")
    if total > MAX_TOTAL_BYTES:
        problems.append(f"项目总大小 {total / 1048576:.1f}MB 超过 90MB，请精简后再上传")
    return problems


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def encode_multipart(
    fields: list[tuple[str, str]],
    files: list[tuple[str, str, bytes]],
) -> tuple[bytes, str]:
    """Build a multipart/form-data body with only the standard library."""
    boundary = f"----VicroCodeAgent{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(str(value).encode("utf-8"))
        parts.append(b"\r\n")
    for name, filename, content in files:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        parts.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        parts.append(content)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def http_call(
    *,
    base_url: str,
    path: str,
    token: str,
    method: str = "POST",
    fields: list[tuple[str, str]] | None = None,
    files: list[tuple[str, str, bytes]] | None = None,
    json_body: dict | None = None,
    idempotency_key: str = "",
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, dict]:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "VicroCode-WebCraft-Deploy/1.0",
    }
    data = None
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif files is not None:
        data, content_type = encode_multipart(fields or [], files)
        headers["Content-Type"] = content_type
    elif fields:
        data = urllib.parse.urlencode(fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key[:64]

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_error: Exception | None = None
    for attempt in range(1, NETWORK_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return response.status, _safe_json(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            return exc.code, _safe_json(body)
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as exc:
            last_error = exc
            if attempt < NETWORK_RETRIES:
                time.sleep(2 * attempt)
                continue
    raise RuntimeError(f"网络请求失败（已重试 {NETWORK_RETRIES} 次）：{last_error}")


def _safe_json(body: str) -> dict:
    try:
        payload = json.loads(body) if body else {}
    except ValueError:
        return {"status": "error", "code": "INVALID_RESPONSE", "message": (body or "")[:500]}
    return payload if isinstance(payload, dict) else {"status": "error", "code": "INVALID_RESPONSE", "message": str(payload)[:500]}


# ---------------------------------------------------------------------------
# config resolution
# ---------------------------------------------------------------------------

def resolve_config(args) -> tuple[str, str, dict]:
    """Return (token, base_url, record)."""
    project_dir = Path(args.dir).expanduser().resolve()
    record = load_record(project_dir)
    token = (
        str(getattr(args, "token", "") or "").strip()
        or os.environ.get("VICROCODE_DEPLOY_TOKEN", "").strip()
        or str(record.get("token") or "").strip()
    )
    site = (
        str(getattr(args, "site", "") or "").strip().lower()
        or os.environ.get("VICROCODE_SITE", "").strip().lower()
        or str(record.get("site") or "").strip().lower()
        or DEFAULT_SITE
    )
    base_url = str(getattr(args, "site_base", "") or "").strip().rstrip("/")
    if not base_url:
        base_url = str(record.get("site_base") or "").strip().rstrip("/")
    if not base_url:
        base_url = SITE_BASES.get(site, SITE_BASES[DEFAULT_SITE])
    return token, base_url, record


def build_manifest(args, project_dir: Path, record: dict) -> dict:
    manifest: dict = {}
    manifest_path = str(getattr(args, "manifest", "") or "").strip()
    if manifest_path:
        path = Path(manifest_path)
        if not path.is_absolute():
            path = project_dir / path
        if not path.is_file():
            raise SystemExit(die(f"manifest 文件不存在：{path}"))
        loaded = read_json_file(path)
        if not loaded:
            raise SystemExit(die(f"manifest 为空或不是合法 JSON 对象：{path}"))
        manifest.update(loaded)

    for field, attr in (
        ("title", "title"),
        ("description", "description"),
        ("publish_status", "publish_status"),
        ("directory_name", "directory_name"),
        ("pageindex", "pageindex"),
    ):
        value = str(getattr(args, attr, "") or "").strip()
        if value:
            manifest[field] = value
    tags = str(getattr(args, "tags", "") or "").strip()
    if tags:
        manifest["tags"] = [item.strip() for item in re.split(r"[,，]", tags) if item.strip()]

    if record.get("project_id") and not manifest.get("project_id"):
        manifest["project_id"] = record["project_id"]
    if record.get("directory_name") and not manifest.get("directory_name"):
        manifest["directory_name"] = record["directory_name"]
    if record.get("site") and not manifest.get("site"):
        manifest["site"] = record["site"]

    # --id 优先级最高：明确指定「升级哪个应用」时，只更新该项目，绝不新建。
    explicit_id = parse_project_id(getattr(args, "project_id", ""))
    if explicit_id:
        previous = manifest.get("project_id")
        if previous not in (None, "", explicit_id, str(explicit_id)):
            info(f"[提示] --id {explicit_id} 覆盖了记录里的项目 #{previous}，本次只升级 #{explicit_id}。")
        manifest["project_id"] = explicit_id

    project_manifest = read_project_manifest(project_dir)
    declared = declared_runtime_data(project_manifest)
    if declared and not manifest.get("dynamic_data_paths"):
        manifest["dynamic_data_paths"] = declared
    return manifest


def site_base_for_manifest(manifest: dict, fallback: str) -> str:
    site = str(manifest.get("site") or "").strip().lower()
    if site in SITE_BASES:
        return SITE_BASES[site]
    return fallback


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def command_whoami(args) -> int:
    token, base_url, _record = resolve_config(args)
    if not token:
        return die("缺少智能部署令牌：请用 --token vco-wc-xxx 或设置 VICROCODE_DEPLOY_TOKEN")
    status, payload = http_call(base_url=base_url, path="/api/agent-deploy/v1/whoami/", token=token, method="GET")
    if status >= 400 or payload.get("status") != "ok":
        return die(payload.get("message") or f"令牌校验失败（HTTP {status}）", 1)
    data = payload.get("data") or {}
    info(f"令牌可用：{data.get('username')} / {data.get('key_name')} / 剩余额度 "
         f"{data.get('daily_request_limit')} - {data.get('today_request_count')}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_preflight(args) -> int:
    token, base_url, record = resolve_config(args)
    project_dir = Path(args.dir).expanduser().resolve()
    if not project_dir.is_dir():
        return die(f"目录不存在：{project_dir}")

    manifest = build_manifest(args, project_dir, record)
    files, skipped = collect_files(project_dir, args.only)
    problems = check_sizes(files)

    if args.dry_run or not token:
        payload = {
            "status": "ok",
            "data": {
                "dry_run": True,
                "file_count": len(files),
                "files": [relative for relative, _ in files][:200],
                "skipped": skipped,
                "problems": problems,
                "manifest": manifest,
            },
        }
        if not token:
            info("未检测到令牌，已执行本地预检（配置令牌后可做平台预检）。")
        return _print_payload(payload, args.json, problems)

    body_files: list[tuple[str, str, bytes]] = []
    if getattr(args, "with_files", False):
        for index, (relative, absolute) in enumerate(files):
            body_files.append((
                f"online_files[{index}]",
                ascii_filename(Path(relative).name, index),
                absolute.read_bytes(),
            ))
        fields: list[tuple[str, str]] = [
            ("manifest", json.dumps(manifest, ensure_ascii=False)),
            ("online_files_paths", json.dumps(
                {str(index): relative for index, (relative, _) in enumerate(files)}, ensure_ascii=False)),
        ]
    else:
        # 轻量预检：只把文件清单交给平台，不上传文件本体
        manifest_with_paths = dict(manifest)
        manifest_with_paths["file_paths"] = [relative for relative, _ in files]
        fields = [("manifest", json.dumps(manifest_with_paths, ensure_ascii=False))]

    status, payload = http_call(
        base_url=base_url,
        path="/api/agent-deploy/v1/preflight/",
        token=token,
        fields=fields,
        files=body_files or None,
    )
    if status >= 400:
        return die(payload.get("message") or f"预检失败（HTTP {status}）", 1)
    data = payload.get("data") or {}
    if skipped:
        data.setdefault("warnings", []).extend(
            [f"本地已跳过：{item}" for item in skipped]
        )
    if problems:
        data.setdefault("issues", []).extend(
            [{"code": "SIZE_LIMIT", "message": item, "fix": "精简文件后重试"} for item in problems]
        )
        data["ok"] = False
    return _print_payload(payload, args.json, problems, exit_on_issues=bool(data.get("issues")))


def _print_payload(payload: dict, as_json: bool, problems: list[str] | None = None, *, exit_on_issues: bool = False) -> int:
    data = payload.get("data") or {}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif data.get("dry_run"):
        info(f"本地预检：共 {data.get('file_count', 0)} 个文件将上传")
        for relative in data.get("files") or []:
            info(f"  {relative}")
        for item in data.get("skipped") or []:
            info(f"  [跳过] {item}")
        for problem in problems or []:
            info(f"[问题] {problem}")
    else:
        info(f"目标动作：{data.get('target_action', '-')}  目录名：{data.get('directory_name', '-')}")
        if data.get("run_url"):
            info(f"当前网址：{data['run_url']}")
        info(f"项目类型：{data.get('project_kind', '-')}  文件数：{(data.get('stats') or {}).get('file_count', '-')}")
        auto = data.get("auto_fill") or {}
        if auto:
            info(f"自动生成标题：{auto.get('title', '')}")
            info(f"自动生成描述：{auto.get('description', '')}")
        for issue in data.get("issues") or []:
            info(f"[问题] {issue.get('code')}: {issue.get('message')} → {issue.get('fix', '')}")
        for warning in data.get("warnings") or []:
            info(f"[提示] {warning}")
        for problem in problems or []:
            info(f"[问题] {problem}")
    issues = data.get("issues") or []
    if exit_on_issues and issues:
        return 1
    return 0


def _project_state(token: str, base_url: str, project_id: int) -> dict:
    """查目标项目当前状态（失败时返回空字典，不影响主流程）。"""
    if not token or not project_id:
        return {}
    status, payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/status/",
        token=token,
        method="GET",
    )
    if status >= 400:
        return {}
    return payload.get("data") or {}


def _stop_project(token: str, base_url: str, project_id: int) -> bool:
    """停止运行中的项目（幂等：本来没运行也算成功）。"""
    if not token or not project_id:
        return False
    status, payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/",
        token=token,
        json_body={"action": "stop"},
    )
    if status >= 400 or payload.get("status") != "ok":
        info(f"[提示] 停止未成功：{payload.get('message') or status}")
        return False
    return True


def _start_project(token: str, base_url: str, project_id: int) -> tuple[int, dict]:
    return http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/",
        token=token,
        json_body={"action": "run", "max_attempts": 3},
    )


def command_deploy(args) -> int:
    token, base_url, record = resolve_config(args)
    project_dir = Path(args.dir).expanduser().resolve()
    if not project_dir.is_dir():
        return die(f"目录不存在：{project_dir}")
    if not token:
        return die(
            "缺少智能部署令牌。请先在 VicroCode「我的令牌 - 智能部署」创建令牌，"
            "然后用 --token vco-wc-xxx 传一次（之后会记录在 .vicrocode/deploy.json）。"
        )

    manifest = build_manifest(args, project_dir, record)
    explicit_id = parse_project_id(getattr(args, "project_id", ""))
    if explicit_id:
        info(f"[升级模式] 目标项目 #{explicit_id}：只更新文件，不会新建项目。")
    files, skipped = collect_files(project_dir, args.only)
    if not files:
        return die("没有可上传的文件（检查 --only 或目录是否为空）")
    problems = check_sizes(files)
    if problems and not args.force:
        for problem in problems:
            info(f"[问题] {problem}")
        append_dev_log(
            project_dir,
            action="upload",
            summary="上传前本地检查未通过",
            files=[relative for relative, _ in files],
            result="failed",
            detail="；".join(problems),
        )
        return die("存在体积超限的文件，请精简后重试（或用 --force 跳过本地检查）", 1)

    digest = package_hash(files)
    if (
        not args.force
        and record.get("project_id")
        and record.get("last_package_hash") == digest
    ):
        info("内容与上次上传完全一致，已跳过上传（如需强制重传请加 --force）。")
        if record.get("run_url"):
            info(f"网址：{record['run_url']}")
        append_dev_log(
            project_dir,
            action="upload",
            summary="内容与上次完全一致，未重复上传",
            files=[relative for relative, _ in files],
            project_id=int(record.get("project_id") or 0),
            run_url=str(record.get("run_url") or ""),
            result="skipped",
        )
        return 0

    body_files: list[tuple[str, str, bytes]] = []
    paths: dict[str, str] = {}
    for index, (relative, absolute) in enumerate(files):
        try:
            content = absolute.read_bytes()
        except OSError as exc:
            return die(f"读取文件失败：{relative} ({exc})")
        body_files.append((f"online_files[{index}]", ascii_filename(Path(relative).name, index), content))
        paths[str(index)] = relative

    fields = [
        ("manifest", json.dumps(manifest, ensure_ascii=False)),
        ("online_files_paths", json.dumps(paths, ensure_ascii=False)),
    ]
    # Python 项目：平台不允许在运行中更新文件（可能直接拒绝，也可能静默不生效），
    # 所以先停、传完再自动恢复上线，避免出现「改了代码但网址没变」。
    target_id = int(manifest.get("project_id") or record.get("project_id") or 0)
    target_state = _project_state(token, base_url, target_id)
    deploy_status = str(target_state.get("deploy_status") or "")
    is_python_target = bool(target_state.get("is_python"))
    was_live = bool(target_state.get("healthy")) or deploy_status in ("success", "running")
    # 上次部署失败说明进程已崩：也要先停一次，清掉平台残留的「运行中」记录
    restart_after = was_live or deploy_status == "failed"
    stopped_for_upload = False
    if is_python_target and restart_after:
        info("检测到 Python 项目已部署过：先停止，以便写入新文件…")
        stopped_for_upload = _stop_project(token, base_url, target_id)

    def _upload_once() -> tuple[int, dict]:
        info(f"正在上传 {len(files)} 个文件到 {base_url} …")
        # 幂等键必须每次请求都唯一：平台会缓存同键请求的响应，
        # 若按键推导（例如含内容哈希），重复上传同一份内容会被当成重复请求，
        # 结果「返回成功但不写文件」。内容未变化的去重由上面的 last_package_hash 在本地完成。
        return http_call(
            base_url=base_url,
            path="/api/agent-deploy/v1/deploy/",
            token=token,
            fields=fields,
            files=body_files,
            idempotency_key=uuid.uuid4().hex,
        )

    status, payload = _upload_once()
    if status >= 400 and "正在运行中" in str(payload.get("message") or ""):
        # 兜底：状态查询没看出在运行，但平台仍拒绝更新 → 停止后重试一次
        info("[提示] 项目正在运行导致更新被拒：先停止后重试…")
        if _stop_project(token, base_url, target_id):
            stopped_for_upload = True
            restart_after = True
            status, payload = _upload_once()
    if status >= 400 or payload.get("status") != "ok":
        code = payload.get("code") or f"HTTP_{status}"
        info(f"[失败] {code}: {payload.get('message')}")
        if code == "DIRECTORY_NAME_TAKEN":
            info("建议：换一个 directory_name，或先用 --directory-name 指定唯一名称。")
        if code == "PROJECT_NOT_FOUND":
            info("建议：确认 --id 对应的项目属于当前令牌账号；如果要新建项目，请去掉 --id。")
        if stopped_for_upload:
            # 为了上传把线上停掉了，上传又失败：赶紧恢复运行，避免留下一个挂掉的站点
            info("[提示] 上传失败，正在把项目恢复到运行状态…")
            _start_project(token, base_url, target_id)
        append_dev_log(
            project_dir,
            action="upload",
            summary=f"上传失败：{code}",
            files=[relative for relative, _ in files],
            project_id=target_id,
            result="failed",
            detail=str(payload.get("message") or ""),
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    data = payload.get("data") or {}
    run_url = str(data.get("run_url") or "")
    record.update({
        "schema": RECORD_SCHEMA,
        "token": token,
        "site": str(manifest.get("site") or record.get("site") or DEFAULT_SITE),
        "site_base": site_base_for_manifest(manifest, base_url),
        "project_id": data.get("project_id"),
        "directory_name": data.get("directory_name"),
        "run_url": run_url,
        "project_kind": "python" if data.get("is_python") else "static",
        "last_upload_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "last_package_hash": digest,
        "file_count": len(files),
    })
    if manifest.get("python", {}).get("auto_deploy") if isinstance(manifest.get("python"), dict) else False:
        record["auto_deploy"] = True
    history = record.get("history")
    if not isinstance(history, list):
        history = []
    history = history[-19:] + [{
        "at": record["last_upload_at"],
        "action": data.get("action") or "deploy",
        "project_id": data.get("project_id"),
        "file_count": len(files),
    }]
    record["history"] = history
    if not args.no_save:
        save_record(project_dir, record)
        warn_if_not_gitignored(project_dir)

    info(f"上传成功（{data.get('action')}）：项目 #{data.get('project_id')}")
    info(f"网址：{run_url}")
    for warning in data.get("warnings") or []:
        info(f"[提示] {warning}")
    uploaded_files = [relative for relative, _ in files]
    append_dev_log(
        project_dir,
        action="upload",
        summary=(
            f"已{'更新' if data.get('action') == 'update' else '新建'}项目并上传 {len(uploaded_files)} 个文件"
        ),
        files=uploaded_files,
        project_id=int(data.get("project_id") or 0),
        run_url=run_url,
        result="ok",
        detail=f"平台动作：{data.get('action') or 'deploy'}",
    )
    if data.get("is_python"):
        info(f"Python 项目：入口 {data.get('entry_file') or '-'}，框架 {data.get('framework') or '-'}")
        deployed_id = int(data.get("project_id") or 0)
        if restart_after:
            info("正在自动重新部署，保持/恢复网址可访问…")
            run_status, run_payload = _start_project(token, base_url, deployed_id)
            if run_status >= 400 or run_payload.get("status") != "ok":
                info(
                    f"[提示] 自动重新部署未提交成功：{run_payload.get('message') or run_status}"
                    "，请手动执行 run"
                )
                append_dev_log(
                    project_dir,
                    action="run",
                    summary="自动重新部署提交失败",
                    project_id=deployed_id,
                    run_url=run_url,
                    result="failed",
                    detail=str(run_payload.get("message") or run_status),
                )
            elif getattr(args, "no_wait", False):
                info("已提交重新部署，可用 status 查看进度。")
                append_dev_log(
                    project_dir,
                    action="run",
                    summary="已提交重新部署（未等待结果）",
                    project_id=deployed_id,
                    run_url=run_url,
                    result="pending",
                )
            else:
                exit_code = _poll_deploy(args, token, base_url, deployed_id)
                append_dev_log(
                    project_dir,
                    action="run",
                    summary="自动重新部署完成" if exit_code == 0 else "自动重新部署失败",
                    project_id=deployed_id,
                    run_url=run_url,
                    result="ok" if exit_code == 0 else "failed",
                )
                return exit_code
        else:
            info("如需部署上线，请运行：python scripts/vicrocode_deploy.py run --dir .")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _project_id(args) -> tuple[str, str, dict, int]:
    token, base_url, record = resolve_config(args)
    manifest = build_manifest(args, Path(args.dir).expanduser().resolve(), record)
    project_id = manifest.get("project_id") or record.get("project_id")
    return token, base_url, record, int(project_id or 0)


def command_run(args) -> int:
    token, base_url, _record, project_id = _project_id(args)
    if not token:
        return die("缺少令牌：请先执行一次 deploy，或传入 --token vco-wc-xxx")
    if not project_id:
        return die("未找到 project_id：请先执行一次 deploy")

    # 平台的上传只写文件、不会替换运行中的进程，而 start 又是幂等的
    # （已在运行会直接返回成功），所以「部署过」就必须重启，否则可能：
    #   1. 新代码不生效（进程还在跑老代码）；
    #   2. 崩溃后残留的「已运行」记录把 start 拦住，导致救不回来。
    action = "restart" if getattr(args, "restart", False) else "run"
    state_status, state_payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/status/",
        token=token,
        method="GET",
    )
    if state_status < 400:
        state = state_payload.get("data") or {}
        deploy_status = str(state.get("deploy_status") or "")
        if state.get("healthy") or deploy_status in ("success", "failed"):
            if action != "restart":
                info(f"检测到项目已部署过（{deploy_status or 'unknown'}）：本次将重启以加载最新代码")
            action = "restart"

    status, payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/",
        token=token,
        json_body={"action": action, "max_attempts": args.max_attempts},
    )
    if status >= 400 or payload.get("status") != "ok":
        info(f"[失败] {payload.get('code') or status}: {payload.get('message')}")
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    data = payload.get("data") or {}
    info(f"部署任务已提交：状态 {data.get('deploy_status', '-')}")
    project_dir = Path(args.dir).expanduser().resolve()
    if not args.no_wait:
        exit_code = _poll_deploy(args, token, base_url, project_id)
        append_dev_log(
            project_dir,
            action="run",
            summary=f"部署{'成功' if exit_code == 0 else '失败'}",
            project_id=project_id,
            result="ok" if exit_code == 0 else "failed",
        )
        return exit_code
    append_dev_log(
        project_dir,
        action="run",
        summary=f"已提交部署（{action}），未等待结果",
        project_id=project_id,
        result="pending",
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _poll_deploy(args, token: str, base_url: str, project_id: int) -> int:
    deadline = time.time() + args.wait_seconds
    last_status = ""
    while time.time() < deadline:
        status, payload = http_call(
            base_url=base_url,
            path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/status/",
            token=token,
            method="GET",
        )
        if status >= 400:
            info(f"[失败] {payload.get('message') or status}")
            return 1
        data = payload.get("data") or {}
        current = str(data.get("deploy_status") or "")
        if current != last_status:
            info(f"部署状态：{current}")
            last_status = current
        if current in {"success", "running"} and data.get("healthy"):
            info(f"部署成功：{data.get('run_url') or ''}")
            if data.get("log_tail"):
                info("最近日志：")
                info("\n".join(str(data["log_tail"]).splitlines()[-20:]))
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if current in {"failed", "error", "timeout"}:
            info(f"[失败] {data.get('error_code') or 'DEPLOY_FAILED'}: {data.get('error_message') or ''}")
            if data.get("suggestion"):
                info(f"建议：{data['suggestion']}")
            if data.get("log_tail"):
                info("日志尾部：")
                info("\n".join(str(data["log_tail"]).splitlines()[-LOG_TAIL_LINES:]))
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        time.sleep(args.interval)
    return die(f"等待部署结果超时（{args.wait_seconds}s），可用 status 命令继续查询", 1)


def command_status(args) -> int:
    token, base_url, _record, project_id = _project_id(args)
    if not token or not project_id:
        return die("缺少令牌或 project_id：请先执行一次 deploy")
    status, payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/status/",
        token=token,
        method="GET",
    )
    if status >= 400:
        return die(payload.get("message") or f"查询失败（HTTP {status}）", 1)
    data = payload.get("data") or {}
    info(f"部署状态：{data.get('deploy_status', '-')}  健康：{data.get('healthy')}")
    if data.get("run_url"):
        info(f"网址：{data['run_url']}")
    for key in ("error_code", "error_message", "suggestion"):
        if data.get(key):
            info(f"{key}: {data[key]}")
    if data.get("log_tail"):
        info("日志尾部：")
        info("\n".join(str(data["log_tail"]).splitlines()[-LOG_TAIL_LINES:]))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_stop(args) -> int:
    token, base_url, _record, project_id = _project_id(args)
    if not token or not project_id:
        return die("缺少令牌或 project_id：请先执行一次 deploy")
    status, payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/deploy/",
        token=token,
        json_body={"action": "stop"},
    )
    if status >= 400 or payload.get("status") != "ok":
        return die(payload.get("message") or f"停止失败（HTTP {status}）", 1)
    info("已提交停止请求。")
    append_dev_log(
        Path(args.dir).expanduser().resolve(),
        action="stop",
        summary="已停止运行中的项目",
        project_id=project_id,
        result="ok",
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_metadata(args) -> int:
    token, base_url, _record, project_id = _project_id(args)
    if not token or not project_id:
        return die("缺少令牌或 project_id：请先执行一次 deploy")
    body: dict = {}
    for field in ("title", "description", "publish_status", "seo_title", "seo_description", "seo_keywords"):
        value = str(getattr(args, field, "") or "").strip()
        if value:
            body[field] = value
    tags = str(getattr(args, "tags", "") or "").strip()
    if tags:
        body["tags"] = [item.strip() for item in re.split(r"[,，]", tags) if item.strip()]
    if not body:
        return die("没有要更新的字段（可用 --title / --description / --tags / --seo-title 等）")
    status, payload = http_call(
        base_url=base_url,
        path=f"/api/agent-deploy/v1/projects/{project_id}/metadata/",
        token=token,
        method="PATCH",
        json_body=body,
    )
    if status >= 400 or payload.get("status") != "ok":
        return die(payload.get("message") or f"更新失败（HTTP {status}）", 1)
    info("项目信息已更新。")
    append_dev_log(
        Path(args.dir).expanduser().resolve(),
        action="metadata",
        summary="已更新项目信息：" + "、".join(sorted(body.keys())),
        project_id=project_id,
        result="ok",
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_log(args) -> int:
    """只往项目目录写一条开发记录（不联网、不上传）。"""
    project_dir = Path(args.dir).expanduser().resolve()
    if not project_dir.is_dir():
        return die(f"目录不存在：{project_dir}")
    summary = str(getattr(args, "summary", "") or "").strip()
    if not summary:
        return die('请用 --summary 说明这次开发/修改做了什么，例如 --summary "完成登录页改版"')
    record = load_record(project_dir)
    project_id = parse_project_id(getattr(args, "project_id", "")) or int(record.get("project_id") or 0)
    append_dev_log(
        project_dir,
        action=str(getattr(args, "action", "") or "modify").strip() or "modify",
        summary=summary,
        files=split_list(getattr(args, "files", "")),
        project_id=project_id,
        run_url=str(record.get("run_url") or ""),
        result=str(getattr(args, "result", "") or "ok").strip() or "ok",
    )
    info(f"已记录到 {RECORD_DIR}/{DEVLOG_FILE}（同时写入 {DEVLOG_JSONL}）")
    return 0


def command_sync(args) -> int:
    """改完即上传：先记录这次修改，再执行 deploy。

    有本地记录或显式 ``--id`` 时只会更新原项目，不会新建。
    """
    project_dir = Path(args.dir).expanduser().resolve()
    if not project_dir.is_dir():
        return die(f"目录不存在：{project_dir}")
    summary = str(getattr(args, "summary", "") or "").strip()
    record = load_record(project_dir)
    if summary:
        append_dev_log(
            project_dir,
            action="modify",
            summary=summary,
            files=split_list(getattr(args, "files", "")),
            project_id=parse_project_id(getattr(args, "project_id", "")) or int(record.get("project_id") or 0),
            run_url=str(record.get("run_url") or ""),
            result="ok",
        )
    else:
        info("[提示] 未提供 --summary：本次只上传，不会记录「改了什么」，建议下次补上。")
    return command_deploy(args)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target, *, with_token: bool = True, with_manifest: bool = False):
        target.add_argument("--dir", default=".", help="项目根目录（默认当前目录）")
        target.add_argument("--json", action="store_true", help="输出原始 JSON")
        target.add_argument(
            "--id",
            dest="project_id",
            default="",
            help="要升级的项目 ID：只更新这个应用，不会新建（例如 --id 1234）",
        )
        if with_token:
            target.add_argument("--token", default="", help="智能部署令牌 vco-wc-...（只首次需要）")
            target.add_argument("--site", default="", help="站点：cn / global")
            target.add_argument("--site-base", default="", help="自定义站点基址")
        if with_manifest:
            target.add_argument("--manifest", default="", help="额外 manifest JSON 文件")
            target.add_argument("--title", default="", help="项目标题")
            target.add_argument("--description", default="", help="项目描述")
            target.add_argument("--tags", default="", help="标签，逗号分隔")
            target.add_argument("--directory-name", default="", help="项目目录名")
            target.add_argument("--pageindex", default="", help="首页文件名")
            target.add_argument("--publish-status", default="", help="draft / private / approved")
            target.add_argument("--only", nargs="*", default=None, help="只上传指定相对路径")

    p = sub.add_parser("whoami", help="校验令牌")
    add_common(p)
    p.set_defaults(func=command_whoami)

    p = sub.add_parser("preflight", help="上传前预检")
    add_common(p, with_manifest=True)
    p.add_argument("--dry-run", action="store_true", help="只做本地检查，不请求平台")
    p.add_argument("--with-files", action="store_true", help="连文件一起预检（能读到页面标题）")
    p.set_defaults(func=command_preflight)

    def add_deploy_flags(target):
        target.add_argument("--force", action="store_true", help="忽略本地体积检查与内容未变化跳过")
        target.add_argument("--no-save", action="store_true", help="不写入 .vicrocode/deploy.json")
        target.add_argument("--no-wait", action="store_true", help="自动重新部署后不等待结果")
        target.add_argument("--interval", type=float, default=5.0, help="轮询间隔秒")
        target.add_argument("--wait-seconds", type=float, default=180.0, help="自动重新部署最长等待秒")

    p = sub.add_parser("deploy", help="上传或更新项目（有记录或 --id 时只更新，不新建）")
    add_common(p, with_manifest=True)
    add_deploy_flags(p)
    p.set_defaults(func=command_deploy)

    p = sub.add_parser("sync", help="改完即上传：记录这次修改并更新项目（不会新建）")
    add_common(p, with_manifest=True)
    add_deploy_flags(p)
    p.add_argument("--summary", default="", help="这次改了什么（写入项目目录的开发记录）")
    p.add_argument("--files", default="", help="本次涉及的文件，逗号分隔（写入记录）")
    p.set_defaults(func=command_sync)

    p = sub.add_parser("log", help="只往项目目录写一条开发记录（不联网）")
    add_common(p, with_token=False)
    p.add_argument("--summary", default="", help="这次开发/修改做了什么")
    p.add_argument("--files", default="", help="涉及的文件，逗号分隔")
    p.add_argument("--action", default="modify", help="记录类型：modify / develop / fix …")
    p.add_argument("--result", default="ok", help="结果标记：ok / failed / pending")
    p.set_defaults(func=command_log)

    p = sub.add_parser("run", help="部署/重启 Python 项目并等待结果")
    add_common(p)
    p.add_argument("--max-attempts", type=int, default=3, help="平台自动重试次数上限")
    p.add_argument("--interval", type=float, default=5.0, help="轮询间隔秒")
    p.add_argument("--wait-seconds", type=float, default=300.0, help="最长等待秒")
    p.add_argument("--no-wait", action="store_true", help="提交后立即返回")
    p.add_argument("--restart", action="store_true", help="强制重启（默认仅在已在线时自动重启）")
    p.set_defaults(func=command_run)

    p = sub.add_parser("status", help="查询部署状态与日志")
    add_common(p)
    p.set_defaults(func=command_status)

    p = sub.add_parser("stop", help="停止运行中的项目")
    add_common(p)
    p.set_defaults(func=command_stop)

    p = sub.add_parser("metadata", help="单独更新项目标题/描述/TDK/标签")
    add_common(p)
    p.add_argument("--seo-title", default="", dest="seo_title")
    p.add_argument("--seo-description", default="", dest="seo_description")
    p.add_argument("--seo-keywords", default="", dest="seo_keywords")
    p.set_defaults(func=command_metadata)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return die("已取消", 2)
    except RuntimeError as exc:
        return die(str(exc), 1)


if __name__ == "__main__":
    sys.exit(main())
