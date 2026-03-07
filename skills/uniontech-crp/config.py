#!/usr/bin/env python3
"""
uniontech-crp Skill - 配置模块

管理 CRP 打包相关的行为配置（非认证信息）。
配置以明文 JSON 存储，AI 可以读取和修改。

配置目录说明：
- 通过环境变量 UNIONTECH_CRP_CONFIG_DIR 指定
- 默认：Docker/OpenClaw 环境 ~/.openclaw/config/uniontech-crp
       Linux/Mac 环境 ~/.config/uniontech-crp

使用方法：
    from config import get_config, save_config, get_config_dir
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================================
# 配置路径（与 auth.py 共享同一目录）
# ============================================================================

def get_config_dir() -> Path:
    """
    获取 CRP 行为配置目录（与凭证目录相同，即 OA 配置目录）。

    优先级：
    1. 环境变量 UNIONTECH_OA_CONFIG_DIR（与 OA 技能保持一致）
    2. 默认：Docker/OpenClaw 用 ~/.openclaw/config/uniontech-oa
            其他系统用 ~/.config/uniontech-oa
    """
    env_dir = os.getenv("UNIONTECH_OA_CONFIG_DIR")
    if env_dir:
        config_dir = Path(env_dir)
    elif Path("/.dockerenv").exists() or os.getenv("OPENCLAW_STATE_DIR") is not None:
        config_dir = Path.home() / ".openclaw" / "config" / "uniontech-oa"
    else:
        config_dir = Path.home() / ".config" / "uniontech-oa"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# ============================================================================
# 默认配置
# ============================================================================

DEFAULTS: Dict[str, Any] = {
    "archs":          "amd64;arm64;loong64;sw64;mips64el",
    "topic_type":     "test",
    "branch_id":      123,        # snipe 分支 ID
    "default_branch": "upstream/master",
    "saved_at":       "",
}


# ============================================================================
# 配置存储
# ============================================================================

class SkillConfigStore:
    """
    CRP Skill 行为配置存储（明文 JSON）。

    存储内容（均有默认值，不配置也能正常工作）：
    - archs：打包架构（分号分隔）
    - topic_type：主题类型（test / release）
    - branch_id：snipe 分支 ID
    - default_branch：默认打包分支
    """

    def __init__(self):
        self._file = get_config_dir() / "crp-config.json"

    def save(self, **kwargs) -> None:
        """保存配置（只更新传入字段）"""
        data = self.load_raw()
        data.update(kwargs)
        data["saved_at"] = datetime.now().isoformat()
        self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_raw(self) -> Dict[str, Any]:
        """加载原始配置（文件不存在时返回空字典）"""
        if not self._file.exists():
            return {}
        try:
            return json.loads(self._file.read_text())
        except Exception:
            return {}

    def get(self, key: str, fallback: Any = None) -> Any:
        """获取单个配置项，不存在时返回 DEFAULTS 中的默认值"""
        data = self.load_raw()
        if key in data:
            return data[key]
        if fallback is not None:
            return fallback
        return DEFAULTS.get(key)

    def as_dict(self) -> Dict[str, Any]:
        """返回完整配置（合并默认值）"""
        result = dict(DEFAULTS)
        result.update(self.load_raw())
        return result


# ============================================================================
# 便捷函数
# ============================================================================

def get_config() -> Dict[str, Any]:
    """
    获取完整配置（含默认值）。
    AI 调用此函数了解当前配置，向用户展示或决定是否需要修改。

    Returns:
        {archs, topic_type, branch_id, default_branch, saved_at}
    """
    return SkillConfigStore().as_dict()


def save_config(
    archs: Optional[str] = None,
    topic_type: Optional[str] = None,
    branch_id: Optional[int] = None,
    default_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """
    保存配置（AI 在用户明确要求修改时调用，只更新传入字段）。

    Returns:
        更新后的完整配置
    """
    store = SkillConfigStore()
    updates: Dict[str, Any] = {}
    if archs         is not None: updates["archs"]          = archs
    if topic_type    is not None: updates["topic_type"]      = topic_type
    if branch_id     is not None: updates["branch_id"]       = branch_id
    if default_branch is not None: updates["default_branch"] = default_branch
    if updates:
        store.save(**updates)
    return store.as_dict()
