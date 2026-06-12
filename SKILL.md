---
name: webcraft
description: VicroCode-specific web application development skill for building, repairing, and packaging web apps that fit VicroCode runtime, design baseline, upload/publish flow, /p/{id}, /api/python-proxy/{id}/, storage, iframe readiness, monetization, and AI integration expectations. Use when Codex is asked to develop a WebCraft/VicroCode-ready HTML/JS/React/Vite/Flask/Python/SQLite app or adapt an existing app for VicroCode.
---

# WebCraft

Build VicroCode-aligned website applications without treating the SDK as the default architecture.

## Start Here

Before doing any implementation work:

1. Read [references/version-and-site-selection.md](references/version-and-site-selection.md).
   If network access is available, run `scripts/check_and_install_update.py` first to compare the local version with the remote package.
2. Read [references/vicrocode-rules.md](references/vicrocode-rules.md).
3. If the task needs AI or model capability, also read [references/ai-model-integration.md](references/ai-model-integration.md).
4. If the task needs pricing, monetization, or upload/publish guidance, also read [references/pricing-and-publish.md](references/pricing-and-publish.md).
5. Use [references/dialogue-template.md](references/dialogue-template.md) as the default conversation pattern when required information is still missing.

## Idea Discovery

When the user wants to build something but does not know what to build yet, do not jump into implementation. Help them convert a vague idea into an input-to-output workflow first.

Ask or propose around these points:

- Who will use it and in what situation.
- What the user will input: text, images, files, URLs, forms, API data, or uploaded media.
- What the app should process or decide.
- What the app should output: a page, report, generated image/video/audio, downloadable file, database record, or API response.
- What a successful first version looks like.
- What can be deferred from the minimum viable version.

If the user is still unsure, give 3-5 concrete app directions in `input -> output` form, then ask them to pick or combine one. Example:

- `topic + target audience -> short video script + shot list`
- `uploaded photos -> style-consistent gallery + downloadable ZIP`
- `product description -> landing page copy + SEO title + publish-ready HTML`
- `CSV file -> charts + summary report + export`

## Workflow

1. Detect or ask for the target site flavor first:
   - Chinese / domestic site
   - English / global site
2. Detect whether this is:
   - a brand-new website app
   - an existing website app that needs modification, repair, or migration
3. If it is an existing app, audit before redesign:
   - current routes and entry points
   - current backend shape
   - current storage and SQLite paths
   - current AI integration points
   - current publish/deploy assumptions
   - current breakage symptoms
4. Classify the project:
   - static frontend
   - frontend + Python/Flask
   - frontend + Python + SQLite
   - generation/media workflow
5. If the app includes Python:
   - confirm whether the project should run on `3.9`, `3.10`, or `3.11`
   - default to `3.10` when the user has no hard requirement
   - do not silently design around `3.12+` because it is outside the platform's default supported range
6. Fix pathing and persistence before UI polish:
   - entry route
   - same-origin platform API
   - `python-proxy` routing
   - platform-managed `runtime/storage` and `runtime/*.db`
   - refresh persistence and sync safety
7. Prefer no-SDK implementation for new apps.
8. If the app is an existing project, prefer minimal-compatible changes over unnecessary rewrites.
9. If the app needs AI capability:
   - collect the provider, base URL, endpoint, auth method, model, and capability type first
   - route calls by the provider's real protocol family and endpoint type
   - do not push any platform-managed model API by default
10. If the app needs monetization:
   - distinguish project access/download coin pricing from model API billing
   - explain which actions should charge coins and why
   - make coin deduction happen only after the charged action succeeds
   - if the action fails, do not deduct coins and do not design silent pre-charge behavior
   - propose pricing in coins with clear rationale
11. If the app is meant to be published on VicroCode:
   - guide the user to `/project-upload-website`
   - then direct them to `/project-manage` for post-upload management
12. End with a concrete acceptance check:
   - route correctness
   - refresh survival
   - runtime file placement
   - upload/publish destination
   - language package and locale switching behavior when the app is public-facing
   - AI/model provider config handling
   - monetization or charging logic when relevant

## Multilingual Project Standard

For public-facing VicroCode tools, guide developers to support the platform language context instead of relying on the platform to translate tool internals at runtime.

Recommended source shape:

```text
locales/
  zh-CN.json
  zh-Hant.json
  en.json
```

Frontend tools should read the runtime language from the parent/platform context:

```js
const locale = window.VICRO_LOCALE || new URLSearchParams(location.search).get("vicro_locale") || "en";
```

Python-backed tools should read the same intent from environment or request/query context when available:

```python
locale = os.environ.get("VICRO_LOCALE") or request.args.get("vicro_locale") or "en"
```

When building or repairing a public tool:

