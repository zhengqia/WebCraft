# Version And Site Selection

Load this file first.

## 1. Skill Version Rule

This skill is expected to keep evolving.

Current local skill version:

```text
v2026-06-12.01
```

Remote package example:

```text
https://www.vicoco.cn/skills/webcraft.zip
```

Preferred metadata URL example:

```text
https://www.vicoco.cn/skills/webcraft.json
```

Whenever this skill is used, follow this behavior:

1. Check whether a newer version is available from the configured download location or release metadata, if network access is available.
   Preferred method: run `scripts/check_and_install_update.py`.
2. If a newer version exists, tell the user:
   - current local version
   - discovered remote version
   - that the skill can be updated automatically
3. Ask whether to download and install the newer version before continuing substantial work.
4. If the user agrees, download and install the latest package, then continue with the updated skill.
5. If version metadata cannot be checked, say that explicitly and continue with the local version.

Do not silently overwrite a newer installed skill without telling the user.

If multiple updates ship on the same date, use an optional revision suffix such as:

```text
v2026-05-16.1
v2026-05-21.3
```

Treat a higher same-day revision as newer than a lower one.

## 2. Site Flavor Selection

VicroCode has CN and global site flavors. Do not assume one blindly.

Choose in this order:

1. If the user explicitly asks for Chinese, domestic, CN, 中文版, or `vicoco.cn`, use CN mode.
2. If the user explicitly asks for English, global, international, EN, or `vicrocode.com`, use global mode.
3. If the target repo, copy, routes, or task context clearly targets one site, follow that.
4. Otherwise ask the user which one they want before committing to public URLs, login links, or publish guidance.

## 3. Default Link Map

### CN / domestic

```text
Site base: https://www.vicoco.cn
Login: https://www.vicoco.cn/register-login
User center: https://www.vicoco.cn/user-center
Skill package example: https://www.vicoco.cn/skills/webcraft.zip
```

### Global / English

```text
Site base: https://www.vicrocode.com
Login: https://www.vicrocode.com/register-login
User center: https://www.vicrocode.com/user-center
```

## 4. Why This Matters

The site flavor affects:

1. login and user-center links
2. upload and publish guidance copy
3. user-facing copy language

## 5. Remote Metadata JSON Shape

Prefer publishing a JSON file beside the zip package.

Example fields:

```json
{
  "skill_name": "webcraft",
  "version": "v2026-05-21.3",
  "manifest_schema": "vicrocode.skill.release.v1",
  "published_at": "2026-05-16T00:00:00Z",
  "zip_url": "https://www.vicoco.cn/skills/webcraft.zip",
  "zip_sha256": "",
  "size_bytes": 0,
  "site_flavor": "cn",
  "release_notes": "Add post-success coin deduction guidance."
}
```

If the JSON exists, prefer it over guessing a version from the zip payload.
