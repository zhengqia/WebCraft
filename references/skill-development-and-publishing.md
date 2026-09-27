# VicroCode SKILL 开发与发布

Load this file whenever the user wants to turn a capability into a VicroCode SKILL, publish or update a skill in the skill marketplace, or ship a remote self-update package (zip + json) for this skill.

## 1. 三者不要混在一起

| 交付形态 | 给谁用 | 入口 | 运行方式 |
| --- | --- | --- | --- |
| 网站项目（HTML / Python） | 最终用户打开网页 | `/user-center` 项目体系 | `/p/{id}` 或 `/api/python-proxy/{id}/` |
| API 端点（API 工具） | 其他程序按 HTTP 调用 | `/user-center/api-endpoint-hosting` | 平台调用 `handler(payload, context)` |
| SKILL 包 | 其他智能体/编程助手安装使用 | `/user-center/skill-development` | 智能体读 `SKILL.md` 与 `references/`，按需运行 `scripts/` |

不要把三者的文件、路由、发布规则混写在一个包里；也不要为了做技能而生成 Flask 服务或 `/p/{id}` 站点。

## 2. 导入与开发方式

平台支持：

1. 上传 ZIP 或选择本地 SKILL 文件夹；
2. 输入 GitHub / GitLab / Gitee 仓库地址；
3. 输入公开 ZIP 下载地址；
4. 在线手工开发；
5. AI 辅助开发。

约束：

- 远程导入第一期只接受**公开 HTTPS 来源**，服务端会限制文件大小、重定向次数与超时，并阻止私网/回环/链路本地/云元数据地址；
- 远程版本必须记录来源 URL、平台类型、branch/tag、最终 commit SHA、下载时间、包 SHA-256、导入人与扫描结果；
- **发布版本必须锁定 commit 或内容哈希**，不允许每次运行都跟随可变分支，避免供应链漂移。

## 3. SKILL 包规范（平台会逐条校验）

- 根目录必须有 `SKILL.md`；
- YAML frontmatter 至少包含 `name` 与 `description`；
- `name` 只能是小写字母、数字、连字符，最长 64 字符，且与目录名一致；
- 推荐提供 `agents/openai.yaml`；
- 可选目录：`scripts/`、`references/`、`assets/`；
- `SKILL.md` 要短、用渐进披露，建议少于 500 行，长内容拆进 `references/`；
- 不鼓励放与执行无关的 README、CHANGELOG 或重复文档；
- `scripts/` 里的 Python 与 API 端点一样，**不能在 Web 宿主进程里运行**；
- 同一份内容不要重复打包大文件。

平台校验范围：目录结构、frontmatter、命名、链接、文件编码、危险压缩包、重复大文件、脚本语法、依赖、敏感信息、收费声明。结论分三档：阻断错误、审核警告、建议优化。**阻断错误必须先修完再提交审核。**

智能体在打包前应自查：包内有没有令牌、内网地址、真实密钥、`.env`、个人隐私数据；`scripts/` 是否只依赖标准库或有声明的依赖；`SKILL.md` 的 description 是否写清了"什么时候用这个技能"。

## 4. 收费必须披露（四类分开写）

SKILL 详情页要分别展示：

1. **SKILL 商品价格**：免费，或购买该包需支付的一次性金币；
2. **运行时内置收费**：安装后使用某些步骤会额外调用的收费服务；
3. **AI 模型费用**：使用者用自己的模型中心 Key 产生；
4. **第三方费用**：外部服务商收取，平台不保证价格。

内置收费声明要用结构化数据（不是只写在介绍里），每项建议包含：

- 收费服务名称与提供方；
- VicroCode API 端点 ID/版本，或第三方域名；
- 触发步骤、是否可选；
- 计费方式：免费 / 固定金币 / 按第三方规则；
- 当前价格、价格查询地址、最后核验时间；
- 使用者需要提供哪一类 Key；
- 是否存在免费替代路径。

购买确认要给出总览，例如：

```text
本 SKILL 售价：20 金币（一次购买）
运行时内置收费：调用"文档解析 API"，2 金币/次
模型费用：使用你选择的 AI 模型中心 Key 另行计费
第三方费用：无
```

**不能用"免费 SKILL"掩盖核心流程必须调用收费端点的事实。**

管理员对待审版本会跑内置收费自动检测（扫描 `SKILL.md`、frontmatter、`agents/`、`scripts/`、`references/`、配置与依赖文件，并做静态 + Runner 动态检查），状态含义：