1. Ask the user which app languages to support before implementation unless they already specified it: Simplified Chinese (`zh-CN`), Traditional Chinese (`zh-Hant`), English (`en`), or any combination of those three.
2. Create a `locales/` directory with one JSON file per selected language, named exactly `zh-CN.json`, `zh-Hant.json`, and/or `en.json`; do not create files for unsupported languages.
3. Keep user-facing UI copy in those language files or a clear translation map instead of hardcoding it across HTML, JS, or Python.
4. Provide project metadata in every supported language when possible: title, description, SEO title, SEO description, keywords, usage notes, and FAQ.
5. Avoid putting critical instructions only inside images; if images contain text, provide language-specific variants or nearby accessible text.
6. Clearly declare unsupported languages so the platform upload flow does not over-publish the project to a market it cannot serve.
7. Do not perform heavy AI translation during first page load. Translation extraction, AI draft generation, review, and publish should happen during upload/edit/admin workflows.
8. If only one language is supported, keep the tool functional as-is and let the platform shell/SEO page handle the current site language around it.

## UI Defaults

- If the user has not chosen a visual style, palette, or art direction, default to `docs\VicroCode网站配色统一方案.md` for color and style design. Read that file from the current project/workspace before designing UI; if it is missing, search the workspace for `VicroCode网站配色统一方案.md` and use the nearest matching file.
- Use in-page web overlay components for all user-facing prompts, notices, errors, confirmations, and blocking messages. Do not rely on native browser `alert`, `confirm`, or `prompt`.
- For destructive or sensitive actions such as delete, clear, overwrite, reset, revoke, charge, publish, or irreversible changes, show an in-page confirmation overlay before execution and proceed only after the user explicitly confirms.

## Non-Negotiables

- Prefer same-origin `/api/...` in production unless the task explicitly requires cross-origin deployment.
- All user-facing prompts, confirmations, warnings, loading states, and errors must be presented through webpage overlay UI instead of native browser dialogs.
- Destructive or sensitive operations must not execute until the user confirms through a webpage overlay.
- Treat `/api/python-proxy/{projectId}/` as the real runtime entry for Python-backed projects.
- Keep platform project database management routes such as `/api/python/database/{projectId}/...` on the same project storage root for upload, confirm, backup, restore, and list operations.
- Treat uploaded project files as source content for `pro/`, not as the platform runtime directory.
- Write runtime outputs under the platform-managed `runtime/` and user-generated files under `runtime/storage/`.
- Write SQLite to the platform-managed `runtime/*.db`, not beside source code.
- For SQLite-backed Python apps, configure connection timeouts and `PRAGMA busy_timeout`, keep transactions short, and make concurrent write conflicts wait or retry transparently instead of surfacing `database is locked` to users.
- Do not pre-create a root `runtime/` folder inside the project source package just to simulate the platform.
- Do not build runtime paths as `Path(__file__).parent / "runtime"` or source-adjacent `runtime/...`.
- For Python apps, resolve read/write runtime paths from the runner environment or runtime working directory, while treating `__file__` as source/pro context.
- If no platform runtime directory is available locally, fall back to the project source directory itself rather than creating a project-external database location.
- If a project needs an initial SQLite template, keep the template `.db` in the uploaded source package and let the runner copy it into `runtime/` on first launch.
- If cached/default uploaded assets can exist as files under `runtime/storage/` or as seed files in the uploaded source package, reconcile those files with SQLite rows before requiring the user to re-upload them. UI previews and backend generation checks must agree.
- If seed/default media assets must survive VicroCode upload filtering, keep a copy in a stable source asset path such as `public/reference_assets/` or `assets/reference_assets/`, not only under source `storage/`. Backend reconciliation may copy these seed assets into runtime-visible `storage/reference_assets/` before validation.
- If platform upload filtering still makes seed/default media unreliable, store required small seed assets as BLOBs in the uploaded source/template SQLite database and let the backend restore them into runtime storage before generation validation.
- For multi-slot cached uploads, also support restoring missing SQLite rows from a complete source or runtime `storage/uploads/*_{slot}.ext` set by copying the selected files into runtime-visible `storage/reference_assets/` before generation validation.
- For staged cached-upload generation flows, do not make generation depend only on cached SQLite rows from earlier upload requests. Before starting generation, submit a request-time snapshot of all required asset files/blobs, or verify the generation endpoint can read the required runtime assets.
- Automatic cached-asset reconciliation must respect explicit user clears, but do not let an old runtime clear marker block seed/default assets that are intentionally shipped in the newly uploaded source package. The clear marker should only block opportunistic restoration from historical runtime/source `storage/uploads` sets until the user uploads a new asset.
- Do not reference `runtime/...` files directly from frontend HTML, script, or asset URLs in the uploaded source package.
- Exclude local runtime artifacts such as `runtime/`, `__pycache__/`, logs, and local temp outputs from the upload bundle unless the user explicitly asks for a local-only package.
- Do not rely on `localStorage` alone for core state.
- Do not use `proxy-project-by-id` as the default runtime path for Python projects.
- Do not hardcode localhost or fixed absolute asset paths into deliverables intended for VicroCode.
- Do not require SDK usage for ordinary website or AI app development.
- If the app performs initial async data/media loading after HTML load, send a one-time parent-window readiness signal only after the first usable UI state is rendered. Use `window.parent.postMessage({ type: "vicro-project-ready" }, "*")` defensively, and do not include secrets, internal paths, tokens, or platform implementation details in the message.
- For image-heavy or gallery-style apps, do not assign real `src` URLs to every offscreen image during initial render. Use placeholders plus `data-src` and `IntersectionObserver` or an equivalent list virtualization/pagination strategy. Native `loading="lazy"` is only a supplement and is not enough if project code still writes all real image URLs into `src` at once.
- Image placeholders should be visible in the finished page layout and show a per-image loading state or progress indicator. Load visible images through a small controlled queue instead of allowing all gallery/result images to download at the same time.
- For image-heavy first screens, send the project readiness signal after data and the visible usable state are rendered; do not wait for every gallery/history image to download. Selected, above-the-fold, preview, and lightbox images may load eagerly, but offscreen gallery/result images must be deferred.
- Do not assume the user wants CN or EN routing. Detect it or ask.
- Do not treat an existing project the same way as a greenfield build. Audit first, then patch.
- For file uploads on VicroCode, use visible upload progress and serialize uploads so the next file cannot start until the previous upload has completed and returned a valid JSON response.
- For slow clear/delete actions that affect uploaded media, lock the relevant buttons and show an explicit "clearing/deleting" loading state until the server returns JSON.
- File upload endpoints must return JSON for both success and failure. Do not let upload failures fall through to HTML error pages or raw Python exceptions.
- After saving an uploaded file, avoid fragile "save then immediately subscript a possibly empty row" assumptions. Return a deterministic payload or explicitly handle a missing database row with a JSON error.
- For Python projects, only guide supported `python_version` values: `3.9`, `3.10`, or `3.11`. Default to `3.10`.
- Do not default new VicroCode Python projects to `3.12+` unless the user explicitly accepts that it falls outside the platform's normal supported range.
- For coin-charged actions, charge only after the feature, generation, unlock, or download has actually succeeded.
- Do not design default VicroCode monetization flows that pre-deduct coins before success unless the user explicitly asks for a special reservation or escrow-like pattern.
- For Python-backed apps that run inside `/api/python-proxy/{projectId}/`, do not assume VicroCode coin charging requests made from the proxy page will be accepted. If the charge API requires project-page origin, make the charge request from the accessible `/p/{projectId}` parent/top window context, or otherwise use an officially supported project-run-page charge bridge.
- Do not discard a successfully generated result only because a post-success charge call was made from the wrong proxy origin. Fix the charge origin first, then decide whether failed charges should lock, hide, or delete the result.
- For async generation jobs, treat an immediate `404`/`task not found` during polling as a temporary pending state for a bounded grace period. Keep the pending UI visible and retry status/gallery lookup before surfacing failure.
- Do not delete, hide, or permanently fail a generated result only because the first result fetch fails. Keep a retry path and recover from durable output files when available.
- Do not make background generation threads depend only on transient SQLite rows that were just inserted by the request handler. Pass a request-time snapshot of required parameters and runtime file paths into the background worker, and use SQLite as persistence/reporting rather than the only source of truth during the first run.
- For long async media generation, reconcile from durable result artifacts before declaring failure: if `runtime/storage/.../{job_id}.png` or an equivalent completed output exists but SQLite still says `processing`, repair the job status and materialize the gallery/result row from the file.

