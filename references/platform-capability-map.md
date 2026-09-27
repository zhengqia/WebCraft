# VicroCode 平台能力地图与用户引导

Load this file whenever the user asks "平台能不能做 X"、"这个功能怎么做"、"要不要自己买服务器/买 Key"，or whenever a project needs a secret, a searchable knowledge base, a database, a reusable API, or a published skill. 先判断平台是否已有现成能力，再决定要不要自己写。

## 1. 平台有没有现成能力（先查这张表）

| 用户想要 | 平台能力 | 让用户去哪里创建 | 你只需要向用户索要 | 项目里怎么接 | 令牌 |
| --- | --- | --- | --- | --- | --- |
| 调用需要密钥的第三方 API（支付、短信、地图、OAuth、快递…） | 密钥托管（Credential Vault） | `/credential-vault`（即 `/user-center/my-tokens?tab=credential-vault`） | 托管 API 名称、提供方、完整 base/端点地址、认证方式、稳定的项目内标识（例如 `payment_api`） | 前端：`fetch('__vicro_proxy__/{identifier}/{path}')`；Python 后端：用注入的 `VICRO_BACKEND_INTERNAL_URL` + `VICRO_PROJECT_PROXY_PATH` + `VICRO_PROJECT_PROXY_TOKEN` | 不需要令牌（平台在代理层注入密钥） |
| 调用 AI 模型（文本/图片/视频/嵌入） | AI 模型中心（网关） | `/user-api-center` | 供应商或中转站、协议族、base URL、模型名、能力类型 | `POST /api/gateway/v1/chat/completions`（另有 `/responses`、`/images/generations`、`/images/edits`、`/videos/generations`、`/messages`、`/gemini/...`） | `sk-ant-...` |
| 文档检索、知识问答、资料库 | 知识库 | `/backend-manager/knowledge-bases` | 知识库公开 ID、检索策略（`keyword` / `semantic` / `hybrid` / `hybrid_mmr`）、top-k、`answer_mode`（默认 `json`） | `POST /api/v1/knowledge-bases/{public_id}/query/` | `vco_know_...` |
| 保存订单、会员、配置等结构化数据（不想自己写库） | 独立数据库（SQLite） | `/backend-manager/databases` | 数据库公开 ID、表名、字段与索引需求 | `/api/v1/databases/{public_id}/tables/{table}/records/` | `vco-data-...` |
| 管理项目自带 SQLite（表、行、备份、恢复、上传确认） | 平台项目数据库管理 | `/backend-manager/python/project/{projectId}` | 项目 ID | `/api/python/database/{projectId}/...` | 同源会话（无需令牌） |
| 做一个给别人复用的 HTTP 函数 | API 端点托管 | `/user-center/api-endpoint-hosting` | 输入变量、输出字段、类型、必填项、示例 | 平台调用 `def handler(payload, context)`；使用方按详情页给出的地址调用（`/api/v1/tools/{slug}/invoke/`） | `vco_api_...` |
| 把自己的能力/流程封装成技能上架 | SKILL 开发 | `/user-center/skill-development`（使用者侧 `/user-center/my-skills`，详情页 `/skills/{slug}`） | 技能名、用途、SKILL 包内容、收费声明 | 见 [skill-development-and-publishing.md](skill-development-and-publishing.md) | 使用者用各自令牌 |
| 把网页/Python 项目传上去（含改完自动更新） | 智能部署（agent-deploy） | 无需页面，用脚本 | 一次 `vco-wc-` 令牌；升级已有应用时提供项目 ID | `python scripts/vicrocode_deploy.py sync --dir <project>` | `vco-wc-...` |
| 用户文件上传、预览、配额 | 文件管理器 | `/backend-manager/files` | 需要的文件类型与大小上限 | 平台后端资源接口（同源会话） | 同源会话 |

后台四大模块统一入口：`/user-center/backend`，模块页 `/backend-manager/{knowledge-bases|databases|files|python}`。

## 2. 引导用户的标准动作（照这个说，用户不会走丢）

Use this shape every time a platform resource must be created by the user:

1. **先说清楚为什么**：例如"这个支付密钥不能写在代码里，平台可以帮你托管，代码里只留一个标识。"
2. **给三步点击路径**：打开哪个网址 → 建什么名字 → 复制哪一串字符串给你。例如：
   - 打开 `/credential-vault`；
   - 新建托管 API：名称"支付接口"，地址填 `https://api.example.com/v1`，认证方式选 Bearer，标识填 `payment_api`；
   - 建完不需要把密钥给我，只要告诉我标识是 `payment_api`。
