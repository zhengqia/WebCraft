# AI Model Integration

Load this file whenever the app needs AI or model capability.

## 1. Default Strategy

Do not default to VicroCode's own model API or any platform-managed service.

Instead:

1. Ask which model provider or API the user wants to use.
2. Ask for the minimum configuration needed to integrate it safely.
3. Implement against the user's chosen provider.

## 2. Required Information To Collect

When the user wants AI features, collect these items before wiring code:

1. Provider name
   - examples: OpenAI, Anthropic, Gemini, OpenRouter, SiliconFlow, Azure OpenAI, custom relay
2. Base URL or API root
   - if applicable
3. Exact endpoint path
   - if not standard
4. API Key or credential injection method
   - direct API key
   - env var name
   - backend secret config
5. Model name
6. Protocol family
   - OpenAI-compatible
   - Anthropic native
   - Gemini native
   - custom JSON schema
7. Capability type
   - text/chat
   - image generation
   - embeddings
   - audio
   - video
   - multimodal
8. Where the call should happen
   - frontend only
   - backend only
   - both
9. Whether streaming is required
10. Whether the result must be stored or just displayed
11. Whether the feature should cost coins inside the project
12. If pricing matters, what the upstream billing basis is
   - per request
   - per token
   - per image
   - monthly quota

## 3. Minimum Questions The Skill Should Ask

If the user simply says “I need AI” and gives no provider details, ask for:

```text
1. 你要接哪个模型供应商或 API？
2. 你的 Base URL / 接口根地址是什么？
3. 你准备使用哪个模型名？
4. 认证方式是什么？是 API Key 吗？准备从哪里读取？
5. 这是文本、图片、视频、音频，还是 embedding？
6. 你要前端直连，还是后端代调？
7. 需要流式输出吗？
8. 这个功能是否要做金币收费？
```

Do not move into implementation until these are either answered or safely inferred.

## 4. Security Rules

1. Do not hardcode secrets into source code.
2. Prefer backend-only secret storage whenever the provider key is sensitive.
3. If the user insists on frontend direct calls, make the risk explicit.
4. Read secrets from env vars, deployment config, or user-managed settings.
5. If the user says they do not yet have credentials, stop and ask them to obtain them from their chosen provider.

## 5. Route Selection Rules

Choose by the user's actual provider protocol:

1. OpenAI-compatible
   - typically `POST /chat/completions`
2. Anthropic native
   - typically `POST /messages`
3. Gemini native
   - typically `POST /models/{modelAction}`
4. Image generation
   - provider-specific image route
5. Custom relay
   - follow the user-supplied docs or endpoint

Do not force every provider through one schema.

## 6. Example Integration Patterns

### OpenAI-compatible

```js
const response = await fetch(`${baseUrl}/chat/completions`, {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model,
    messages,
  }),
});
```

### Anthropic native

```js
const response = await fetch(`${baseUrl}/messages`, {
  method: 'POST',
  headers: {
    'x-api-key': apiKey,
    'anthropic-version': '2023-06-01',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model,
    max_tokens: 1024,
    messages,
  }),
});
```

### Gemini native

```js
const response = await fetch(`${baseUrl}/models/${modelAction}`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(payload),
});
```

## 7. Pricing Guidance

If the user wants AI features to cost coins in the VicroCode project:

1. ask what the upstream cost basis is
2. ask whether they want fixed project-side pricing or usage-based pricing
3. make the coin rule explicit in the UI before charging

Do not invent exact cost-based pricing if the provider's billing data is missing.

## 8. Common Mistakes

Avoid:

1. choosing a provider for the user without asking
2. hardcoding secrets into frontend code
3. assuming every provider uses `Bearer` auth
4. assuming every provider uses OpenAI-compatible JSON
5. implementing model calls before collecting endpoint, auth, and model info
