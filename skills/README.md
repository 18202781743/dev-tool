# dev-tool Skills

将 dev-tool 核心功能封装为两个独立的 OpenClaw Skill，供 AI 助手通过自然语言驱动打包、打 Tag、查询等操作。

## 目录结构

```
skills/
├── README.md
├── github-pr/
│   ├── SKILL.md             # OpenClaw Skill 描述（触发条件 & 用法）
│   ├── auth.py              # 凭证存储（github_id / deb_email），gh CLI 状态检查
│   ├── git_pr.py            # 全部 Git Tag / PR 逻辑（内联自 git-tag.py）
│   └── security.py          # 输入验证（包名、分支、org、版本号）
└── uniontech-crp/
    ├── SKILL.md             # OpenClaw Skill 描述（触发条件 & 用法）
    ├── auth.py              # 凭证存储（OA loginid / password，Fernet 加密）
    ├── config.py            # 行为配置（archs / topic_type / branch_id 等）
    ├── crp.py               # 全部 CRP API 逻辑（直接调用 crp.uniontech.com）
    └── security.py          # 输入验证（包名、主题名、分支、文件路径）
```

## 设计原则

- **零外部二进制依赖**：两个 skill 均内联原始逻辑，不调用 `dev-tool` 可执行文件
  - `github-pr`：调用 `git` / `gh` CLI
  - `uniontech-crp`：直接调用 CRP HTTP API（`https://crp.uniontech.com`）
- **参数由用户提供**：所有操作参数明确传入，不从配置文件读取隐含默认值
- **认证模块独立**：各 skill 有自己的 `auth.py`，提供统一的 4 个便捷函数
- **无交互原则**：缺凭证/环境问题返回 `None` 或抛 `RuntimeError`，由 AI 引导用户修复
- **安全验证**：每个 skill 独立维护 `security.py`，校验包名、分支名、主题名等
- **结果格式统一**：`{success: bool, msg: str, ...}`

## Auth 模块接口（两个 skill 统一风格）

```python
from auth import (
    get_cached_credentials,        # 返回凭证摘要（不含密码），供 AI 判断是否需要重新配置
    login_with_credentials,        # 用指定凭证登录并缓存（AI 获得用户确认后调用）
    login_with_cached_credentials, # 用缓存凭证自动登录，无缓存返回 None
    clear_cached_credentials,      # 清除缓存（切换账号时使用）
)
```

### github-pr 凭证

| 字段 | 说明 |
|------|------|
| `github_id` | GitHub 用户名（用于 fork / push） |
| `deb_email` | Debian changelog 邮箱，格式 `Name <email>` |

存储：`~/.config/github-pr/credentials.json`（明文 JSON，字段本身不敏感）

### uniontech-crp 凭证

复用 OA 账号（loginid / password），与 `uniontech-oa-lib` **共用同一套凭证存储**。

存储：`~/.config/uniontech-oa/default.json`（Fernet 加密）+ `key.bin`

## 安装

```bash
# 部署到 OpenClaw workspace
cp -r skills/github-pr   ~/.openclaw/workspace/skills/
cp -r skills/uniontech-crp ~/.openclaw/workspace/skills/
```

## 依赖

### github-pr

```bash
sudo apt install gh devscripts   # gh CLI + dch
gh auth login                    # 登录 GitHub
pip install requests             # HTTP 库
```

### uniontech-crp

```bash
pip install requests cryptography rsa   # HTTP / 加密 / RSA 密码加密
pip install openpyxl                    # 可选，仅 gendoc 命令需要
```

## 快速参考

### github-pr

```python
from auth import login_with_cached_credentials
from git_pr import GitPRClient

creds = login_with_cached_credentials()   # {github_id, deb_email}
client = GitPRClient(creds["github_id"], creds["deb_email"])

client.tag("dtkcommon", org="linuxdeepin", branch="master")   # 打 Tag PR（版本自动递增）
client.merge("dtkcommon", org="linuxdeepin")                  # 合并 PR
client.lasttag("dtkcommon", org="linuxdeepin")                # 查最新 Tag
client.test("dtkcommon", org="linuxdeepin", branch="master")  # 测试模式（不推送）
client.release("dtkcommon", org="linuxdeepin")                # 触发 Auto Release
client.projects(org="linuxdeepin", name_filter="deepin")      # 搜索项目
```

### uniontech-crp

```python
from auth import login_with_cached_credentials
from crp import CRPClient

cred = login_with_cached_credentials()   # {loginid, password, token}
client = CRPClient(cred["token"])

client.pack("yss-dde-test", "dtkcommon-v25", branch="upstream/master")  # 打包
client.test("yss-dde-test", "dtkcommon-v25")                            # 测试（不提交）
client.topics("yss")                                                     # 查询主题
client.projects("dtkcommon")                                             # 查询项目
client.instances("yss-dde-test")                                         # 查已打包列表（含 build_url）
client.branches("yss-dde-test", "dtkcommon-v25")                        # 查可用分支
client.gendoc("yss-dde-test")                                            # 生成转测文档
```

### CRP 打包状态说明

| 状态 | 含义 | build_url |
|------|------|-----------|
| `UPLOAD_OK` | ✅ 打包成功 | 无（不需要） |
| `APPLYING` | 🟡 打包中 | shuttle 链接 |
| `UPLOADING` | 🟡 上传中 | shuttle 链接 |
| `UPLOAD_GIVEUP` | ❌ 打包失败 | shuttle 链接（可查日志）|
| `APPLY_FAILED` | ❌ 申请失败 | shuttle 链接 |
| `UNKNOWN` | ⏳ 刚提交，等待调度 | shuttle 链接 |

打包失败时 `instances()` 返回的 `build_url` 即为 shuttle 日志链接，格式：
```
https://shuttle.uniontech.com/#/tasks/task?taskid=<build_id>
```
