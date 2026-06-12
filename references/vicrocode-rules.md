# VicroCode Rules Reference

Load this file before editing a VicroCode website app.

## 1. Runtime Facts

1. Frontend entry is usually `/p/{projectId}`, not `/index.html`.
2. Python-backed pages often end up running under `/api/python-proxy/{projectId}/`.
3. Uploaded project source lands in `pro/`, which is a code/template area.
4. The platform-managed sibling `runtime/` is the real read/write area.
5. For Python Runner projects, `__file__` usually still points at `pro/`, while the current working directory may be `runtime/`.
6. A source package should not include its own fake root `runtime/` directory just to mimic the platform.
7. Published deployment can expose timing, refresh, and route-normalization issues that local testing may not show.

## 2. Project-Type Decision

Classify the app before patching:

1. Static frontend only
2. Frontend + Python/Flask
3. Frontend + Python + SQLite
4. Generation/media workflow

If the app involves Python, SQLite, file upload, generated files, or long-running tasks, assume runtime path and sync rules apply.

If the task is modifying an existing site rather than building from scratch, do this first:

1. identify the current entry route
2. identify the current runtime and persistence assumptions
3. identify whether the app already has a backend or AI integration
4. identify the smallest safe change set

Do not begin by rewriting the whole app if the problem is really route, runtime, or storage incompatibility.

## 3. Python Version Rules

If the app includes Python or Flask:

1. Only guide supported `python_version` values: `3.9`, `3.10`, or `3.11`.
2. Default to `3.10` if the user does not have a hard requirement.
3. Do not silently choose `3.12+` for VicroCode-targeted projects. Flag it as outside the platform's normal supported range first.
4. The platform website may itself run on Python `3.10.6`, but project runtime selection is separate. Do not confuse the website's own interpreter with the project's selected runtime.
5. When discussing execution commands or server preparation, prefer version-explicit launch patterns such as `py -3.9`, `py -3.10`, or `py -3.11`, or the matching full interpreter paths.

## 4. Path Rules

### Platform API

1. Prefer same-origin `/api/...` in production.
2. Use explicit `apiBaseUrl` only when the deployment is intentionally split.
3. Avoid default hardcoded `localhost`, `127.0.0.1`, or a fixed backend host.
4. Do not use `api.vicrocode.com` / `api.vicoco.cn` as a project backend, platform business origin, or master/slave forwarding URL. These subdomains are only for the VicroCode API Center / model gateway public entrypoint.

### Python Project API

1. Use `/api/python-proxy/{projectId}/...` for the app's Python backend.
2. Do not default to `/api/proxy-project-by-id/{projectId}/...` for runtime behavior.
3. If you need project runtime assets from a Python app, normalize `/storage/...` URLs through the Python proxy when appropriate.

### Project Database Management API

1. `/api/python/database/{projectId}/...` operates on the current project `pro/`, `runtime/*.db`, and `runtime/backup/`.
2. Do not split upload, confirm-upload, backup, restore, delete, import-schema, and list-backups across different storage roots.
3. These operations must resolve to one consistent project filesystem, otherwise backups, temp upload paths, and database rows will appear inconsistent.

### Static Assets

1. Prefer relative asset paths.
2. Allow optional dynamic loading of SDK/vendor assets from `python-proxy` when the page actually runs there.
3. Do not make SDK loading a hard blocker for the whole page unless the task explicitly depends on it.

## 5. Persistence Rules

### Runtime Files

Put user-generated and runtime outputs in:

```text
runtime/
runtime/storage/
runtime/uploads/
runtime/models/
```

Avoid writing runtime results only into:

```text
pro/
backend/storage/
source-adjacent temp folders
```

Do not assume the uploaded source package itself should contain a root `runtime/` folder. On VicroCode, `runtime/` is created and managed outside the uploaded source tree.

### SQLite

