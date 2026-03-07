#!/usr/bin/env python3
"""
github-pr Skill - GitHub 认证模块

管理 GitHub PR 操作所需的用户信息（github_id / deb_email）。
GitHub Token 由 gh CLI 自行管理，本模块不涉及 Token 存储。

配置目录说明：
- 通过命令行参数 --config-dir 指定（推荐）
- 通过环境变量 GITHUB_PR_CONFIG_DIR 指定
- 默认：Docker/OpenClaw 环境 ~/.openclaw/config/github-pr
       Linux/Mac 环境 ~/.config/github-pr

使用方法：
    from auth import get_cached_credentials, login_with_credentials, login_with_cached_credentials

    # 检查是否有缓存
    info = get_cached_credentials()          # {github_id, deb_email, saved_at} 或 None

    # 用缓存信息初始化（同时检查 gh CLI 可用性）
    creds = login_with_cached_credentials()  # {github_id, deb_email} 或 None

    # 首次配置（AI 获得用户确认后调用）
    creds = login_with_credentials("18202781743", "Your Name <you@example.com>")
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================================
# 配置路径
# ============================================================================

def get_config_dir() -> Path:
    """
    获取配置目录。

    优先级：
    1. 命令行参数 --config-dir
    2. 环境变量 GITHUB_PR_CONFIG_DIR
    3. 默认：Docker/OpenClaw 用 ~/.openclaw/config/github-pr
            其他系统用 ~/.config/github-pr
    """
    if "--config-dir" in sys.argv:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config-dir", type=str)
        args, _ = parser.parse_known_args()
        if args.config_dir:
            config_dir = Path(args.config_dir)
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir

    env_dir = os.getenv("GITHUB_PR_CONFIG_DIR")
    if env_dir:
        config_dir = Path(env_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    is_openclaw = Path("/.dockerenv").exists() or os.getenv("OPENCLAW_STATE_DIR") is not None
    if is_openclaw:
        config_dir = Path.home() / ".openclaw" / "config" / "github-pr"
    else:
        config_dir = Path.home() / ".config" / "github-pr"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# ============================================================================
# 凭证存储（github_id / deb_email 不敏感，明文 JSON 即可）
# ============================================================================

class CredentialStore:
    """
    存储 GitHub PR Skill 用户信息（明文 JSON）。

    存储内容：
    - github_id：GitHub 用户名（用于 fork / push）
    - deb_email：Debian changelog 邮箱，格式 "Name <email>"
    """

    def __init__(self):
        self._file = get_config_dir() / "credentials.json"

    def save(self, github_id: str, deb_email: str,
             metadata: Optional[Dict[str, Any]] = None) -> None:
        """保存用户信息"""
        data = {
            "github_id": github_id,
            "deb_email":  deb_email,
            "saved_at":   datetime.now().isoformat(),
            "metadata":   metadata or {},
        }
        self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._file.chmod(0o600)

    def load(self) -> Optional[Dict[str, Any]]:
        """加载用户信息，不存在或格式错误返回 None"""
        if not self._file.exists():
            return None
        try:
            data = json.loads(self._file.read_text())
            if not data.get("github_id") or not data.get("deb_email"):
                return None
            return {
                "github_id": data["github_id"],
                "deb_email":  data["deb_email"],
                "saved_at":   data.get("saved_at", ""),
                "metadata":   data.get("metadata", {}),
            }
        except Exception:
            return None

    def clear(self) -> None:
        if self._file.exists():
            self._file.unlink()


# ============================================================================
# gh CLI 检查
# ============================================================================

def _check_gh_cli() -> Optional[str]:
    """
    检查 gh CLI 状态。

    Returns:
        None 表示正常，字符串表示错误信息。
    """
    if subprocess.run(["which", "gh"], capture_output=True).returncode != 0:
        return "GitHub CLI (gh) 未安装，请运行: sudo apt install gh"
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        return "GitHub CLI (gh) 未登录，请运行: gh auth login"
    return None


# ============================================================================
# 便捷函数（与 uniontech-oa-lib 接口风格一致）
# ============================================================================

def get_cached_credentials() -> Optional[Dict[str, Any]]:
    """
    获取已缓存的用户信息（不含敏感内容，供 AI 判断是否需要重新配置）。

    Returns:
        {github_id, deb_email, saved_at} 或 None（无缓存）
    """
    creds = CredentialStore().load()
    if not creds:
        return None
    return {
        "github_id": creds["github_id"],
        "deb_email":  creds["deb_email"],
        "saved_at":   creds.get("saved_at", "")[:10],
    }


def login_with_credentials(
    github_id: str,
    deb_email: str,
    save_credentials: bool = True,
) -> Dict[str, Any]:
    """
    保存用户信息并检查 gh CLI 可用性（供 AI 在获得用户确认后调用）。

    Args:
        github_id:        GitHub 用户名（如 18202781743）
        deb_email:        Debian changelog 邮箱（如 "Name <email>"）
        save_credentials: 是否持久化到本地缓存

    Returns:
        {github_id, deb_email}

    Raises:
        RuntimeError: gh CLI 未安装或未登录时抛出
    """
    err = _check_gh_cli()
    if err:
        raise RuntimeError(err)

    if save_credentials:
        CredentialStore().save(github_id, deb_email)

    return {"github_id": github_id, "deb_email": deb_email}


def login_with_cached_credentials() -> Optional[Dict[str, Any]]:
    """
    直接使用已缓存的用户信息，无需任何参数。
    若无缓存或 gh CLI 不可用则返回 None，AI 应提示用户配置。

    Returns:
        {github_id, deb_email} 或 None
    """
    creds = CredentialStore().load()
    if not creds:
        return None
    err = _check_gh_cli()
    if err:
        return None
    return {"github_id": creds["github_id"], "deb_email": creds["deb_email"]}


def clear_cached_credentials() -> None:
    """清除已缓存的用户信息（切换账号时使用）"""
    CredentialStore().clear()
