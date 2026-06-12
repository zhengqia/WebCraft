# Standard Dialogue Template

Use this template when a VicroCode webapp task begins and key context is still missing.

Do not ask every question mechanically if the answer is already obvious from the repo or the user request. Ask only what is still needed.

## 1. First Decision: Site Flavor

If the user did not make this clear, ask first:

```text
这个应用要做中文版 / 国内站，还是 English / 国际站？
```

Why:

1. login links differ
2. upload/publish links may differ in copy language
3. user-facing product copy differs

## 1.5 Existing Site Or New Build

If the user did not make this clear, ask early:

```text
这是全新开发一个网站应用，还是修改 / 修复现有网站？
```

If it is an existing website, follow with:

```text
请补充这几个信息：
1. 现有网站是纯前端，还是带 Python / Flask / SQLite？
2. 现在主要要改什么：样式、功能、接入 AI、修 bug，还是迁移到 VicroCode？
3. 当前已知异常是什么？
4. 现有项目有没有已经在用的接口、数据库、存储目录或 AI 接口？
5. 如果是 Python 项目，当前用的是 3.9 / 3.10 / 3.11 哪个版本？
```

## 1.8 Python Version

If the app will use Python and the version is still unclear, ask:

```text
如果这是 Python 项目，你要用 Python 3.9、3.10 还是 3.11？
如果没有特殊依赖，默认我会按 3.10 来做。当前先不要按 3.12+ 设计。
```

## 2. Second Decision: Does The App Need AI

If unclear, ask:

```text
这个应用要不要接入 AI / 大模型接口？
```

If yes, immediately follow with:

```text
1. 你要接哪个模型供应商或 API？
2. 你的 Base URL / 接口根地址是什么？
3. 你准备用哪个模型名？
4. 认证方式是什么？API Key 要从哪里读取？
5. 这是文本、图片、视频、音频，还是 embedding？
6. 你要前端直连，还是后端代调？
7. 需要流式输出吗？
```

## 3. Third Decision: Monetization

If unclear, ask:

```text
这个应用是否需要金币收费？
如果需要，是项目内固定扣费，还是按模型调用量计费？
默认我会按“功能成功后再扣金币”来设计，你如果想改成别的模式，需要提前说明。
```

## 4. Fourth Decision: Publish Destination

If the user is building for VicroCode hosting but has not mentioned publish flow, ask:

```text
开发完成后，你是否要把它上传到 VicroCode 平台发布？
如果要，我会按 /project-upload-website 和 /project-manage 的流程来收尾。
```

## 5. Required Guidance When No API Credential Is Present

If the app needs model APIs and the user has not provided credentials yet, the skill should say something equivalent to:

```text
先确认你要接哪个模型供应商。然后请提供：
- Base URL / API 根地址
- 模型名
- 认证方式
- API Key 或它将从哪个环境变量读取
- 调用发生在前端还是后端

如果你还没有 API Key，需要先去你选择的模型供应商后台创建。
```

## 6. Default Completion Checklist To Tell The User

When finishing a build, the skill should normally remind the user of the next platform step:

```text
如果你要在 VicroCode 上发布：
1. 先去 /project-upload-website 上传项目
2. 再去 /project-manage 管理项目、定价和发布状态
```
