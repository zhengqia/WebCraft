#!/usr/bin/env python3
"""WebCraft 技能自检：发版前跑一遍，确认包结构、版本号、脚本语法与自动生成能力都正常。

用法::

    python scripts/selftest.py                  # 结构 / 版本 / 语法 / 元数据推导 / 令牌扫描
    python scripts/selftest.py --with-browser   # 额外真实截图一次（需要本机有 Chrome/Edge）

退出码：0 全部通过；1 存在失败项。
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
DEPLOY_SCRIPT = SCRIPTS_DIR / "vicrocode_deploy.py"
REQUIRED_SUBCOMMANDS = (
    "whoami", "preflight", "deploy", "sync", "screenshot", "log", "run", "status", "stop", "metadata",
)
SECRET_TOKEN_RE = re.compile(r"vco-(?:wc|api|know|data)-[A-Za-z0-9._-]{20,}")
SOURCE_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".txt"}

results: list[tuple[str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results.append((status, f"{name}{(' - ' + detail) if detail else ''}"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    record("PASS" if ok else "FAIL", name, detail)
    return ok


def warn(name: str, ok: bool, detail: str = "") -> bool:
    record("PASS" if ok else "WARN", name, detail)
    return ok


def check_structure() -> None:
    skill_md = SKILL_DIR / "SKILL.md"
    if not check("SKILL.md 存在", skill_md.is_file()):
        return
    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    check("SKILL.md 有 YAML frontmatter", text.startswith("---") and "name:" in text[:400] and "description:" in text[:1200])
    check("SKILL.md 行数不超过 500", len(text.splitlines()) <= 500, f"{len(text.splitlines())} 行")
    linked = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", text))
    existing = {path.name for path in REFERENCES_DIR.glob("*.md")}
    check("SKILL.md 引用的 references 都存在", not (linked - existing), "、".join(sorted(linked - existing)))
    check("references 都被 SKILL.md 引用", not (existing - linked), "、".join(sorted(existing - linked)))
    check("存在 agents/openai.yaml", (SKILL_DIR / "agents" / "openai.yaml").is_file())
    check("存在部署脚本", DEPLOY_SCRIPT.is_file())


def check_versions() -> None:
    version_path = SKILL_DIR / "VERSION"
    if not check("VERSION 存在", version_path.is_file()):
        return
    version = version_path.read_text(encoding="utf-8").strip()
    try:
        marketplace = json.loads((SKILL_DIR / "marketplace.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        check("marketplace.json 可解析", False, str(exc))
        return
    check(
        "marketplace.json 版本与 VERSION 一致",
        marketplace.get("version") == version,
        f"VERSION={version} marketplace={marketplace.get('version')}",
    )
    selection = (REFERENCES_DIR / "version-and-site-selection.md").read_text(encoding="utf-8", errors="ignore")
    tail = selection.split("Current local skill version", 1)[-1][:200]
    match = re.search(r"```text\s*\n\s*(\S+)", tail)
    check(
        "version-and-site-selection.md 本地版本一致",
        bool(match) and match.group(1).strip() == version,
        match.group(1).strip() if match else "未找到版本号",
    )
    readme = (SKILL_DIR / "README.md").read_text(encoding="utf-8", errors="ignore")
    check("README 提到当前版本", version in readme, version)


def check_scripts() -> None:
    for script in sorted(SCRIPTS_DIR.glob("*.py")):
        completed = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True,
        )
        detail = (completed.stderr or b"").decode("utf-8", errors="replace").strip()[:160]
        check(f"{script.name} 语法检查", completed.returncode == 0, detail)
    completed = subprocess.run(
        [sys.executable, str(DEPLOY_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    help_text = f"{completed.stdout or ''}{completed.stderr or ''}"
    missing = [name for name in REQUIRED_SUBCOMMANDS if name not in help_text]
    check("部署脚本子命令齐全", not missing, "、".join(missing))


def check_secrets() -> None:
    hits: list[str] = []
    for path in SKILL_DIR.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in SECRET_TOKEN_RE.finditer(content):
            hits.append(f"{path.relative_to(SKILL_DIR)}:{match.group(0)[:16]}...")
    check("包内没有真实令牌", not hits, "；".join(hits[:3]))


def check_metadata_generation() -> Path:
    sys.path.insert(0, str(SCRIPTS_DIR))
    import vicrocode_deploy as vd  # noqa: WPS433 - 同目录脚本，运行时导入

    workdir = Path(tempfile.mkdtemp(prefix="webcraft-selftest-"))
    (workdir / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>发票报销助手 - 拖拽生成报销清单</title>"
        "<meta name='description' content='把电子发票拖进来，自动识别金额与抬头，一键生成报销清单。'>"
        "</head><body><h1>发票报销助手</h1>"
        "<p>支持 PDF 与图片格式，适合财务与出差报销场景。</p></body></html>",
        encoding="utf-8",
    )
    meta = vd.derive_project_metadata(workdir, {})
    check("兜底推导项目名", bool(meta.get("title")), str(meta.get("title", "")))
    check("兜底推导描述", bool(meta.get("description")), str(meta.get("description", ""))[:60])
    tags = meta.get("tags") or []
    check("兜底推导标签（1-5 个）", 1 <= len(tags) <= 5, "、".join(tags))
    check(
        "兜底推导 TDK",
        all(meta.get(key) for key in ("seo_title", "seo_description", "seo_keywords")),
    )
    explicit = vd.derive_project_metadata(workdir, {"title": "自定义标题", "tags": ["报销", "财务"]})
    check(
        "manifest 显式值优先",
        explicit.get("title") == "自定义标题" and explicit.get("tags") == ["报销", "财务"],
    )
    check(
        "缺失元数据能被检出",
        vd._missing_agent_metadata({}) == list(vd.AGENT_METADATA_FIELDS),
    )
    check(
        "元数据齐全时不报缺项",
        vd._missing_agent_metadata(vd.derive_project_metadata(workdir, {})) == [],
    )
    browser = vd.find_browser()
    warn("检测到 Chrome / Edge（自动截图用）", bool(browser), browser or "未找到，上传时会跳过截图")
    return workdir


def main() -> int:
    parser = argparse.ArgumentParser(description="WebCraft skill self test")
    parser.add_argument("--with-browser", action="store_true", help="额外真实截图一次")
    args = parser.parse_args()

    check_structure()
    check_versions()
    check_scripts()
    check_secrets()
    workdir = check_metadata_generation()

    if args.with_browser:
        sys.path.insert(0, str(SCRIPTS_DIR))
        import vicrocode_deploy as vd  # noqa: WPS433

        shots, note = vd.generate_screenshots(workdir, {"pageindex": "index.html"}, force=True)
        check("真实截图生成", bool(shots), note)
        for shot in shots:
            check(f"截图文件非空：{shot.name}", shot.is_file() and shot.stat().st_size >= 1024)
    else:
        record("SKIP", "真实截图测试（加 --with-browser 才会跑）")

    shutil.rmtree(workdir, ignore_errors=True)
    for cache in SCRIPTS_DIR.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    print("WebCraft 技能自检")
    print("=" * 60)
    failed = 0
    warned = 0
    for status, message in results:
        if status == "FAIL":
            failed += 1
        elif status == "WARN":
            warned += 1
        print(f"[{status}] {message}")
    print("=" * 60)
    print(f"共 {len(results)} 项：通过 {len(results) - failed - warned}，警告 {warned}，失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