1. Treat SQLite as runtime state, not as static project content.
2. Put real runtime databases in `runtime/*.db`.
3. Do not build runtime DB paths as `Path(__file__).parent / "runtime" / "...db"` because `__file__` normally lives under `pro/`.
4. Resolve runtime DB and storage roots from the runner environment or runtime working directory.
5. If the platform runtime directory is absent in local development, fall back to the project directory rather than a project-external temp/AppData database path.
6. If the project needs initial data, keep the template `.db` in source/pro and let the runner copy it into `runtime/` on first launch.
7. Configure SQLite connection timeouts and `PRAGMA busy_timeout`; when another request is writing, queue/wait or retry transparently instead of returning `database is locked` to the user. Keep write transactions short and never hold a database transaction across slow network/model calls.
8. If refresh loses data after upload, inspect SQLite pathing before touching UI code.
9. If cached/default user assets exist as files under `runtime/storage/` or as seed files in the uploaded source package, but their SQLite rows are missing after upload or runtime creation, backfill or reconcile the rows before reporting "missing upload" to the user.
10. Before a generation flow trusts cached uploads, refresh the frontend state from the backend source of truth so visual previews and server-side availability checks do not diverge.
11. For staged cached-upload generation flows, do not make generation depend only on cached SQLite rows from earlier upload requests. Submit a request-time snapshot of every required asset file/blob, or verify the generation endpoint can read the required runtime assets.
12. For async generation jobs, treat early `404` or "task not found" polling responses as a temporary pending state for a bounded grace period.
13. Do not delete, hide, or permanently fail a generated result only because the first result fetch fails. Keep a retry path and recover from durable output files when available.
14. For fixed multi-slot uploads such as `front/left/right/rear/top`, if `storage/reference_assets/{slot}.ext` is missing but a complete source or runtime `storage/uploads/*_{slot}.ext` set exists, copy the chosen complete set into runtime-visible `storage/reference_assets/` and then backfill SQLite rows before rejecting generation.
15. If users can explicitly clear cached uploads, persist a small runtime clear marker or equivalent server-side state. The marker should block opportunistic restoration from historical `storage/uploads` groups, but it must not block seed/default assets intentionally shipped in the uploaded source package such as `storage/reference_assets/{slot}.ext`, `public/reference_assets/{slot}.ext`, or `assets/reference_assets/{slot}.ext`. New successful uploads should remove the marker.
16. If platform upload filtering may skip source `storage/`, put required seed/default media in a stable source asset folder such as `public/reference_assets/` or `assets/reference_assets/` and let the backend copy it into runtime `storage/reference_assets/` before validation.
17. If required seed/default media must be available even when directories are filtered or sync is partial, store compact seed assets as BLOBs in the uploaded source/template SQLite database and restore them into runtime storage before validating a generation request.

### URL Return Shape

Prefer relative runtime URLs such as:

```json
{
  "image_url": "/storage/uploads/13/01.png",
  "model_url": "/storage/models/13/generated.glb"
}
```

Then normalize them in the frontend when the app runs under `python-proxy`.

Do not hardcode frontend asset references such as `<script src="runtime/...">` in the uploaded source package.

## 6. iframe and State Rules

Assume the app may run in an iframe:

1. `window.self !== window.top`
2. parent URL may be unreadable
3. storage APIs may be restricted
4. autoplay, popup, and download behavior may be constrained

Do not store critical state only in `localStorage`. Prefer:

1. backend storage or runtime files
2. URL parameters
3. `localStorage` as a supplemental cache only

For apps whose visible first screen depends on async backend data, cached media, or gallery/list hydration, keep the project-side loading state active until the first usable UI state is rendered. Then send a one-time readiness signal to the parent page:

```js
function notifyVicroProjectReadyOnce() {
  if (window.__vicroProjectReadySent) return;
  window.__vicroProjectReadySent = true;
  try {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "vicro-project-ready" }, "*");
    }
  } catch (error) {}
}
```

Call this only after critical startup requests have settled and the user can see meaningful content or a stable empty state. The message is a public UI lifecycle signal only: do not include secrets, tokens, internal paths, server topology, user data, or debug details.

For image-heavy galleries, history lists, result grids, or media libraries, project-side lazy loading is required:

