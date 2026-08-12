# Credential Proxy And Cloning

Load this file whenever a VicroCode project calls an authenticated API, uses Credential Vault, or will be offered for cloning.

## 1. Core Contract

VicroCode Credential Vault stores one hosted API as one unit:

- API name and provider
- complete API base/endpoint address
- stable project identifier such as `payment_api`
- authentication method and encrypted credential
- request-count, concurrency, and timeout protection

Project source keeps only the identifier. The platform resolves the current project, adds the bound owner's credential at the proxy layer, and forwards the request. A clone keeps the same identifier while its owner binds a different credential.

Never put these values in project files, browser storage, logs, prompts, examples, or query strings:

- provider API keys or bearer tokens
- Basic passwords
- OAuth client secrets or access tokens
- HMAC secrets
- VicroCode project proxy tokens

## 2. Required Workflow

When adapting an app for Credential Vault or cloning:

1. Inventory every outbound authenticated API call and every place a secret may exist.
2. Ask the developer to create one hosted API per credential/address pair in `/credential-vault` before upload.
3. Obtain only the hosted API identifier, API address, auth method, and protocol details. Do not ask the user to paste the raw secret into the coding conversation.
4. Replace direct provider URLs and client-side auth injection with the proxy patterns below.
5. Remove `.env`, `.env.*`, private keys, service-account files, credential JSON, and hard-coded secrets from the upload source.
6. Run `python scripts/check_clone_secrets.py <project-dir>` from the installed WebCraft package.
7. Test success, provider errors, missing binding (`409`), rate limits (`429`), and streaming/binary responses when used.
8. Upload through `/project-upload-website`.
9. In `/project-manage`, select the hosted APIs used by the project.
10. Run the platform project check. It scans source rules and uses the hosted credential to test the real connectivity of every selected API from the platform backend.
11. Submit administrator review only after both the source rules and API connectivity pass.

Do not create platform Credential Vault records through undocumented project code. The developer creates and manages them in the platform UI.

## 3. Browser And Static-Frontend Pattern

Use a relative URL without a leading slash:

```js
function vicroHostedApi(identifier, upstreamPath = "") {
  const safeIdentifier = encodeURIComponent(identifier);
  const safePath = String(upstreamPath).replace(/^\/+/, "");
  return `__vicro_proxy__/${safeIdentifier}/${safePath}`;
}

const response = await fetch(
  vicroHostedApi("payment_api", "orders"),
  {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ amount: 9900, currency: "CNY" })
  }
);

const payload = await response.json().catch(() => ({}));
if (!response.ok) {
  throw new Error(payload.message || `API request failed (${response.status})`);
}
```

Rules:

1. Do not add the provider `Authorization` header; VicroCode strips caller auth and injects the hosted credential.
2. Do not prefix this contract with `/`. A relative URL keeps the request in the current project URL space, including `/api/python-proxy/{id}/`.
3. Do not parse or hardcode a project ID.
4. Keep normal content negotiation headers. The proxy forwards a safe subset such as `Accept`, `Content-Type`, `Accept-Language`, `Range`, and conditional cache headers.
5. Query parameters and request bodies remain part of the business request and may be passed normally, but never place a secret in them.
6. If the configured API address already names the final endpoint, call the identifier with an empty `upstreamPath`. Otherwise append only the provider path below that configured address.

## 4. Python-Backend Pattern

VicroCode injects these runtime variables into the Python project process:

```text
VICRO_BACKEND_INTERNAL_URL
VICRO_PROJECT_PROXY_PATH
VICRO_PROJECT_PROXY_TOKEN
VICRO_PROJECT_ID
```

Use the first three only inside the Python backend:

```python
from __future__ import annotations

import os
from urllib.parse import quote

import requests


def call_hosted_api(identifier: str, upstream_path: str = "", **request_kwargs):
    backend = os.environ["VICRO_BACKEND_INTERNAL_URL"].rstrip("/")
    proxy_root = os.environ["VICRO_PROJECT_PROXY_PATH"].strip("/")
    project_token = os.environ["VICRO_PROJECT_PROXY_TOKEN"]
    safe_identifier = quote(identifier, safe="")
    safe_path = str(upstream_path).lstrip("/")
    url = f"{backend}/{proxy_root}/{safe_identifier}/"
    if safe_path:
        url += safe_path

    headers = dict(request_kwargs.pop("headers", {}) or {})
    headers.pop("Authorization", None)
    headers.pop("authorization", None)
    headers["X-Vicro-Project-Token"] = project_token
    return requests.request(url=url, headers=headers, **request_kwargs)


response = call_hosted_api(
    "payment_api",
    "orders",
    method="POST",
    json={"amount": 9900, "currency": "CNY"},
    timeout=65,
)
response.raise_for_status()
result = response.json()
```

