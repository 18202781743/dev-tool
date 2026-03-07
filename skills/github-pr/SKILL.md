---
name: github-pr
description: Use when creating GitHub PRs to bump Debian package versions, merging tag PRs, querying the latest tag, triggering auto-release workflows, or listing GitHub projects for linuxdeepin packages.
---

# GitHub PR (Tag Bump)

## Overview

通过内置 Python 脚本直接调用 `git` / `gh` CLI，完成 Debian 包版本 bump、changelog 更新、fork PR 创建等操作。**不依赖任何外部 dev-tool 二进制。**

**依赖：**
- `gh` CLI（已登录：`gh auth login`）
- `git` CLI
- `dch`（`devscripts` 包，用于更新 debian/changelog）

## When to Use

- "给 `deepin-terminal` 打一个新版本的 tag PR"
- "合并 `dtkcommon` 的 tag PR"
- "查一下 `dtkgui` 的最新 tag"
- "触发 `deepin-terminal` 的 Auto Release"
- "搜索一下 linuxdeepin 下有哪些 deepin-screen 相关项目"

## Authentication

github_id / deb_email 存储在独立配置文件，gh Token 由 gh CLI 自行管理。

```python
from auth import get_cached_credentials, login_with_credentials, login_with_cached_credentials

# 检查是否有缓存
info = get_cached_credentials()          # {github_id, deb_email, saved_at} 或 None

# 用缓存信息初始化
creds = login_with_cached_credentials()  # {github_id, deb_email} 或 None

# 首次配置（AI 获得用户确认后调用）
creds = login_with_credentials("18202781743", "YeShanShan <yeshanshan@uniontech.com>")
```

配置目录：`~/.config/github-pr/`（OpenClaw：`~/.openclaw/config/github-pr/`）

## Quick Reference

| 操作 | 方法 | 必填参数 |
|------|------|---------|
| 打 Tag PR | `client.tag(name, org, branch)` | name |
| 合并 PR | `client.merge(name, org)` | name |
| 查最新 Tag | `client.lasttag(name, org)` | name |
| 测试模式（不推送）| `client.test(name, org, branch)` | name |
| 触发 Auto Release | `client.release(name, org)` | name |
| 搜索项目 | `client.projects(org, name_filter)` | — |

## Implementation

```python
from auth import login_with_cached_credentials
from git_pr import GitPRClient

creds = login_with_cached_credentials()
if not creds:
    raise RuntimeError("未找到用户信息缓存或 gh CLI 未就绪")

client = GitPRClient(creds["github_id"], creds["deb_email"])

# 打 Tag PR（版本号自动递增）
result = client.tag("dtkcommon", org="linuxdeepin", branch="master")
# result: {success, msg, pr_url, tag}

# 指定版本号
result = client.tag("dtkcommon", version="6.7.36", reviewers=["reviewer1"])
```

## How It Works

1. **准备仓库** — 若本地缓存（`~/.cache/git-tag-dir/`）无该仓库，自动 `git clone` + fork 初始化
2. **更新 changelog** — `dch -v <tag>` 写入提交记录，`dch -r` 完成签名
3. **提交并推送** — `git commit` → `git push github dev-changelog -f`
4. **创建 PR** — `gh pr create --head <github_id>:dev-changelog`

## Common Mistakes

| 现象 | 原因 | 解决 |
|------|------|------|
| `gh` 未就绪 | 未登录 | `gh auth login` |
| `dch` 未找到 | 未安装 | `sudo apt install devscripts` |
| fork 不存在 | 首次使用 | skill 自动创建 fork |
| PR 重复创建 | 上次未合并 | 先调用 `merge()` |
