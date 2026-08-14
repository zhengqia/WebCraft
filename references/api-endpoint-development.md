# VicroCode API Endpoint Development

Load this file whenever the user wants to create, repair, upload, test, or publish a hosted Python API tool in VicroCode.

## Contents

1. Product boundary
2. Access and development flow
3. Workspace contract
4. Handler and schema contract
5. Dependencies and environment
6. Security and credentials
7. Testing, versioning, and publishing
8. Invocation contract
9. Acceptance checklist

## 1. Product Boundary

A VicroCode API endpoint is not a website project and not a Flask/FastAPI server.

For an API endpoint:

- use `/user-center/api-endpoint-hosting`
- create the API tool record before entering its development workspace
- use `/user-center/api-endpoint-hosting/{id}/develop?workspace_window=1` for online development
- implement one platform-called Python `handler`
- do not create HTML, frontend routes, Flask/FastAPI apps, a listening port, SQLite, or a project `runtime/` tree
- do not apply website-project `/p/{id}` or `/api/python-proxy/{id}/` conventions

Keep API endpoint development and SKILL development separate. Do not combine their files, API routes, release rules, or user interfaces.

## 2. Access And Development Flow

API endpoint creation, upload, online AI development, testing, and publishing require an active Super Individual VIP or higher. Current quotas are:

- Super Individual: 20 API tools
- Team: 100 API tools
- Enterprise: unlimited

Use this order:

1. Create a named API tool in `/user-center/api-endpoint-hosting`.
2. Define or confirm the input variables, output fields, data types, required fields, and examples.
3. Enter the dedicated development workspace.
4. For AI-assisted development, select a usable AI Model Center APIKEY. Send the user to `/user-api-center` if none exists.
5. Let the platform use its administrator-configured primary/fallback development models. Do not hardcode model names into endpoint source.
6. Generate or edit the allowed workspace files.
7. Run syntax, schema, dependency, and security checks.
8. Test with form-mode input first; use JSON mode only when it is useful.
9. Fix every failed check and test again.
10. Upload at least three screenshots, set a unique version number, choose whether to enter the marketplace, and submit review.

The AI must clarify ambiguous requirements before generating code. It should confirm the contract with the user instead of guessing field meanings, charging behavior, external APIs, or sensitive data handling.

## 3. Workspace Contract

Required core files:

```text
main.py
input.schema.json
output.schema.json
```

Recommended file:

```text
README.md
```

Optional dependency file:

```text
requirements.txt
```

Additional files must remain in the workspace root. Supported text extensions are:

```text
.py .md .txt .json .yaml .yml .toml .ini .cfg
```

Rules:

- never create subdirectories, absolute paths, `..` paths, symlinks, executables, archives, databases, or binary assets
- never read, write, list, rename, or delete files outside the current endpoint workspace
- do not create `.env`, credential files, virtual environments, caches, logs, or generated runtime directories
- keep the total editable workspace under 2 MB
- keep `main.py` non-empty and both schema files as JSON objects
- do not add `vicrocode.json`; it is not part of the current hosted endpoint workspace contract
- do not expose or mention server filesystem paths in source, errors, README content, or user-facing output

## 4. Handler And Schema Contract

Define this exact callable in `main.py`:

```python
def handler(payload: dict, context: dict) -> dict:
    """Receive validated JSON input and return a JSON-serializable result."""
    name = str(payload.get("name") or "").strip()
    return {"greeting": f"Hello, {name}"}
```

Do not start a web server or parse HTTP headers inside `main.py`. VicroCode handles authentication, HTTP, schema validation, rate limits, idempotency, charging, and response wrapping outside the user function.

Treat `payload` as the request JSON object. Treat `context` as platform-supplied, non-secret request metadata. Never assume it contains a real API key, database credential, host path, or another user's data.

Example `input.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Name to greet",
      "examples": ["VicroCode"]
    }
  },
  "required": ["name"],
  "additionalProperties": false
}
```

Example `output.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "greeting": {
      "type": "string",
      "examples": ["Hello, VicroCode"]
    }
  },
  "required": ["greeting"],
  "additionalProperties": false
}
```

Make the handler result match `output.schema.json` exactly and keep it JSON serializable. Do not return file handles, generators, custom objects, raw exceptions, or secrets.

## 5. Dependencies And Environment

Target Python 3.10-compatible code. Prefer the standard library.

