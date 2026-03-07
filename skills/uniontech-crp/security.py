#!/usr/bin/env python3
"""
uniontech-crp Skill - 安全工具模块
提供输入验证功能
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    message: str = ""
    sanitized_value: Any = None


class InputValidator:
    """输入验证器"""

    @classmethod
    def validate_package_name(cls, name: str) -> ValidationResult:
        """验证包名（字母、数字、连字符、加号）"""
        if not name:
            return ValidationResult(False, "包名不能为空")
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.+\-]*$', name):
            return ValidationResult(False, f"包名格式无效: {name!r}")
        return ValidationResult(True, sanitized_value=name)

    @classmethod
    def validate_topic(cls, topic: str) -> ValidationResult:
        """验证 CRP 主题名（拒绝 shell 注入字符）"""
        if not topic:
            return ValidationResult(False, "topic 不能为空")
        for ch in [';', '&', '|', '$', '`', ' ', '\n']:
            if ch in topic:
                return ValidationResult(False, f"topic 包含非法字符: {ch!r}")
        return ValidationResult(True, sanitized_value=topic)

    @classmethod
    def validate_branch(cls, branch: str) -> ValidationResult:
        """验证分支名"""
        if not branch:
            return ValidationResult(False, "分支名不能为空")
        for ch in [';', '&', '|', '$', '`', ' ', '\n']:
            if ch in branch:
                return ValidationResult(False, f"分支名包含非法字符: {ch!r}")
        return ValidationResult(True, sanitized_value=branch)

    @classmethod
    def validate_file_path(cls, path: str) -> ValidationResult:
        """验证文件路径（禁止路径遍历）"""
        if not path:
            return ValidationResult(False, "路径不能为空")
        if ".." in path:
            return ValidationResult(False, "路径不能包含 ..")
        for ch in [';', '&', '|', '$', '`', '\n']:
            if ch in path:
                return ValidationResult(False, f"路径包含非法字符: {ch!r}")
        return ValidationResult(True, sanitized_value=path)
