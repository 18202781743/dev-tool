#!/usr/bin/env python3
"""
CRP 认证模块 - 复用 OA 凭证，与 uniontech-oa-lib 共享同一套凭证存储

凭证存储目录与 OA 技能一致：
- 环境变量 UNIONTECH_OA_CONFIG_DIR 指定
- 默认：Docker/OpenClaw 环境 ~/.openclaw/config/uniontech-oa
       Linux/Mac 环境 ~/.config/uniontech-oa

CRP 使用 OA 账号登录（loginid/password 相同），但走 CRP 自己的 API 获取 Token。

使用方法：
    from auth import get_cached_credentials, login_with_credentials, login_with_cached_credentials

    # 检查是否有缓存
    info = get_cached_credentials()      # {loginid, username, saved_at} 或 None

    # 用缓存凭证登录 CRP，获取 token
    result = login_with_cached_credentials()  # {loginid, password, token} 或 None

    # 用指定凭证登录（首次配置或切换账号）
    result = login_with_credentials("ut003649", "mypassword")
"""

from __future__ import annotations

import base64
import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import rsa
from cryptography.fernet import Fernet

# ============================================================================
# 配置
# ============================================================================

CRP_BASE_URL = "https://crp.uniontech.com"
HEADERS_JSON = {"Content-Type": "application/json"}

