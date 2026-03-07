---
name: uniontech-crp
description: Use when packing CRP packages, querying CRP projects/topics/instances/branches, or generating release documents for linuxdeepin via the CRP API.
---

# Uniontech CRP Pack

## Overview

直接调用 CRP HTTP API（`https://crp.uniontech.com`）管理打包流程，不依赖任何外部二进制工具。

认证与 OA 技能（`uniontech-oa-lib`）**共用同一套凭证存储**（`~/.config/uniontech-oa/` 或 `~/.openclaw/config/uniontech-oa/`），无需单独配置 CRP 账号。

**依赖：**
- `requests`（HTTP 调用）
- `cryptography`（凭证 Fernet 加密）
- `rsa`（CRP 登录密码 RSA 加密）
- `openpyxl`（`gendoc` 生成转测文档时需要）

## When to Use

- "给 `yss-dde-test` 主题打一个 `deepin-terminal` 的包"
- "查一下 `yss-dde-test` 主题下已打包的列表"
- "测试打包 `deepin-terminal`（不实际提交）"
- "生成 `yss-dde-test` 的转测申请单"
- "查一下有没有 deepin-terminal 这个 CRP 项目"

## Authentication

CRP 使用 OA 同一套账号（loginid/password），凭证与 OA 技能共用。

```python
from auth import get_cached_credentials, login_with_credentials, login_with_cached_credentials

# 检查是否有缓存（不含密码）
info = get_cached_credentials()  # {loginid, username, saved_at} 或 None

# 用缓存凭证登录 CRP，获取 token
cred = login_with_cached_credentials()  # {loginid, password, token} 或 None

# 首次配置（AI 获得用户确认后调用）
cred = login_with_credentials("ut003649", "mypassword")
# {loginid, password, token}
```

凭证存储目录：`~/.config/uniontech-oa/`（OpenClaw：`~/.openclaw/config/uniontech-oa/`）

## Skill Config

行为配置存储在 `~/.config/uniontech-oa/crp-config.json`，均有默认值。

```python
from config import get_config, save_config

cfg = get_config()
# {archs, topic_type, branch_id, default_branch}

save_config(default_branch="upstream/master")
```

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `archs` | `amd64;arm64;loong64;sw64;mips64el` | 打包架构 |
| `topic_type` | `test` | 主题类型 |
| `branch_id` | `123` | snipe 分支 ID |
| `default_branch` | `upstream/master` | 默认打包分支 |

## Quick Reference

| 操作 | 方法 | 必填参数 |
|------|------|---------|
| 打包 | `client.pack(topic, name)` | topic, name |
| 测试（不提交）| `client.test(topic, name)` | topic, name |
| 查询主题 | `client.topics(keyword)` | keyword |
| 查询项目 | `client.projects(name)` | — |
| 查询已打包列表 | `client.instances(topic)` | topic |
| 查询分支 | `client.branches(topic, name)` | topic, name |
| 生成转测文档 | `client.gendoc(topic)` | topic |

## Implementation

```python
from auth import login_with_cached_credentials
from crp import CRPClient

# 1. 用 OA 缓存凭证登录 CRP，获取 token
cred = login_with_cached_credentials()
if not cred:
    raise RuntimeError("无凭证缓存，请提供 OA 账号和密码")

# 2. 创建客户端（注入 token）
client = CRPClient(cred["token"])

# 3. 执行操作
result = client.pack("yss-dde-test", "deepin-terminal", branch="upstream/master")
# result: {success, msg, ...}
```

## Build Status

| 状态 | 含义 |
|------|------|
| `UPLOAD_OK` | ✅ 打包成功 |
| `APPLYING` | 🟡 打包中 |
| `UPLOADING` | 🟡 上传中 |
| `UPLOAD_GIVEUP` | ❌ 打包失败 |
| `APPLY_FAILED` | ❌ 申请失败 |

## Common Mistakes

| 现象 | 原因 | 解决 |
|------|------|------|
| 无凭证缓存 | 首次使用或 OA 技能未配置 | AI 引导提供 OA 账号密码 |
| topic 不存在 | 名称错误 | `client.topics(keyword)` 查询 |
| gendoc 无模板 | 未放置模板文件 | 放置 `crp-gendoc.xlsx` 到配置目录 |
