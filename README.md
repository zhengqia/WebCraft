<img width="1152" height="360" alt="logo" src="https://github.com/user-attachments/assets/fc5b63ef-7fff-403f-a980-0a7839ba2fde" />

## SKILL简介
一句话开发并上传到VicroCode环境，不再烦技术选型和各种费用。

您不需要考虑技术选型，不需要考虑服务器、部署方法、备案、申请支付通道等，只需发挥您的创造力，开发出让客户喜欢的应用即可。

几乎没什么成本，也没什么技术负担。

支持安装在Claude Code/Codex/OpenClaw/Hermes/Coze等多种智能体中。

新版 WebCraft 支持 VicroCode 密钥托管与克隆开发：编程助手可以把项目中的 API Key、Bearer Token、OAuth2、HMAC 等认证改为平台代理调用，使用稳定的项目内标识码，克隆后由每位使用者绑定自己的密钥，无需修改源码或项目 ID。技能还包含克隆前敏感文件/硬编码密钥预检。

WebCraft v101 新增 API 端点托管开发规范：明确 `handler(payload, context)`、输入输出 Schema、受限工作区文件、国内镜像依赖安装、密钥托管、安全扫描、测试、版本审核和 `vco_api_` 调用流程，避免把 API 工具误做成 Flask 网站或访问服务器目录。

WebCraft v102 新增知识库、数据库与后台资源管理规范：覆盖 LanceDB 多格式解析、图片描述/原图模式、Excel 转 Markdown、AI 自动分段与计费、网页爬虫库、知识库 API、SQLite 一致性备份、统一账号配额、管理员封锁申诉，以及暗色和移动端验收要求。详见 `references/knowledge-database-management.md`。

WebCraft v103 新增 VicroCode 新手平台手册：Aether 视觉默认值、知识库/数据库/文件/Python 管理器配置、模型中心与托管 API 路由、运行期持久化、上传/发布/克隆流程、SEO 与多语言验收清单。详见 `references/vicrocode-platform-playbook.md`。

WebCraft v104 新增「运行期数据文件」交付隔离规范：用 JSON / JS / CSV 存数据的项目必须在项目根放 `vicrocode.project.json` 声明 `runtime_data`、上传副本必须是空模板、运行期写入必须落在平台 runtime 目录，并新增 `scripts/scan_runtime_data.py` 一键预检。这样开发者用 AI 生成的项目可以一键上传，作者的数据不会随克隆或源码包交付给他人。详见 `references/runtime-data-and-cloning-isolation.md`。

WebCraft v105 新增「智能体一键上传与自动部署」：开发智能体用「我的令牌 - 智能部署」生成的 `vco-wc-` 令牌即可免浏览器登录上传/更新项目（标题、描述、TDK 自动生成），Python 项目可一键自动部署并返回网址，部署失败会返回结构化原因与日志尾部；本地记录文件 `.vicrocode/deploy.json` 永不上传、也不随源码交付。详见 `references/agent-deploy.md`。

WebCraft v106 统一令牌前缀：智能部署令牌由 `sk-wc-` 调整为 `vco-wc-`，数据库令牌由 `vco_YYYYMMDD_` 调整为 `vco-data-`（旧前缀令牌继续可用）。


## About SKILL
Develop and upload to VicroCode in one sentence — no more stressing over tech stack decisions and endless costs.

You don't need to worry about technology choices, servers, deployment methods, ICP filing, or payment gateway applications. Just unleash your creativity and build applications your customers will love.

Virtually no cost, and virtually no technical burden.

Supports installation in Claude Code, Codex, OpenClaw, Hermes, Coze, and other agents.

WebCraft also supports VicroCode Credential Vault and clone-ready development. Coding assistants can replace API keys, bearer tokens, OAuth2, HMAC, and other direct authentication with the platform proxy, use stable in-project identifiers, and let each clone owner bind a separate credential without source or project-ID changes. A local clone-secret preflight is included.