# CRP 登录密码 RSA 公钥（前端 jsencrypt 使用）
_CRP_RSA_PUBKEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCkA9WqirWQII3D8/M9UG8X8ybQ
Ou+cPSNTgR9b4HenJ7A5zSfkXZnetb5q6MmKTJLGCl9MSsHveQPHmLGDG+xw2MlB
w3Yefd/jJ1Cg8pP69wlHRX+wiyh5p8KY55ehFNsQLm3kDGXgVJdtrZn/MiBOlCtE
fe9YvvT0lqy2BtBpaQIDAQAB
-----END PUBLIC KEY-----"""


def get_config_dir() -> Path:
    """
    获取凭证存储目录（与 uniontech-oa-lib 共用同一目录）

    优先级：
    1. 命令行参数 --config-dir
    2. 环境变量 UNIONTECH_OA_CONFIG_DIR
    3. 默认：Docker/OpenClaw 用 ~/.openclaw/config/uniontech-oa
            其他系统用 ~/.config/uniontech-oa
    """
    if "--config-dir" in sys.argv:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config-dir", type=str)
        args, _ = parser.parse_known_args()
        if args.config_dir:
            config_dir = Path(args.config_dir)
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir

    env_dir = os.getenv("UNIONTECH_OA_CONFIG_DIR")
    if env_dir:
        config_dir = Path(env_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    is_openclaw = Path("/.dockerenv").exists() or os.getenv("OPENCLAW_STATE_DIR") is not None
    if is_openclaw:
        config_dir = Path.home() / ".openclaw" / "config" / "uniontech-oa"
    else:
        config_dir = Path.home() / ".config" / "uniontech-oa"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# ============================================================================
# 加密存储（与 uniontech-oa-lib 相同实现，读写同一文件）
# ============================================================================

class CredentialStore:
    """
    加密存储 OA 凭证，与 uniontech-oa-lib 共享同一个 key.bin + default.json。
    CRP 技能直接读取 OA 凭证，无需单独存储。
    """

    def __init__(self):
        config_dir = get_config_dir()
        self._key_file        = config_dir / "key.bin"
        self._credential_file = config_dir / "default.json"
        self._fernet: Optional[Fernet] = None

    def _get_or_create_key(self) -> bytes:
        if self._key_file.exists():
            return self._key_file.read_bytes()
        key = Fernet.generate_key()
        self._key_file.write_bytes(key)
        self._key_file.chmod(0o600)
        return key

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(self._get_or_create_key())
        return self._fernet

    def save_credentials(self, loginid: str, password: str,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        data = {
            "loginid": loginid,
            "password_encrypted": self.fernet.encrypt(
                password.encode("utf-8")
            ).decode("utf-8"),
            "saved_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._credential_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2)
        )
        self._credential_file.chmod(0o600)

    def load_credentials(self) -> Optional[Dict[str, Any]]:
        if not self._credential_file.exists():
            return None
        try:
            data  = json.loads(self._credential_file.read_text())
            pwd   = self.fernet.decrypt(
                data["password_encrypted"].encode("utf-8")
            ).decode("utf-8")
            return {
                "loginid":  data["loginid"],
                "password": pwd,
                "saved_at": data.get("saved_at", ""),
                "metadata": data.get("metadata", {}),
            }
        except Exception:
            return None

    def clear_credentials(self) -> None:
        if self._credential_file.exists():
            self._credential_file.unlink()


# ============================================================================
# CRP 认证工具
# ============================================================================

def _encrypt_password(plain: str) -> str:
    """RSA 公钥加密密码（与 CRP 前端 jsencrypt 行为一致）"""
    pub_key = rsa.PublicKey.load_pkcs1_openssl_pem(_CRP_RSA_PUBKEY_PEM)
    cipher  = rsa.encrypt(plain.encode("utf-8"), pub_key)
    return base64.b64encode(cipher).decode("utf-8")


def _fetch_crp_token(loginid: str, password: str) -> str:
    """
    用 OA 账号登录 CRP，返回 Bearer Token。
    失败时抛出 RuntimeError。
    """
    encrypted_pwd = _encrypt_password(password)
    resp = requests.post(
        f"{CRP_BASE_URL}/api/login",
        headers=HEADERS_JSON,
        json={"userName": loginid, "password": encrypted_pwd},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("Token", "")
    if not token:
        raise RuntimeError("CRP 登录失败：服务器未返回 Token")
    return token


# ============================================================================
# 便捷函数（与 uniontech-oa-lib 接口风格保持一致）
# ============================================================================

def get_cached_credentials() -> Optional[Dict[str, Any]]:
    """
    获取已缓存的凭证摘要（不含密码明文，仅供展示）。
    AI 调用此函数了解是否有缓存，再决定是否向用户询问。

    Returns:
        {loginid, username, saved_at} 或 None（无缓存）
    """
    store = CredentialStore()
    creds = store.load_credentials()
    if not creds:
        return None
    return {
        "loginid":  creds["loginid"],
        "username": creds.get("metadata", {}).get("username", ""),
        "saved_at": creds.get("saved_at", "")[:10],
    }


def login_with_credentials(
    loginid: str,
    password: str,
    save_credentials: bool = True,
) -> Dict[str, Any]:
    """
    用指定凭证登录 CRP（供 AI 在获得用户确认后调用）。

    Args:
        loginid:          OA 登录账号（如 ut003649）
        password:         OA 密码
        save_credentials: 是否持久化凭证缓存

    Returns:
        {loginid, password, token}

    Raises:
        RuntimeError: 登录失败时抛出
    """
    if save_credentials:
        store = CredentialStore()
        store.save_credentials(loginid, password)

    token = _fetch_crp_token(loginid, password)
    return {"loginid": loginid, "password": password, "token": token}


def login_with_cached_credentials() -> Optional[Dict[str, Any]]:
    """
    直接使用已缓存凭证登录 CRP，无需任何参数。
    若无缓存则返回 None，AI 应提示用户提供凭证。

    Returns:
        {loginid, password, token} 或 None
    """
    store = CredentialStore()
    creds = store.load_credentials()
    if not creds:
        return None
    try:
        token = _fetch_crp_token(creds["loginid"], creds["password"])
        return {"loginid": creds["loginid"], "password": creds["password"], "token": token}
    except Exception:
        return None


def clear_cached_credentials() -> None:
    """清除已缓存的凭证（用户选择切换账号时调用）"""
    CredentialStore().clear_credentials()
