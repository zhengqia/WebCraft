# Agent Deploy — 智能体一键上传、更新与自动部署

Read this file whenever the user asks to upload / update / deploy a finished project to
VicroCode (e.g. 「上传到 VicroCode」「更新到 VicroCode」「部署」).

The agent path replaces the manual browser flow of `/project-upload-website` and
`/project-edit-website` with one CLI script. The platform runs the **same server-side
rules** for both, so nothing is skipped.

---

## 1. Prerequisite: the 智能部署 token

The script authenticates with a special token (`vco-wc-...`) instead of a browser login.

- Create it once: `我的令牌 → 智能部署`（国内站 `https://www.vicoco.cn/user-center/my-tokens?tab=api-keys&create=deploy`；国际站对应 `https://www.vicrocode.com/user-center/my-tokens?tab=api-keys&create=deploy`）。
- The token prefix is `vco-wc-`. It only works for `/api/agent-deploy/v1/*` and only for the token owner's own projects.
- The token may be bound to an IP allowlist or an expiry; either will make requests fail with a clear error code.
- First run: pass `--token vco-wc-...` once. The script stores it in `.vicrocode/deploy.json` and reuses it afterwards.

---

## 2. The record file (`.vicrocode/deploy.json`)

The script keeps a local record in the project root so later runs are automatic:

```json
{
  "schema": "vicrocode.agent-deploy.v1",
  "site": "cn",
  "site_base": "https://www.vicoco.cn",
  "token": "vco-wc-...",
  "project_id": 1234,
  "directory_name": "my-tool",
  "run_url": "https://www.vicoco.cn/p/1234/",
  "project_kind": "static",
  "last_upload_at": "2026-09-24T12:00:00+08:00",
  "last_package_hash": "sha256:...",
  "auto_deploy": false,
  "history": []
}
```

Rules:
- This file holds a token, so it is **local only**. Never upload it, commit it, or copy its contents into any file that ships.
- The same folder keeps the project-local dev log: `.vicrocode/dev-log.md` (human readable) and `.vicrocode/dev-log.jsonl` (one JSON object per line). Every develop / modify / upload / run / stop / metadata action appends an entry, so the project carries its own history of what changed and when it was uploaded. It is local-only as well.
- Add `.vicrocode/` to `.gitignore`; the script reminds the user when a `.git` directory or `.gitignore` is present.
- The platform also strips `.vicrocode/` on ingest, in clone snapshots, in source packages, and in source delivery — this is a safety net, not an excuse to ship it.

---

## 3. Commands

Run from the project directory (or pass `--dir <path>`).

| Command | Purpose |
|---|---|
| `whoami` | Validate the token and show the bound account and quota. |
| `preflight` | Detect project type, entry file, dynamic data, sensitive files, and size problems before uploading. Add `--with-files` to also read the page `<title>`/`<meta>`; add `--dry-run` for a local-only scan. |
| `deploy` | Create or update the project. With `--id <project id>` (or an existing record) it only updates that app and never creates a new one. Auto-fills title/description/tags/TDK. Prints the run URL. Idempotent; skips when content is unchanged (`--force` to re-upload). |
| `sync` | Finish a develop / modify pass: record the change locally and upload it in one step (`--summary`, `--files`). |
| `screenshot` | Capture desktop / tablet / mobile screenshots of the local project (or of a live URL with `--url`). |
| `log` | Append a develop / modify entry to the project-local dev log without touching the platform. |
| `run` | Start/restart the Python app and poll until success or failure (`--no-wait` to submit and return). |
| `status` | Query deploy status, health, and log tail. |
| `stop` | Stop the running app. |
| `metadata` | Update title/description/tags/TDK/publish status without touching files. |

Common flags: `--dir`, `--site cn|global`, `--site-base https://...`, `--token vco-wc-...`,
`--id 1234`, `--manifest manifest.json`, `--title`, `--description`, `--tags a,b`,
`--directory-name`, `--publish-status draft|private|approved`, `--json`.

Screenshot flags: `--no-screenshot` (skip), `--screenshots a.png,b.png` (use your own images),
`--browser <path to chrome/msedge>` (when auto-detection fails).

`--id` is the explicit upgrade switch: pass the project ID (for example `--id 1234`) and the
upload only updates that app — a new project is never created. The ID is remembered in
`.vicrocode/deploy.json`, so later runs keep updating the same app automatically.