Rules:

1. Never send `VICRO_PROJECT_PROXY_TOKEN` to the browser, response payload, template, logs, exception messages, or SQLite.
2. Never use it as the upstream provider credential. It authorizes only the current VicroCode project to call its bound identifier.
3. Do not default the internal backend address to a public VicroCode domain in production. Fail clearly if the injected variables are absent; local development may use an explicit developer-only mock configuration.
4. Restart the Python project after a new runtime integration is deployed so injected variables are present.
5. For streaming, use `stream=True` and close the response. For multipart requests, let `requests` generate the boundary; do not set it manually.

## 5. Authentication Ownership

Credential Vault supports non-AI APIs as well as AI/model APIs. The project request should not care which auth scheme the developer selected:

- Bearer token
- API key in a request header
- API key in a query parameter
- Basic authentication
- OAuth 2.0 Client Credentials
- HMAC signing
- multiple custom credential headers
- VicroCode AI Model Center authorization

The platform owns credential injection and OAuth token exchange. Project code owns only the provider's business payload and response handling.

Do not force third-party APIs into an OpenAI-compatible schema. Preserve the real provider method, path, body, response, streaming, and error semantics.

## 6. Clone Behavior

Code must satisfy all of these before clone review:

1. The identifier is stable and descriptive.
2. No project ID, provider secret, or original owner's username is embedded in the proxy call.
3. Missing credentials produce a clear UI that sends the project owner to `/credential-vault` instead of asking them to edit source.
4. A clone uses the same source and identifier but binds the clone owner's hosted API.
5. Updating a clone must preserve runtime data and credential bindings; do not move credentials into project files as an update workaround.
6. A clone cannot expose, edit, download, or re-clone its source. Do not design UI that promises those capabilities.
7. Clone purchase/renewal and upstream provider usage are separate. During active clone authorization, the clone owner does not pay the original developer again per project use, but third-party API/model costs may still apply to the clone owner's credential.

## 7. Error Handling

Handle these proxy outcomes explicitly:

- `403 PROJECT_PROXY_FORBIDDEN`: the caller cannot use this project/API.
- `409 CREDENTIAL_BINDING_MISSING`: the project owner must bind the identifier in Credential Vault.
- `409 TARGET_RECONSENT_REQUIRED`: the target origin changed and must be confirmed again.
- `429 PROXY_RATE_LIMIT` or `PROXY_CONCURRENCY_LIMIT`: show a retry-later message; do not loop aggressively.
- `502 MASTER_PROXY_UNAVAILABLE` or `UPSTREAM_REQUEST_FAILED`: platform/upstream temporary failure.

Do not display raw response bodies that may contain provider debugging data. Keep user errors useful and log only request IDs, safe status details, and non-secret context.

## 8. Acceptance Checklist

Before handoff, verify:

1. Search source for `.env`, key files, known key prefixes, and assignments containing `api_key`, `secret`, `token`, or `password`.
2. Confirm browser requests contain no provider credential.
3. Confirm Python logs and exceptions contain no project proxy token.
4. Confirm the original project works with its binding.
5. Confirm a missing binding returns a guided message.
6. Confirm the same source works after the project ID changes.
7. Confirm request-count and concurrency limits do not trigger retry storms.
8. Confirm the platform project check passes both source rules and selected hosted API connectivity before clone review is submitted.

## 9. Repairing Platform Connectivity Failures

When the VicroCode project check reports an API connectivity failure, use only the safe reason shown by the platform. Never ask the developer to paste the hosted secret into the conversation and never bypass the proxy to test from browser code.

Diagnose these areas as applicable:

1. API address and whether it represents the final endpoint or a base path.
2. Authentication placement: Bearer, header, query, Basic, OAuth2, HMAC, or custom headers.
3. HTTPS certificate validity, hostname match, and complete certificate chain.
4. Provider availability, firewall rules, ports, and provider IP allowlists. The test originates from the VicroCode backend, not the developer's browser.
5. OAuth2 token endpoint and client-credentials permissions.
6. Provider-side account permissions and API enablement when the result is `401` or `403`.
7. Timeout and retry behavior without disabling TLS verification or creating retry storms.
8. The `__vicro_proxy__/{identifier}/...` path and stable identifier used in project code.

Treat `400`, `404`, `405`, `409`, `415`, `422`, or `429` from the configured address as evidence that the network is reachable; the real business call may still require its documented method, path, parameters, or quota. Treat DNS failure, connection failure, timeout, TLS failure, `401`/`403`, and upstream `5xx` as blocking results that must be resolved before review.

After repairing the project, run `scripts/check_clone_secrets.py <project-dir>`, run relevant local integration tests, list the changed files, and ask the developer to return to `/project-manage` and run the project check again.
