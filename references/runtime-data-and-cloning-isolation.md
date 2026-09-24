# Runtime Data Storage and Delivery Isolation

Read this file whenever the app stores state in files instead of a database, or whenever
the project may be cloned, delivered, or sold as source.

This is a hard requirement, not a suggestion. Getting it wrong leaks the original author's
real data to every buyer and clone recipient.

## 1. Why this matters

The platform has two project roots:

| Root | Content | Delivered to buyers/clones |
|---|---|---|
| `pro/` | source code and **templates** | yes, the whole tree is delivered |
| `runtime/` | live state written while the project runs | never |

SQLite is safe because of one convention: the `.db` inside `pro/` is a read-only template,
and the runner copies it into `runtime/` on first launch, after which all reads and writes
go to `runtime/`. So `pro/` never accumulates real data.

A project that stores records in `data.json`, `db.js`, `records.json`, `data/*.json`, or any
other plain file has no such convention. If the app writes to the copy inside `pro/`, then:

- the original author's real records are visible inside their own project tree,
- the clone snapshot and the `sourdown/{username}.zip` source package both contain those
  records,
- every recipient gets the author's data.

## 2. Mandatory contract

1. **Declare every runtime data path** in a `vicrocode.project.json` file at the project root
   (the folder that becomes `pro/`).
2. **Keep uploaded copies as empty templates.** The file may exist in the source package, but
   it must contain only the initial/seed shape (`[]`, `{}`, `{"items": []}`), never the author's
   real records.
3. **Never put real user data into the uploaded source package.** No exported JSON dumps, no
   "just for now" samples with real names, emails, orders, or IDs.
4. **Write runtime file data through `runtime/`**, exactly like SQLite: resolve the runtime
   directory from the runner environment and copy the template there on first launch.
5. **Do not ship a project-local root `runtime/` folder.** The platform owns it.

## 3. The declaration file

Create `vicrocode.project.json` in the project root:

```json
{
  "schema": "vicrocode.project.v1",
  "storage_type": "json_file",
  "runtime_data": [
    "data/",
    "data.json",
    "db.js"
  ]
}
```

Rules:

- `runtime_data` entries are paths relative to the project root (`pro/`). Files or folders
  are both allowed.
- Folder entries cover everything inside them, so `"data/"` is the simplest correct answer
  for a folder-based store.
- `storage_type` is informational. Use `json_file`, `js_module`, `csv_file`, `memory` or
  `none` so the platform and reviewers understand the shape.
- The file itself stays in the source package — it carries no secret and tells buyers and
  clones where the data lives.
- The platform also accepts `dynamic_data_paths`, `data_paths`, or
  `storage.paths` as aliases, but `runtime_data` is the canonical key.

When this file is present, the upload page auto-selects those paths, the platform records
them on the project, and no manual step is needed at upload time — this is what makes
"one-click upload" work.

## 4. Recommended project shapes

### Python (Flask/FastAPI) with file storage

```text
app.py
vicrocode.project.json
data/
  orders.json          # template: []  or  {"items": []}
static/
templates/
```

```python
import json
import os

def data_dir() -> str:
    # runtime/ is the platform-managed read/write area (same idea as runtime/*.db).
    runtime_root = os.environ.get("VICRO_RUNTIME_DIR") or os.getcwd()
    path = os.path.join(runtime_root, "data")
    os.makedirs(path, exist_ok=True)
    return path

def load_orders() -> list:
    target = os.path.join(data_dir(), "orders.json")
    if not os.path.exists(target):
        # first launch: seed from the source template next to the code
        template = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "orders.json")
        if os.path.exists(template):
            with open(template, "r", encoding="utf-8") as handle:
                return json.load(handle)
        return []
    with open(target, "r", encoding="utf-8") as handle:
        return json.load(handle)

def save_orders(rows: list) -> None:
    target = os.path.join(data_dir(), "orders.json")
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
```

Notes:

- `VICRO_RUNTIME_DIR` is injected by the runner; `os.getcwd()` is also the runtime directory.
- Never build the data path from `__file__` for writes. `__file__` points at `pro/`, which is
  the delivery area.
- If `VICRO_RUNTIME_DIR` is absent (local development), falling back to the project directory
  is acceptable as long as the file is declared in `vicrocode.project.json`.

### Static / browser-only app

A pure static site cannot write server-side files. If a "JSON file" appears to hold the
author's data, it is almost always:

- a dataset exported once and committed by mistake — remove it and fetch real data from the
  backend instead, or
- state that belongs in the backend/runtime — move it behind a Python endpoint.

Do not design a static app whose only persistence is a source-controlled JSON file.

### JS module store (`db.js`, `store.js`)

Declare it:

```json
{ "schema": "vicrocode.project.v1", "storage_type": "js_module", "runtime_data": ["db.js"] }
```

Keep the shipped module a pure empty template:

```js
// db.js — template only. Runtime data lives in runtime/, not here.
module.exports = [];
```

If the module mixes helper functions with data literals, split it: keep logic in
`db.js` and move the data to `data.json`, then declare only `data.json`. The platform cannot
safely empty a file that also contains code, so a mixed file is reported as a manual risk
instead of being isolated automatically.

## 5. What the platform does with the declaration

1. **Upload** — the manifest and the upload form fill `dynamic_data_paths` on the project, and
   the current content of those files is captured as the author's trusted template baseline.
2. **Clone snapshot / source package** — delivery runs on a copy. Each declared file is
   replaced by the trusted baseline; when no trusted baseline exists, it falls back to an
   empty template instead of shipping the author's records. The author's own folder is never
   modified, and a copy of their real data is kept under
   `User_File/_dynamic_data_backups/{projectId}/{timestamp}/`.
3. **Runtime** — on launch, the declared templates are copied into `runtime/`, and the runner
   redirects reads/writes of those paths from `pro/` to `runtime/`, so `pro/` stays exactly as
   uploaded.
4. **Health checks** — the admin clone-health page flags projects whose snapshot predates the
   isolation, or whose declared files have no trusted baseline.

## 6. Detection signals the platform uses

You do not have to guess; declare the paths. But these are the signals used to catch missing
declarations, so avoid accidental matches:

- a write call in source code targeting a data file (`fs.writeFileSync`, `json.dump`,
  `open(path, "w")`, `JSONFilePreset`, `persist()`),
- a dependency that means file storage (`lowdb`, `json-server`, `nedb`, `electron-store`,
  `conf`, `tinydb`, `shelve`, `diskcache`),
- file names that usually mean a whole dataset (`data.json`, `db.json`, `users.json`,
  `orders.json`, `records.json`, `store.json`, `messages.json`, `todos.json`, `data/`),
- JSON whose top level is an array, or whose elements carry `id` / `created_at` / timestamp
  fields.

Files under `static/`, `assets/`, `public/`, `templates/`, `locales/` are treated as static
assets and are not auto-selected, so a static catalog JSON placed there will not be flagged.

## 7. Acceptance checklist

Before finishing a project that stores state in files:

1. `vicrocode.project.json` exists in the project root and lists every runtime data path.
2. Every declared file in the source package is an empty template, with no real records.
3. All writes resolve to the runtime directory, not to a path built from `__file__`.
4. No `runtime/` folder is shipped inside the project source.
5. No exported production data (JSON dumps, CSV exports, `db.js` snapshots, uploaded media)
   is present in the source package.
6. If the project was previously uploaded with real data inside `pro/`, re-save it once so
   the platform recaptures a clean trusted baseline, then rebuild the clone version.
7. Run `scripts/scan_runtime_data.py <project-dir>` and confirm it reports no undeclared data
   files.