When a third-party package is genuinely required, add a root `requirements.txt`. The platform installs dependencies into a project-isolated cache during testing and invocation, using configured HTTPS domestic PyPI mirrors.

Allowed requirement examples:

```text
pydantic==2.11.7
python-dateutil>=2.9,<3
```

Dependency rules:

- use only PyPI package names with optional versions, extras, and environment markers
- never use URLs, Git repositories, local paths, editable installs, pip options, or custom index directives
- declare no more than 20 direct packages and keep the file under 16 KB
- use packages that provide compatible prebuilt wheels; native builds, installers, services, and system DLL setup are unsupported
- do not run `pip`, `uv`, `conda`, PowerShell, shell, or subprocess installation commands from source
- do not vendor a virtual environment or site-packages into the workspace

Current local Runner limits are up to 30 seconds, 256 MB process-tree memory, and 5 MB JSON output. Tests may run without Hyper-V during the current low-traffic phase, but this is not a production security guarantee. Do not weaken scanner or execution restrictions to make a test pass.

## 6. Security And Credentials

Current endpoint code must not perform arbitrary filesystem, subprocess, operating-system, socket, or direct network access. It must not use dynamic execution or Python internal-object escape techniques.

Never ask the user to paste an API key into chat or endpoint files. If the requirement needs an authenticated third-party API:

1. direct the user to `/credential-vault`
2. ask them to create the hosted credential and bind it with “绑定API工具接口”
3. keep only the safe hosted identifier in the design
4. confirm that the VicroCode endpoint runtime exposes an approved proxy capability before generating the outbound call

Binding a credential does not authorize arbitrary `requests`, sockets, provider URLs, or secret access in the current local Runner. If the approved proxy capability is unavailable, explain that limitation and stop instead of embedding a key or bypassing the scanner.

Keep these key types distinct:

- AI Model Center APIKEY: selected by the author only for AI-assisted development
- Credential Vault record: stores a third-party secret outside source
- `vco_api_...`: created by a consumer to invoke a published API tool

Never write, print, log, return, screenshot, or commit any of them.

## 7. Testing, Versioning, And Publishing

Before submission:

1. Test valid minimum input.
2. Test missing required fields, wrong types, boundaries, empty values, and Unicode.
3. Confirm syntax and security scans pass.
4. Confirm every imported third-party module is declared in `requirements.txt`.
5. Confirm output is JSON serializable and passes `output.schema.json`.
6. Confirm errors do not reveal paths, source, secrets, or internal stack traces.
7. Configure at least five free successful trial calls; fewer than five cannot pass review.
8. Set the successful-call price in whole coins or choose free. Charging is completed only for a successful invocation.
9. Upload at least three distinct screenshots.
10. Use the platform-suggested next version, such as `1.0.0` then `1.0.1`; never reuse a historical version label.
11. Choose whether the reviewed release should also be published to the VicroCode marketplace.

Published versions are immutable. Later workspace changes do not affect the live version until a new version passes administrator review. A rejected update must leave the previous live version unchanged.

## 8. Invocation Contract

Consumers first add the tool to “我的 API 工具”, then create one or more independent APIKEYs for that tool. Invoke the current published version with:

```bash
curl -X POST "https://YOUR_VICROCODE_DOMAIN/api/v1/tools/TOOL_SLUG/invoke/" \
  -H "Authorization: Bearer vco_api_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-business-operation-id" \
  -d '{"name":"VicroCode"}'
```

The request body must be a JSON object and is limited to 1 MB. The optional `Idempotency-Key` prevents a repeated business operation from being charged twice. Do not place the API key in source code; read it from the consumer application's secure environment.

## 9. Acceptance Checklist

Before handoff, verify:

1. The deliverable is a hosted API endpoint, not a website server.
2. Only supported root workspace files exist.
3. `handler(payload, context)` exists and requires no host paths or secrets.
4. Input and output schemas are valid JSON objects and match real behavior.
5. Dependencies use the restricted wheel-only `requirements.txt` format and pass domestic-mirror installation.
6. Security scans, dependency setup, valid tests, and invalid-input tests pass.
7. No API keys, provider URLs requiring secrets, `.env` files, or absolute paths exist in the workspace.
8. The price, at least five free trials, three screenshots, unique version, and marketplace choice are ready for review.
9. Invocation documentation uses a consumer-created `vco_api_` key and the published tool route.