WebCraft v101 adds a dedicated API Endpoint Hosting contract covering `handler(payload, context)`, input/output schemas, root-only workspace files, domestic-mirror dependency setup, credential protection, security checks, testing, version review, and consumer `vco_api_` invocation. This prevents hosted tools from being incorrectly built as Flask websites or from touching server directories.

WebCraft v102 adds knowledge-base, database, and admin resource management rules: LanceDB multi-format parsing, image description/original modes, Excel-to-Markdown, AI segmentation and billing, web crawling libraries, knowledge-base APIs, consistent SQLite backups, unified account quotas, admin block appeals, plus dark-mode and mobile acceptance checks. See `references/knowledge-database-management.md`.

WebCraft v103 adds the VicroCode beginner platform playbook: Aether visual defaults, knowledge-base/database/file/Python manager setup, model-center and hosted-API routing, runtime persistence, upload/publish/clone flow, SEO and multilingual acceptance checks. See `references/vicrocode-platform-playbook.md` and `references/knowledge-database-management.md`.

WebCraft v104 adds the runtime data delivery isolation contract: projects storing records in JSON / JS / CSV files must declare every runtime data path in `vicrocode.project.json`, upload empty templates instead of real records, and resolve runtime writes to the platform runtime directory. A new `scripts/scan_runtime_data.py` preflight catches undeclared data files, so an AI-built project can be uploaded in one click without leaking the author's data to clone recipients or source buyers. See `references/runtime-data-and-cloning-isolation.md`.

WebCraft v105 adds one-click agent upload and auto-deploy: a `vco-wc-` 智能部署 token lets the coding agent upload or update a project without a browser login (title, description and TDK are generated automatically), deploy Python projects online with automatic retries and structured failure diagnosis, and report the run URL. The local `.vicrocode/deploy.json` record is never uploaded or delivered. See `references/agent-deploy.md`.

WebCraft v106 unifies token prefixes: the agent-deploy token moves from `sk-wc-` to `vco-wc-`, and the standalone-database token from `vco_YYYYMMDD_` to `vco-data-` (legacy prefixes keep working).


## 安装方法
复制这个给Agent：
```
请帮我安装这个技能：https://github.com/zhengqia/WebCraft
```

### Installation
Copy this to your Agent:
```
Please install this skill: https://github.com/zhengqia/WebCraft
```


## VicroCode介绍
VicroCode是一个轻量级应用部署代码托管平台，告别昂贵服务器和复杂的部署！

您可免费部署您的应用，迅速验证项目可行性。

支持HTML+JS+CSS+Python+SQLite，提供网页应用管理器、Python管理器、SQLite数据库在线管理器等实用工具，零门槛轻松操作。免复杂配置实现代码快速部署发布，搭建优质代码流通生态，助力开发者实现技术变现，让每段代码都能迸发商业与实用价值。

开箱即用，免部署、免服务器、免备案、免申请支付通道，支持接入AI智能体、通用管理系统、游戏等多种项目。

并提供多种变现通道，你免费上传，我帮你卖！

国内站：https://www.vicoco.cn

海外站：https://www.vicrocode.com

<img width="300" height="300" alt="企微2" src="https://github.com/user-attachments/assets/1d67afca-d8a9-4e9e-8758-969182a5f785" />

联系我

<img width="300" height="300" alt="qrcode_for_gh_be0e834eba94_344" src="https://github.com/user-attachments/assets/f42a4517-0066-42b0-ba9b-93a5ec202e1c" />

关注公众号


## About VicroCode
VicroCode is a lightweight application deployment and code hosting platform — say goodbye to expensive servers and complicated deployments!

Deploy your applications for free and quickly validate project viability. It supports HTML + JS + CSS + Python + SQLite, and comes with practical tools like a web app manager, Python manager, and SQLite database online manager — zero barrier to entry.

Achieve rapid code deployment and publishing without complex configuration, build a quality code distribution ecosystem, and help developers monetize their skills — letting every piece of code unleash its commercial and practical value.

Ready to use out of the box — no deployment, no servers, no ICP filing, no payment gateway applications required. Supports integrating AI agents, general-purpose management systems, games, and more.

It also offers multiple monetization channels — you upload for free, we help you sell!

website:https://www.vicrocode.com

