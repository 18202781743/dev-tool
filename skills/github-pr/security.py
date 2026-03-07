#!/usr/bin/env python3
"""
github-pr Skill - 安全工具模块
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
    def validate_org(cls, org: str) -> ValidationResult:
        """验证 GitHub 组织名"""
        if not org:
            return ValidationResult(False, "组织名不能为空")
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*$', org):
            return ValidationResult(False, f"组织名格式无效: {org!r}")
        return ValidationResult(True, sanitized_value=org)

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
    def validate_version(cls, version: str) -> ValidationResult:
        """验证版本号（如 6.7.36 或 6.7.36-1）"""
        if not version:
            return ValidationResult(False, "版本号不能为空")
        if not re.match(r'^\d+(\.\d+)+([-+~]\S*)?$', version):
            return ValidationResult(False, f"版本号格式无效: {version!r}")
        return ValidationResult(True, sanitized_value=version)

    @classmethod
    def validate_reviewer(cls, reviewer: str) -> ValidationResult:
        """验证 GitHub 用户名（审阅者）"""
        if not reviewer:
            return ValidationResult(False, "审阅者不能为空")
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*$', reviewer):
            return ValidationResult(False, f"用户名格式无效: {reviewer!r}")
        return ValidationResult(True, sanitized_value=reviewer)