3. **只要标识符，不要密钥**：永远不要让用户把 provider API Key、Bearer、Basic 密码、OAuth secret、HMAC 密钥贴进聊天、源码、日志或截图。
4. **创建完再改代码**：拿到标识/公开 ID 后再替换直连调用，最后跑一次连通性检查。
5. **给失败预案**：常见错误 `403 PROJECT_PROXY_FORBIDDEN`、`409 CREDENTIAL_BINDING_MISSING`、`409 TARGET_RECONSENT_REQUIRED`、`429 PROXY_RATE_LIMIT` 的含义与处理见 [credential-proxy-and-cloning.md](credential-proxy-and-cloning.md)。

知识与数据库的引导话术：

- 知识库："先在 `/backend-manager/knowledge-bases` 建一个知识库并上传资料，等状态变成 `ready`，把它的公开 ID 告诉我，我接到项目里做检索。"
- 数据库："如果要存订单/会员数据，建议用平台的独立数据库：`/backend-manager/databases` 新建，把公开 ID 和表名给我；项目自带的 SQLite 只管项目自己的运行数据。"

## 3. 令牌与权限速查

| 前缀 | 用途 | 创建位置 |
| --- | --- | --- |
| `vco_api_...` | API 工具（端点）调用 | 我的令牌 `/user-center/my-tokens` 或 API 端点托管页 |
| `vco_know_...` | 知识库检索 | 我的令牌（类目选"知识库"） |
| `vco-data-...` | 独立数据库读写 | 我的令牌（类目选"数据库"） |
| `vco-wc-...` | 智能部署（上传/更新/部署） | 我的令牌（类目选"智能部署"，深链 `?create=deploy`） |
| `sk-ant-...` | AI 模型中心调用 | `/user-api-center` 模型中心 |

规则：**一个令牌只属于一个类目**，不要混用；`vco_api_` 与 AI 模型中心的 KEY 完全独立。旧前缀（`sk-wc-`、`vco_YYYYMMDD_`）仍被平台兼容，但新代码一律用上表前缀。

## 4. 运行期契约速查

- 浏览器/静态前端调用托管密钥：`__vicro_proxy__/{identifier}/{upstreamPath}`（相对地址，**不要**加前导斜杠，**不要**写项目 ID 或平台域名）。
- Python 项目调用托管密钥：读环境变量 `VICRO_BACKEND_INTERNAL_URL`、`VICRO_PROJECT_PROXY_PATH`、`VICRO_PROJECT_PROXY_TOKEN`，且**不要**把 token 返回或写日志。
- 项目运行入口：用户可见 `/p/{projectId}/`，Python 实际入口 `/api/python-proxy/{projectId}/`。
- 长任务（模型、转码、爬取、大文件）：必须带 `X-Vicro-Long-Timeout: 1` 或 `__vicro_long_timeout=1`，或改成"启动/查询/取结果"异步三步。
- 单请求上限：约 100 MB，文件数量上限 10000；更大的内容请拆分或走对象存储式的分片上传。

## 5. 平台没有的能力（要说清楚，并给替代方案）

- 平台不会替用户保管他自己的第三方账号密码，也不会用未公开接口去代建资源：托管 API、知识库、数据库、API 端点、技能都必须由**用户在界面里创建**。
- 需要写文件到服务器目录、需要任意端口/协议（如 WebSocket 自建服务、SMTP、Redis 直连）、需要超出单请求体积上限的一次性大上传，都属于不支持范围。
- 遇到不支持的需求，明确告诉用户"平台不支持 X"，再给一条能落地的替代路径（异步任务、分片上传、改用平台托管资源、把密钥托管后直连第三方 HTTPS）。

## 6. 不要做的事

- 不要因为用户说"我要 AI/支付/短信"就让用户自己去注册第三方并写死密钥；先看密钥托管和模型中心。
- 不要把知识库、数据库、托管 API 的密钥或未公开的内部接口当成"项目代码能自动创建"的东西。
- 不要用资源的展示名当 ID；ID 必须是稳定、可读、可长期保留的标识。
- 不要在引导里一次性抛给用户十个页面链接；一次只让用户做一个动作。

## 7. 验收清单

- 项目里每一个外部调用要么走密钥托管、要么走平台令牌，源码中没有任何真实密钥。
- 用户能在平台上看到自己创建的资源（托管 API / 知识库 / 数据库 / API 工具 / 技能），且项目用的是它们的公开 ID。
- 涉及检索/数据库/端点的调用都带了正确类目的令牌，越权或缺失时有可读的错误提示。
- 用户被告知了最终网址与后续在哪里管理（`/project-manage`、`/user-center/...`）。
