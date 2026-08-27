# Knowledge Base, Database, and Backend Resource Management

Use this reference when a VicroCode project needs a managed knowledge base, a SQLite database, or the account-level backend resource managers. These modules are platform resources, not ordinary files inside a website project.

## 1. Resource boundaries

- Keep website source in the uploaded project package (`pro/`) and runtime state in the platform-managed `runtime/` directory.
- A LanceDB knowledge base and a SQLite database must have stable resource identifiers. Do not use display names as identifiers.
- The account quota covers databases, knowledge bases, files, SKILL assets, and API-tool assets together. Show account usage separately from each project’s usage; do not present a project usage number as a project quota.
- File capacity is accounted for at account level. Include files produced by SKILL and API-tool execution in the account total and attribute them to the originating project when possible.
- Admin resource moderation is part of the contract: deleting or blocking a resource must be auditable. A blocked knowledge base or database must reject API calls with a structured `403` response, expose the block reason to its owner, and support an owner appeal plus an administrator approve/reject decision with a reason.

## 2. LanceDB knowledge bases

### Supported ingestion

Provide a clear upload result for every file. At minimum, plan handlers for:

- PDF and DOC/DOCX text extraction, preserving embedded images as knowledge-base assets;
- XLS/XLSX/CSV parsing into readable Markdown tables (retain sheet names, headers, and row boundaries);
- Markdown, TXT, HTML, JSON, and common structured text formats;
- images such as JPG, PNG, WEBP, and GIF;
- web pages through the platform crawler.

Never report “OCR component missing” as the only explanation. Image uploads must offer two explicit modes:

1. **AI image description** — run image understanding and store the resulting description as searchable text, with the original image retained when the user allows it.
2. **Original image + text mark** — store the original image and any user-supplied label/alt text without requiring OCR.

OCR is an optional enhancement for text visible in an image, not the universal parser for PDF, DOCX, or spreadsheets. Select a parser by MIME type and return a JSON error naming the missing parser, file type, and recovery action.

### Segmentation and indexing

- Do not assign a “default free segmentation policy” when creating a base. Let the user choose a segmentation policy during upload or re-processing.
- Support manual segmentation, rule-based segmentation, and **AI automatic segmentation**. AI segmentation costs 50 coins per successful operation; charge only after segments are produced and persisted. The user must see the cost before confirmation.
- After an edit, require an explicit “confirm update knowledge base” action before the new segment becomes searchable. If the user leaves with unsaved edits, show an in-page warning overlay.
- Rebuild LanceDB indexes automatically after a confirmed upload, edit, re-upload, delete, or segmentation change. Do not expose “rebuild index” as a confusing routine user action; surface status such as `processing`, `ready`, or `failed` instead.
- Persist source metadata, parser/segmentation strategy, checksum, extraction warnings, and index version so a failed rebuild can be retried safely and diagnosed.
- Keep source images and embedded document images linked to the source record and available from the visual file-management page.

### Web crawling

1. Normalize and validate the URL, follow redirects safely, enforce size/time limits, and sanitize extracted HTML.
2. Try the internal crawler library first. Store successful crawler scripts and their metadata in the platform crawler library for future matching.
3. If the library cannot extract useful content, show a confirmation overlay before offering an AI-generated crawler. The optional hint field should explain: “If you know the site’s technical details, add them here so AI can try a more targeted approach.”
4. The AI crawler attempt costs 200 coins per attempt, including failed script-generation attempts as explicitly requested by the product. Try at most five Python crawler scripts for one user request, record each attempt, and never execute unreviewed code outside the restricted crawler workspace.
5. Sanitize the result, show the user whether content was found, and only charge a normal content-processing fee after a successful extraction. Never silently swallow crawler errors or return mojibake caused by an incorrect response encoding.

## 3. Knowledge-base API and AI answers

- API tokens are created and revoked only from `my-tokens`; do not create ad-hoc secrets in a resource page.
- Support JSON retrieval and optional AI-answer modes through an explicit request parameter (for example, `answer_mode: "json" | "ai"`). AI answers are off by default and require the owner to enable the setting.
- Expose the retrieval strategy as a request parameter. Supported strategies may include keyword, semantic/vector, hybrid, and reranked hybrid search; document the defaults and top-k limits in the API schema.
- Open-scope choices are: specified Agent/API tools, specified site accounts, or public. Public means other callers may use the endpoint, but a valid token is still required.
- Provide an API-call method panel showing input/output parameters, a copyable integration prompt, and a test panel with both a readable result preview and a raw JSON result tab. Errors must appear above overlays or inside the active overlay with a visible role/status region.
- AI answer configuration should keep model-center credential selection separate from the prompt template. Default models can be offered, but only recently used/available model credentials should appear in the selector. Never ship a provider key in source code.
- AI prompt optimization is a distinct 10-coin action using the platform-managed model key; charge after a successful optimized prompt is returned.

## 4. SQLite databases

- Independent databases and Agent-embedded databases share the same browse, table, row, upload, backup, restore, and delete capabilities. Independent databases may add API access and open-scope controls; do not fork the core management experience.
- Require case-insensitive duplicate-name validation within the owner’s scope. Return a structured `409` error such as `DATABASE_NAME_DUPLICATE` and ask the user to rename the database.
- Use platform runtime paths (`runtime/*.db`) rather than source-adjacent paths. Enable a connection timeout and `PRAGMA busy_timeout`; keep transactions short and retry transient lock conflicts.
- Preserve WAL/SHM behavior and never copy a live WAL database as if it were a consistent backup. Flush/checkpoint or use SQLite’s backup API, then verify the backup before exposing a download.
- API-created databases must use a token created from `my-tokens` and must enforce the same owner/project scope and moderation block checks as the UI.
- Project selection must let the owner inspect databases uploaded by that project and databases added from the manager. Always show the bound project name next to a database title.

## 5. Manager UI and mobile behavior

- The four managers (knowledge base, database, file, and Python) open as independent manager pages with their own resource list; they do not inherit the personal-center sidebar.
- The first account-level dashboard summarizes all backend resources and total quota usage. Project-data remains a separate project page and may consume the same metrics, but it is not the admin resource dashboard.
- Keep manager page backgrounds, cards, controls, overlays, and side navigation readable in both light and dark themes. Set foreground colors explicitly on every dark surface and control.
- Remove duplicate “quick actions” and repeated module titles from content cards; place cross-manager shortcuts in the manager sidebar only.
- On narrow screens, collapse the resource list and dashboard cards without hiding create, save, cancel, upload, or close controls. File uploads are serialized, show progress, and return JSON on both success and failure.

## 6. Acceptance checklist

- [ ] MIME-specific parser selected; image mode is explicit; embedded document images are retained.
- [ ] Excel/CSV output is readable Markdown and preserves sheets/headers.
- [ ] Manual and AI segmentation are visible, confirmed before indexing, and charged only after success.
- [ ] Index status is automatic and recoverable; no confusing routine rebuild button.
- [ ] Crawler library is tried before AI; AI crawler confirmation, 200-coin attempt billing, five-attempt limit, and audit trail are present.
- [ ] Retrieval API supports JSON/AI modes, strategy parameter, token scope, test preview, raw JSON, and integration prompt.
- [ ] SQLite duplicate names, runtime path, WAL-safe backup, lock handling, project scope, and API token checks are covered.
- [ ] Account quota includes all resource classes and project attribution is visible.
- [ ] Admin block/appeal workflow returns structured API errors and owner-visible reasons.
- [ ] Light/dark themes, overlays, keyboard access, and mobile layouts are tested.