## Upload Shape

When the project will be uploaded to VicroCode:

1. Keep the source package limited to source assets such as `app.py`, `index.html`, `public/`, `templates/`, `static/`, and optional template `.db` files.
2. Assume the platform will place that source under `User_File/{username}/proname/{project_directory}/pro/`.
3. Assume the platform will create and manage `User_File/{username}/proname/{project_directory}/runtime/` separately at run time.
4. Do not present a project-local root `runtime/` folder as part of the recommended upload structure.
5. For local development, prefer a compatibility path that keeps template/state files inside the project directory when platform runtime is absent, so the uploaded directory still contains the needed initial data.

## AI Integration Guidance

- Do not default to VicroCode's own model API.
- Ask the user which provider or relay they want to use.
- Collect the exact integration inputs before implementation.
- When the user has not provided credentials or provider details, stop and ask for them instead of fabricating defaults.
- Respect provider-specific auth and payload formats.

## Pricing Guidance

- For project monetization, explain which user actions should consume coins and why.
- Default to post-success charging, not pre-execution charging.
- For model API billing, prefer template-style pricing guidance, not ad hoc per-model guessing.
- Use coin language explicitly. The platform convention is `100 coins = 1 RMB`.
- Distinguish:
  - fixed project price or feature charge
  - upstream AI/model usage billing

## Legacy Charge Guidance

If the user explicitly wants in-project VicroCode coin charging:

1. Reuse `public/sdk/vicrocode-sdk-v001.js` or `public/sdk/vicrocode-sdk-v002.js`.
2. Keep the charge logic separate from general business API design.
3. Assume `verify-user` only returns login basics, not balance.