1. Do not put every real image URL into `<img src="...">` during initial render.
2. Render offscreen images with a lightweight placeholder `src` and keep the real URL in `data-src` or app state.
3. Use `IntersectionObserver`, list virtualization, pagination, or an equivalent visibility gate to assign the real `src` only when the image is near the viewport.
4. Native `loading="lazy"` and `decoding="async"` are useful but not sufficient by themselves when the app code still assigns all real `src` values at once.
5. Load only selected, above-the-fold, preview, and lightbox images eagerly.
6. Do not keep the parent-page readiness/loading overlay visible until all gallery/history images finish downloading. Signal readiness after the first usable UI state is rendered and defer the rest.
7. Show visible placeholders in the final layout before image downloads finish. Each image card should have its own loading/progress state so users can see images appear progressively.
8. For large galleries or generated-result histories, use a small controlled image download queue, for example 2-4 concurrent visible image downloads, rather than letting all visible and offscreen images download at once.

## 7. Upload Rules

For file uploads on VicroCode, local success is not enough. Published deployment can expose timing and response-shape bugs.

1. Upload UI must show progress for every real upload request.
2. Serialize user file uploads by default: while one file is uploading, disable other upload inputs and upload-triggering buttons until the current request completes.
3. Start the next upload only after the previous upload returns a valid JSON success response.
4. Parse non-JSON upload responses defensively and surface a clear error instead of assuming every response is JSON.
5. Upload APIs must return JSON for both success and failure. Add API error handlers for large files, HTTP errors, and unexpected exceptions.
6. Avoid save-then-read assumptions that can produce `NoneType` errors after delayed DB visibility. Return deterministic upload metadata from the save path, or handle a missing row with a JSON error.
7. Do not use multiple concurrent uploads as the default for Python-backed VicroCode apps unless the backend and deployed request path are explicitly designed and tested for it.
8. If an upload cache can be auto-restored from historical source/runtime upload files, make the clear/delete API disable that history-based restoration until the next successful upload; otherwise the UI's "clear" action is not real. Do not use this marker to suppress packaged seed/default assets after a fresh project upload.
9. Slow clear/delete actions for uploaded media need explicit loading states: disable related upload/generate buttons, show "clearing" or "deleting" progress/copy, and only reset the UI after a valid JSON response.

## 8. AI Integration Rules

1. Do not assume VicroCode's own model service.
2. First collect the user's chosen provider, base URL, auth method, model, and endpoint style.
3. Route requests by the provider's real protocol family:
   - OpenAI-compatible
   - Anthropic native
   - Gemini native
   - provider-specific custom API
4. Do not hardcode secrets in frontend code.
5. If the user has not provided enough provider information, pause and ask before implementing.

## 9. Coin Charging Rules

If the app charges VicroCode coins for an in-project action:

1. Treat post-success charging as the default rule.
2. Make the success condition explicit in product and code terms.
3. Deduct coins only after the target feature, generation, unlock, or download has actually succeeded.
4. If the action fails, do not deduct coins.
5. Do not hide pre-charge logic behind loading states, async polling, or vague "processing" copy.
6. If the user explicitly wants a reservation or escrow-like pattern, call out the tradeoff and do not present it as the default VicroCode pattern.
7. For Python-backed apps rendered through `/api/python-proxy/{projectId}/`, verify the VicroCode charge API accepts the request origin. If charge endpoints only accept the project run page, dispatch the charge request from the accessible `/p/{projectId}` parent/top window context or an officially supported charge bridge.
8. Do not treat a proxy-origin charge rejection such as "invalid request source" as an AI generation failure. The generated result and the charging settlement are separate states.

## 10. Debugging Order

When a VicroCode app breaks after upload:

