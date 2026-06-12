# Pricing And Publish Guidance

Load this file when the task involves monetization, charging, upload, or publish flow.

## 1. Publish Destination

When the user finishes building a VicroCode website app, guide them to:

1. Upload/publish entry: `/project-upload-website`
2. Post-upload management: `/project-manage`

Explain this concretely:

1. Upload source or website package through `/project-upload-website`
2. After upload, manage the project, pricing, publish state, and subsequent edits from `/project-manage`

Do not leave the user with code only and no platform publish destination.

## 2. Coin Charging Categories

Distinguish two charging modes:

### A. Project-side charging

Use when the app itself should charge coins for user actions inside the project.

Examples:

1. unlocking a premium feature
2. starting a generation task
3. downloading a high-value result
4. buying permanent access to a source-code package or hosted project

This is where legacy in-project charging SDK usage may still be relevant.

### B. Model API charging

Use when the app consumes an upstream AI or model provider through the user's chosen API.

Examples:

1. text generation
2. image generation
3. Anthropic or Gemini native calls
4. agentic or workflow-like AI features

This should be priced as upstream AI/model usage, not as an unrelated flat charge unless the product intentionally wraps it that way.

## 3. How To Decide What Should Consume Coins

Recommend charging coins when all of the following are true:

1. the action creates measurable compute cost or content value
2. the action is not just navigation or trivial UI interaction
3. the user can understand the value exchange before clicking
4. the app can clearly determine whether the action succeeded or failed

Avoid charging coins for:

1. basic page viewing
2. form editing without costly backend work
3. retry loops caused by platform bugs
4. failed runs, failed generations, failed downloads, or failed unlock attempts

## 4. Charging Timing Rule

Default rule:

1. run the feature first
2. confirm success from the real business result
3. deduct coins only after success

Examples of success signals:

1. a generation task returned a usable result or output file
2. a paid download link was actually prepared and ready
3. a premium feature finished the requested server-side action
4. an unlock action really granted the target capability or content

If the action fails:

1. do not deduct coins
2. show the failure reason when possible
3. let the user retry without hidden extra charging
4. do not fake success just to justify a deduction

Do not default to pre-deducting coins before compute starts unless the user explicitly wants a reservation, deposit, or escrow-like design and understands the tradeoff.

## 5. Project-Side Pricing Guidance

If the user wants a fixed in-project charge:

1. explain the charged action explicitly
2. show the price in coins before execution
3. state that the deduction occurs only after success
4. recommend a simple low-friction starting price for validation
5. keep the charge amount configurable instead of scattering literals

Platform convention to mention:

```text
100 coins = 1 RMB
```

For source-code or hosted-project listing flows, current platform UI also uses coin-based pricing and describes the same conversion.

## 6. Model API Pricing Guidance

Do not guess final per-model billing blindly.

Explain the billing basis first:

1. what the upstream provider charges by
2. whether the user wants fixed project-side pricing or usage-based pricing
3. whether the app should absorb cost, pass through cost, or add markup

Recommended guidance:

1. If the user is calling their own upstream provider key, keep the project-side pricing explicit and simple.
2. If the user wants to resell model usage inside a project, propose either:
   - pass-through style upstream pricing, or
   - a fixed project-side package price with an explicit quota
3. If exact pricing data is missing, say so and propose a provisional rule instead of pretending it is exact.
4. Even when AI or model usage is involved, keep the default deduction timing as post-success, not pre-run.

## 7. Pricing Suggestions The Skill Should Give

When asked to help price an AI feature, the skill should usually output:

1. which action is charged
2. whether this is project-side charging or upstream AI/model charging
3. when the coins are deducted
4. the proposed coin amount or pricing rule
5. why that pricing choice is reasonable
6. where the user can later adjust it

## 8. Minimum Publish And Monetization Checklist

Before finishing a monetized VicroCode app, verify:

1. the user knows to upload via `/project-upload-website`
2. the user knows to manage pricing and publish state via `/project-manage`
3. charged actions are clearly identified
4. the deduction happens only after success
5. prices are shown in coins
6. AI/model pricing is not confused with generic project charging