| 状态 | 含义 | 发布处理 |
| --- | --- | --- |
| `none` | 无收费线索且声明无收费 | 继续其它审核 |
| `declared` | 与作者声明一致 | 披露后可审核 |
| `suspected` | 疑似收费但信息不足 | 必须人工确认 |
| `mismatch` | 与声明或价格不一致 | 阻止发布，要求修正 |
| `blocked` | 隐藏凭证、恶意绕过或禁止的网络行为 | 阻止发布并安全审核 |
| `scan_failed` | 扫描器故障 | 不允许当作"未发现"，需重试或人工处理 |

收费目标、调用方式或价格变化时，技能需要重新审核，并提醒已购买用户。

## 5. 购买、下载与发布

- 免费 SKILL 也会建立领取记录，用于版本通知与滥用控制；
- 收费购买走账本事务，作者 90%、平台 10%（比例后台可配）；
- 下载不暴露真实存储路径，使用短期/一次性/限次下载令牌；
- 下载包按**已审核版本**生成，并包含结构化收费声明；
- 已发布版本不可原地修改：修改产生新草稿/新版本；"最新稳定版"别名可切回已审核版本用于回滚。

## 6. 远程自更新发布物（只需两个文件）

技能（含本技能自身）对外分发只需要：

```text
<site>/skills/{skill}.zip
<site>/skills/{skill}.json
```

中文站示例：`https://www.vicoco.cn/skills/webcraft.zip`、`https://www.vicoco.cn/skills/webcraft.json`（站点源码里同时保留 `SKILLS/webcraft.{zip,json}` 与 `public/skills/` 两份，发布前端后即可对外访问）。

JSON 采用固定 schema `vicrocode.skill.release.v1`：

```json
{
  "skill_name": "webcraft",
  "version": "v109",
  "manifest_schema": "vicrocode.skill.release.v1",
  "published_at": "2026-09-27T00:00:00Z",
  "zip_url": "https://www.vicoco.cn/skills/webcraft.zip",
  "zip_sha256": "",
  "size_bytes": 0,
  "site_flavor": "cn",
  "release_notes": "本次更新说明"
}
```

打包（本技能自带脚本，纯标准库）：

```powershell
python SKILLS/webcraft/scripts/build_release_bundle.py `
  --output-dir SKILLS `
  --site-base https://www.vicoco.cn `
  --site-flavor cn `
  --release-notes "本次更新说明"
```

发版时必须同步更新的四处：

1. `VERSION`（例如 `v109`）；
2. `marketplace.json` 的 `version`（可顺带更新 description / tags）；
3. `references/version-and-site-selection.md` 里的 "Current local skill version"（技能靠它做自我更新检查，写着旧版本会误判）；
4. `README.md` 的版本更新说明段落（中英各一段）。

然后把生成的 `webcraft.zip` / `webcraft.json` 复制到站点静态分发目录（本仓库为 `public/skills/`），并同步本地已安装副本（例如 `~/.agents/skills/webcraft`）。

## 7. 智能体在"发布技能"任务里的分工

1. 先判断用户要的是技能包，还是 API 端点 / 网站项目；
2. 帮用户整理包结构（`SKILL.md` 精简 + `references/` 拆分 + `scripts/` 只留必需）；
3. 写清 frontmatter：`name`（小写连字符）与 `description`（写"什么时候用"，不是广告词）；
4. 跑敏感信息与密钥自查，去掉内网地址与真实凭据；
5. 核对收费声明与实际调用是否一致（有收费端点就必须声明）；
6. 在 `/user-center/skill-development` 导入 ZIP 或仓库 → 填版本号 → 上传截图 → 提交审核；
7. 审核通过后确认版本号、兼容平台、文件清单与收费披露；
8. 需要远程自更新时，按第 6 节打包并同步四处版本信息。

## 8. 验收清单

- `SKILL.md` 有合法 frontmatter，`name` 与目录名一致，正文简短且渐进披露；
- 包内无密钥、无内网地址、无隐私数据、无无用大文件；
- `scripts/` 里的脚本能在不依赖 Web 宿主进程的前提下运行；
- 收费声明与包内真实调用一致，且说明"谁收费、多少、什么时候收"；
- 发布物锁定 commit/内容哈希，并记录了扫描结果；
- 站点分发目录里的 zip 与 json 版本、sha256、size 一致，且本地已安装副本已同步。