1. Check the route the browser actually entered.
2. Check API path normalization.
3. For upload bugs, check whether multiple files were being uploaded concurrently and whether the failing response was non-JSON.
4. For project database upload/backup bugs, check whether upload, confirm, backup, restore, and list operations resolve to one consistent project storage root.
5. For post-success charge failures, check whether the current page is `/api/python-proxy/{id}` while the charge endpoint requires `/p/{id}` project-page origin.
6. Check whether runtime files were written to `runtime/` and sync-safe directories.
7. If the UI shows cached uploaded files but the backend reports missing files, check whether SQLite rows were lost while `runtime/storage/...` files still exist.
8. If staged cached uploads are followed by a generation POST and only some slots go missing online, check whether the generation request carries file/blob snapshots or only a "use saved cache" flag.
9. If only some cached upload slots are missing, check both `storage/reference_assets/` and complete historical `storage/uploads/*_{slot}.ext` groups before asking the user to upload again.
10. If an async job starts successfully but status polling immediately returns `404` or "task not found", treat it as a temporary pending state. Retry for a bounded grace period and also check the gallery/result endpoint before declaring failure.
11. If a background worker reports missing files/rows that the request handler just wrote, pass request-time snapshots of required parameters and runtime file paths into the worker instead of re-reading only fresh SQLite rows.
12. Check SQLite location.
13. Check whether the app relied on local browser state.
14. For existing projects, check whether the bug is caused by old architecture assumptions before redesigning code.
15. If monetization is involved, check whether charging was incorrectly triggered before success.
16. Only then spend time on CSS or interaction polish.

## 11. Common Bad Patterns

Avoid these:

1. Hardcoded `http://127.0.0.1:5000`
2. Generated files written beside source code
3. SQLite fixed beside source files
4. Runtime assets returned as broken absolute URLs
5. Shipping a project-local `runtime/` folder as part of the upload package
6. Building runtime paths from source-relative `.../runtime/...`
7. Frontend HTML that directly references `runtime/...` files from the source package
8. Core state restored only from `localStorage`
9. Fixing VicroCode bugs by changing prompts instead of code structure
10. Treating every AI model as a text `chat/completions` model
11. Assuming a Python app can target `3.12+` without checking platform support first
12. Deducting coins before the paid action actually succeeds
13. Starting several file uploads at once in a published VicroCode deployment without progress, locking, and JSON response validation
14. Letting upload endpoints return HTML error pages or raw exception strings to frontend upload code
15. Calling VicroCode coin charge APIs from a Python proxy iframe when the platform validates only `/p/{projectId}` project-page origin

## 12. Acceptance Checklist

Before finishing:

1. Confirm `projectId` detection works for `/p/{id}` and Python runtime paths when relevant.
2. Confirm the app survives refresh without losing important state.
3. Confirm runtime outputs land in `runtime/` and sync-safe locations.
4. Confirm SQLite, if used, is under `runtime/*.db`.
5. Confirm the uploaded source package does not depend on a project-local root `runtime/` folder or `runtime/...` frontend asset references.
6. Confirm Python projects are pinned to `3.9`, `3.10`, or `3.11`, with `3.10` as the default when unspecified.
7. Confirm coin-charged actions deduct only after success and do not pre-charge failed runs.
8. Confirm model calls use the correct provider route and do not hardcode secrets.
9. Confirm every real file upload has progress UI, upload controls are locked during the current upload, and upload APIs return JSON on success and failure.
10. Confirm post-success charge calls use a platform-accepted project-page origin when the app itself is served through `python-proxy`.
11. Confirm cached upload previews are backed by server-visible records or filesystem reconciliation, not by stale frontend state alone.
12. Confirm multi-slot cached uploads can recover from missing SQLite rows using source/runtime `storage/reference_assets/` or a complete source/runtime `storage/uploads/*_{slot}.ext` set.
13. Confirm source seed/default media needed at runtime is stored in a platform-upload-stable source folder such as `public/reference_assets/` if `storage/` may be filtered.
14. Confirm async job polling tolerates short pending periods without immediately showing "task not found".
15. Confirm background workers receive a request-time snapshot of required inputs and file paths when freshly inserted rows may not be immediately visible.
16. Confirm long async media jobs can recover from durable output files when runtime SQLite status is stale, rolled back, or stuck at `processing`.
17. For image-heavy apps, confirm offscreen gallery/history/result images do not receive real `src` URLs during initial render, visible image placeholders show loading/progress, image downloads are limited or queued, and readiness does not wait for all images to download.