Token resolution order: `--token` → `VICROCODE_DEPLOY_TOKEN` env → record file.
Site resolution order: `--site` → `VICROCODE_SITE` → record file → `cn`.

---

## 4. Manifest shape

`--manifest` accepts a JSON object. Everything is optional; the script auto-fills the rest.

```json
{
  "schema": "vicrocode.agent-deploy.v1",
  "directory_name": "my-tool",
  "project_id": 1234,
  "title": "AI 图片去水印工具",
  "description": "上传图片一键去水印，支持批量处理与下载。",
  "tags": ["图片处理", "AI工具"],
  "seo_title": "AI 图片去水印在线工具 - 免费批量处理",
  "seo_description": "上传图片即可自动去除水印，支持 JPG/PNG。",
  "seo_keywords": "去水印,图片处理,在线工具",
  "display_options": ["online", "download"],
  "proclass": "website",
  "publish_status": "draft",
  "primary_locale": "zh-CN",
  "dynamic_data_paths": ["data/"],
  "pageindex": "index.html",
  "python": { "entry_file": "app.py", "framework": "flask", "auto_deploy": true }
}
```

- `directory_name`: `^[a-zA-Z0-9_-]+$`; invalid characters are auto-slugified. Unique per author.
- `project_id` vs `directory_name`: give either to target an existing project; the script prefers the record file's values, so later runs update instead of re-create.
- `dynamic_data_paths` is auto-merged from `vicrocode.project.json`'s `runtime_data`.
- `publish_status` default is `draft` for new projects. **Updating files on a draft project auto-promotes it to `private`** (platform rule), and the script reports a warning.
- TDK/description/tags default to the page `<title>`/`<meta>` when the agent did not provide them.

---

## 5. Error codes → actions

The platform returns a stable `code` on failures. Map them to concrete fixes:

| code | Meaning | What to do |
|---|---|---|
| `TOKEN_INVALID` | token missing/revoked/expired | Ask the user to recreate the 智能部署 token. |
| `TOKEN_IP_DENIED` | IP not in the token allowlist | Ask the user to adjust the token IP allowlist. |
| `TOKEN_QUOTA_EXCEEDED` | daily limit reached | Wait or raise the token limit. |
| `DIRECTORY_NAME_INVALID` | name not `^[a-zA-Z0-9_-]+$` | The script already slugifies; if it persists, set `--directory-name` explicitly. |
| `DIRECTORY_NAME_TAKEN` | same author already has that name (not this token) | Choose a new `directory_name`. |
| `NO_ONLINE_FILES` | nothing uploadable | Verify `online_files`/paths; check nothing was filtered as sensitive. |
| `ENTRY_FILE_MISSING` | no `index.html` at root for a static project | Put the entry page at the project root or set `pageindex`. |
| `PROJECT_QUOTA_EXCEEDED` | user project/storage quota | Tell the user to free space. |
| `PYTHON_DEPS_FAILED` / `PYTHON_DEPS_RETRY` | dependency install failed | Fix `requirements.txt` and re-run `deploy` + `run`. |
| `PYTHON_START_FAILED` / `PYTHON_HEALTH_TIMEOUT` | process didn't start or port not healthy | Read the returned log tail, fix code, re-run. |

---

## 6. Python auto-deploy

- `run` posts `{"action":"run"}` and polls `deploy/status/`. The platform:
  1. installs dependencies (three mirrors + wheel fallback), assigns a port, starts the process;
  2. health-checks the port (TCP connect + HTTP response);
  3. auto-retries **transient** failures (network, mirror timeouts, port conflicts) up to `max_attempts` (default 3, backoff 5/15/30s);
  4. for **deterministic** failures (missing module, syntax error, missing entry), it stops retrying and returns a structured `error_code` + `suggestion` + the log tail so the agent fixes the code.
- `deploy/status/` returns `deploy_status` (`idle`/`running`/`success`/`failed`), `healthy`, `run_url`, `log_tail`, `attempts`, and, on failure, `error_code`/`error_message`/`suggestion`.
- Log tails are masked (tokens/secrets redacted) and capped at the last 100 lines / 16 KB.

---

## 7. Returned URL

- `run_url` is the user-facing page: `https://www.vicoco.cn/p/{id}/` (CN) or `https://www.vicrocode.com/p/{id}/` (global).
- `proxy_url` is the direct runtime proxy for Python projects (`/api/python-proxy/{id}/`) and is meant for programmatic checks, not for handing to users.

