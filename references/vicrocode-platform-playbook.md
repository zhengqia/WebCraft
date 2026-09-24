# VicroCode Platform Playbook

Use this guide when a developer is unfamiliar with VicroCode and needs a complete, safe path from idea to a published project. It documents public product contracts only; never add credentials, private infrastructure, unreleased behavior, or security-sensitive details to a project or skill.

## 1. Choose the project surface

| Need | Start here | What the project owns |
| --- | --- | --- |
| Static HTML/React/Vite website | WebCraft website project | UI and same-origin API calls |
| Python business logic | Python project + `/api/python-proxy/{projectId}/` | Python handlers and runtime files |
| Reusable HTTP function | API Endpoint Hosting | `handler(payload, context)` and JSON schema; no Flask server |
| Searchable documents | Knowledge Base manager | ingestion, segmentation, retrieval and access scope |
| Structured records | Database manager | SQLite tables, rows, backup and API scope |
| User files | File manager | uploads, metadata, previews and account quota |

For an existing app, audit its route, API calls, persistence and upload assumptions before changing the design. Keep a small, compatible patch when possible.

## 2. Beginner setup map

1. Create or open the project in the project workspace.
2. Decide whether the public site serves Simplified Chinese, Traditional Chinese, English, or a declared combination. Keep copy and SEO metadata in `locales/zh-CN.json`, `locales/zh-Hant.json`, and/or `locales/en.json`.
3. Use the platform's warm Aether baseline by default: `#fafbf8` page surface, `#f5f6f3` containers, `#111111` text on light surfaces, explicit light text on dark surfaces, restrained borders, and accessible 14px+ body text.
4. For Python, choose only `3.9`, `3.10`, or `3.11`; use `3.10` when no requirement is given.
5. Put source in the upload package and write mutable data to platform-managed `runtime/` and `runtime/storage/`. Do not ship a fake project-root `runtime/` folder.
6. Test the real route, refresh behavior, empty/error states, mobile layout, and iframe behavior before upload.

## 3. Managed resources

### Knowledge bases

- Create a stable resource identifier; do not use a display name as an ID.
- Pick a parser by MIME type (PDF/DOCX, spreadsheet, Markdown/TXT/HTML/JSON, image, or web page). Image ingestion must let the user choose AI description or original image plus alt text; OCR is optional.
- Let the user choose manual, rule-based, or AI segmentation. Show the cost before an AI operation and charge only after segments are persisted.
- After upload/edit/reprocess/delete, rebuild the index automatically and expose `processing`, `ready`, or `failed` status with a retry path.
- For web pages, normalize the URL, enforce size/time limits, sanitize HTML, try the crawler library first, and show an in-page confirmation before an optional AI crawler.
- Retrieval APIs require a token created in the token center, an explicit scope, strategy (`keyword`, `semantic`, `hybrid`, or reranked hybrid), top-k limit, and `answer_mode` (`json` by default or explicitly enabled `ai`).

### Databases

- Independent and project-bound databases use the same browse/table/row/upload/backup/restore/delete experience. Show the bound project next to the database name.
- Reject case-insensitive duplicate names with a structured `409` error. Keep databases under `runtime/*.db`, set a timeout and `PRAGMA busy_timeout`, and keep transactions short.
- Create consistent backups with SQLite backup/checkpoint APIs; never copy a live WAL file as a complete backup.
- Database APIs use token scope and the same moderation/ownership checks as the UI.

### Backend resources and files

- Knowledge bases, databases, files and Python projects have separate manager pages and account-level quota accounting.
- File uploads show progress, serialize requests, lock related controls while uploading/clearing, and return JSON on success and failure.
- Reconcile metadata rows with runtime files after upload or restore. Never rely on stale `localStorage` previews.
- Administrative block/delete/appeal actions need an auditable record and a visible reason; use webpage overlays for confirmation.

## 4. Python projects and APIs

- Browser requests to Python use same-origin `/api/python-proxy/{projectId}/...`; do not make `/api/proxy-project-by-id/...` the default.
- Resolve runtime paths from the runner environment. Treat `__file__` as source/pro context, not as the runtime root.
- For long model, media, crawler or file jobs, send `X-Vicro-Long-Timeout: 1` or `__vicro_long_timeout=1`, or use an async start/status/result flow.
- Hosted API projects use the separate API Endpoint Hosting contract: root workspace files, `handler(payload, context)`, declared JSON input/output schemas, restricted dependencies, and review before publish.
- Website projects that call authenticated third-party APIs use `__vicro_proxy__/{identifier}/{upstreamPath}` or injected Python proxy environment variables. Never put a provider key or original project ID in browser code.

## 5. Model Center integration

Collect provider, protocol family, base URL, model, capability and credential source before coding. Route by the real protocol (OpenAI-compatible, Anthropic, Gemini, or provider-specific). Keep model credentials in the platform credential flow; do not expose keys in prompts, source, logs or client bundles. Separate model usage billing from project access/download coins and settle any coin charge only after a successful result.

## 6. Upload, publish and clone

1. Run route, persistence, secret-scan and API-connectivity checks locally.
2. Upload through `/project-upload-website`.
3. Manage domains, visibility, locales and runtime settings in `/project-manage`.
4. For clone-ready projects, create stable hosted API identifiers in Credential Vault, replace direct provider calls, remove `.env`/private keys, run the clone secret scan, then pass the source-rule and API-connectivity checks before clone review.
5. Keep public links same-origin and generate canonical, hreflang, sitemap, title, description, structured data and readable fallback HTML for each published locale.

## 7. Acceptance checklist

- Route works at `/p/{id}` (and the Python proxy route when applicable) after refresh and inside an iframe.
- Runtime files and SQLite are under platform-managed runtime paths.
- Resource managers show ownership, quota, status, errors and mobile-safe controls.
- All uploads and destructive actions have progress/confirmation overlays and structured JSON responses.
- Model calls use the selected protocol and hosted credentials without secrets in source.
- Public pages have locale files, internal links, canonical/hreflang metadata, sitemap entries and no accidental third-party links.
- Upload/publish/clone checks pass, and monetized actions charge only after success.