---

## 8. Safety checklist before deploy

1. `preflight` reports no blocking `issues`.
2. `vicrocode.project.json` declares every runtime data path (or `runtime_data: []`).
3. Every declared data file is an empty template (no real records).
4. No `.env`, private keys, `.git/`, `node_modules/`, or `.vicrocode/` would be uploaded (the script filters them and reports what it skipped).
5. The `vco-wc-` token was never written into project source or logs.

---

## 9. Upgrading an existing app (never create a duplicate)

Three ways to target an existing project, in priority order:

1. `--id <project id>` — the user says "升级应用 1234" or gives an ID. The upload becomes a
   strict update of that project (`--id` overrides the record file) and a new project is never
   created. If the ID does not belong to the token owner, the platform answers
   `PROJECT_NOT_FOUND` and the script tells the user to check the ID.
2. The record file `.vicrocode/deploy.json` — it already stores `project_id` from the first
   successful upload, so plain `deploy` / `sync` keeps updating the same app.
3. `directory_name` — used only when there is no ID and no record; if that name is free, a new
   project is created.

When neither a record nor an ID exists and the user wants an existing project updated, ask for
the project ID before uploading.

```bash
# upgrade app #1234 with the current folder contents
python scripts/vicrocode_deploy.py sync --dir . --id 1234 --summary "修复手机端布局" --files index.html,style.css

# same, upload only (no local change entry)
python scripts/vicrocode_deploy.py deploy --dir . --id 1234
```

---

## 10. Project-local dev log

The script appends one entry per action to `<project>/.vicrocode/dev-log.md`:

```markdown
## 2026-09-27 21:05:11+0800 — modify [ok]
- 说明：修复手机端布局
- 项目：#1234  https://www.vicoco.cn/p/1234/
- 涉及文件（2）：index.html、style.css
```

- Written automatically by `sync` (action `modify` + `upload`), `deploy` (`upload`, also
  `skipped` / `failed`), `run` (`run`), `stop` and `metadata`.
- Add an entry by hand when you changed something outside the deploy flow:

```bash
python scripts/vicrocode_deploy.py log --dir . --summary "重写导出逻辑" --files app.py
```

- The same data is appended to `.vicrocode/dev-log.jsonl` for scripts.
- Both files stay local: never upload, commit, or deliver them, and keep `.vicrocode/` in
  `.gitignore`.

---

## 11. Automatic metadata and screenshots

Upload is self-filling: never ask the user to type the project name, description, TDK, tags or
screenshots by hand.

**Metadata** (`title`, `description`, `tags`, `seo_title`, `seo_description`, `seo_keywords`) is
resolved in this order:

1. explicit value from the manifest file or a CLI flag (`--title`, `--description`, `--tags`);
2. the page itself: `<title>`, `<meta name="description">`, `<meta name="keywords">`, `<h1>`,
   and the visible body text;
3. a local fallback (directory name, first meaningful sentence, derived keyword phrases).

Limits match the platform: title ≤ 100, description ≤ 300, keywords ≤ 200, at most 5 tags.
`preflight --dry-run` prints every generated field, so review the copy before uploading; put
anything you want to change into `vicrocode.project.json` / `--manifest`.

**Screenshots** are generated by the same `deploy` / `sync` run:

- three viewports: desktop `1440x900`, tablet `1024x768`, mobile `390x844`;
- captured with the local Chrome or Edge (auto-detected; use `--browser <path>` or the
  `VICROCODE_BROWSER` environment variable when detection fails);
- the page is served from a temporary local HTTP server first, so same-origin relative paths
  behave like production;
- images are cached in `.vicrocode/screenshots/` (local only, never uploaded as project source)
  and reused while the source is unchanged — `--force` re-captures them;
- `--no-screenshot` skips them, `--screenshots a.png,b.png` uploads your own images instead;
- `screenshot --dir .` captures on demand, and
  `screenshot --dir . --url https://www.vicoco.cn/p/1234/` captures a deployed page (handy after
  the first upload and for Python projects);
- the platform keeps up to 5 screenshots and uses the first one as the cover image.

Before shipping a change to this skill itself, run `python scripts/selftest.py --with-browser`.
It verifies the package shape, version consistency, script syntax, secret scan, and the
metadata / screenshot pipeline.
