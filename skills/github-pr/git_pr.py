#!/usr/bin/env python3
"""
github-pr Skill - Git Tag / PR 操作

完整内联 git-tag.py 逻辑，不依赖任何外部二进制工具（仅使用 git / gh CLI）。

用法：
  python git_pr.py tag     --name deepin-terminal --org linuxdeepin --branch master
  python git_pr.py merge   --name deepin-terminal --org linuxdeepin
  python git_pr.py lasttag --name deepin-terminal --org linuxdeepin
  python git_pr.py test    --name deepin-terminal --org linuxdeepin --branch master
  python git_pr.py release --name deepin-terminal --org linuxdeepin
  python git_pr.py projects [--name keyword] [--org linuxdeepin]

Exit Codes:
  0 - 成功
  1 - 一般错误
  2 - 参数错误
  3 - 认证错误
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from auth import get_cached_credentials, login_with_credentials, login_with_cached_credentials
from security import InputValidator, ValidationResult

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR   = 1
EXIT_USAGE   = 2
EXIT_AUTH    = 3

DEFAULT_ORG    = "linuxdeepin"
DEFAULT_BRANCH = "master"
DEFAULT_REPO_ROOT = "~/.cache/git-tag-dir"


def error_response(error_type: str, message: str, suggestion: str = None, **extra) -> str:
    resp = {"error": error_type, "message": message}
    if suggestion:
        resp["suggestion"] = suggestion
    resp.update(extra)
    return json.dumps(resp, ensure_ascii=False, indent=2)


def _ok(msg: str, **kw) -> Dict[str, Any]:
    return {"success": True, "msg": msg, **kw}


def _err(msg: str, **kw) -> Dict[str, Any]:
    return {"success": False, "msg": msg, **kw}


# ============================================================================
# Changelog / Version 工具（内联自 git-tag.py）
# ============================================================================

def _find_commit_by_blame(changelog_version: str) -> Optional[str]:
    """通过 git blame 定位 changelog 版本对应的提交 hash"""
    # 方法1: 提交信息 grep
    try:
        cl = subprocess.run(
            ["dpkg-parsechangelog", "--format", "rfc822"],
            capture_output=True, text=True,
        )
        if cl.returncode == 0:
            cl_data: Dict[str, str] = {}
            for line in cl.stdout.split("\n"):
                if ":" in line and not line.startswith(" "):
                    k, v = line.split(":", 1)
                    cl_data[k.strip()] = v.strip()

            for change_line in cl_data.get("Changes", "").strip().split("\n"):
                change_line = change_line.strip()
                if change_line.startswith("*"):
                    pattern = change_line[1:].strip()
                    if len(pattern) > 10:
                        r = subprocess.run(
                            ["git", "log", "--grep", pattern, "--format=%H", "-n", "1"],
                            capture_output=True, text=True,
                        )
                        if r.returncode == 0 and r.stdout.strip():
                            return r.stdout.strip()
    except Exception:
        pass

    # 方法2: 作者 + changelog 内容匹配
    try:
        m = re.search(r"<([^>]+)>", subprocess.run(
            ["dpkg-parsechangelog", "--show-field", "Maintainer"],
            capture_output=True, text=True,
        ).stdout.strip())
        if m:
            email = m.group(1)
            r = subprocess.run(
                ["git", "log", "--author", email, "--format=%H", "-n", "10", "--since=1 week ago"],
                capture_output=True, text=True,
            )
            for commit in r.stdout.strip().split("\n"):
                if not commit:
                    continue
                files_r = subprocess.run(
                    ["git", "show", "--name-only", commit],
                    capture_output=True, text=True,
                )
                if "debian/changelog" in files_r.stdout:
                    show_r = subprocess.run(
                        ["git", "show", commit, "debian/changelog"],
                        capture_output=True, text=True,
                    )
                    if f"({changelog_version})" in show_r.stdout:
                        return commit
    except Exception:
        pass

    # 方法3: 字符串匹配 blame
    try:
        blame_r = subprocess.run(
            ["git", "blame", "--porcelain", "debian/changelog"],
            capture_output=True, text=True,
        )
        if blame_r.returncode == 0:
            lines = blame_r.stdout.split("\n")
            current_commit = None
            for line in lines:
                if line and not line.startswith("\t") and " " in line:
                    parts = line.split(" ")
                    if len(parts[0]) == 40 and all(c in "0123456789abcdef" for c in parts[0].lower()):
                        current_commit = parts[0]
                elif line.startswith("\t") and current_commit:
                    content = line[1:]
                    if f"({changelog_version})" in content and (
                        "unstable" in content or "stable" in content
                    ):
                        return current_commit
    except Exception:
        pass

    return None


def _find_last_tagged_version() -> Optional[str]:
    """查找最新已打 tag 的版本，优先从 debian/changelog 读取"""
    try:
        r = subprocess.run(
            "dpkg-parsechangelog --show-field Version",
            shell=True, capture_output=True, text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            version = r.stdout.strip()
            commit = _find_commit_by_blame(version)
            return commit or version
    except Exception:
        pass

    r = subprocess.run(
        ["git", "tag", "-l", "--sort=-version:refname"],
        capture_output=True, text=True,
    )
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split("\n")[0]
    return None


def _fetch_last_git_tag() -> Optional[str]:
    r = subprocess.run(
        "git describe --tags --abbrev=0",
        shell=True, capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _auto_increment_version(last_tag: str) -> str:
    """根据 last_tag 自动递增 patch 版本号"""
    base = last_tag

    # last_tag 是 commit hash → 从 changelog 取版本
    if len(last_tag) == 40 and all(c in "0123456789abcdef" for c in last_tag.lower()):
        r = subprocess.run(
            "dpkg-parsechangelog --show-field Version",
            shell=True, capture_output=True, text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            base = r.stdout.strip()
        else:
            git_tag = _fetch_last_git_tag()
            if git_tag:
                base = git_tag
            else:
                raise ValueError("无法确定基础版本号")

    epoch = ""
    version_part = base
    if ":" in base:
        epoch_part, version_part = base.split(":", 1)
        epoch = epoch_part + ":"

    parts = version_part.split(".")
    if len(parts) != 3:
        raise ValueError(f"版本号格式错误 '{version_part}'，应为 major.minor.patch")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    return f"{epoch}{major}.{minor}.{patch + 1}"


def _get_commit_log(last_tag: str, project_tag: str) -> str:
    """获取 last_tag..HEAD 的提交摘要，用于 changelog"""
    r = subprocess.run(
        ["git", "log", "--pretty=format:%s", "--no-merges", f"{last_tag}..HEAD"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() or f"Release {project_tag}"


# ============================================================================
# Git / GitHub 操作
# ============================================================================

def _git(*args, cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=cwd, check=check,
    )


def _gh(*args, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh"] + list(args),
        capture_output=True, text=True, check=check,
    )


def _prepare_repo(project_name: str, project_org: str, github_id: str,
                  project_branch: str, repo_root: str) -> str:
    """clone / 初始化仓库，返回仓库路径"""
    root = os.path.expanduser(repo_root)
    os.makedirs(root, exist_ok=True)

    repo_dir = os.path.join(root, project_name)
    if not os.path.exists(repo_dir):
        subprocess.run(
            ["git", "clone",
             f"https://github.com/{project_org}/{project_name}.git",
             repo_dir],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            f"git remote add github https://github.com/{github_id}/{project_name}.git",
            shell=True, check=True, capture_output=True, text=True, cwd=repo_dir,
        )
        _gh("repo", "set-default", f"{project_org}/{project_name}")

    return repo_dir


def _init_tag_pr(repo_dir: str, project_branch: str, deb_email: str,
                 project_tag: str, auto_tag: bool) -> str:
    """
    在 repo_dir 中：fetch → reset → checkout dev-changelog → 更新 changelog → commit。
    返回实际使用的 project_tag。
    """
    os.environ["DEBEMAIL"] = deb_email

    subprocess.run("git fetch origin", shell=True, check=True,
                   capture_output=True, text=True, cwd=repo_dir)
    subprocess.run(["git", "reset", "--hard", f"origin/{project_branch}"],
                   check=True, capture_output=True, text=True, cwd=repo_dir)
    subprocess.run(f"git checkout -B dev-changelog origin/{project_branch}",
                   shell=True, check=True, capture_output=True, text=True, cwd=repo_dir)

    old_cwd = os.getcwd()
    os.chdir(repo_dir)
    try:
        last_tag = _find_last_tagged_version()
        if auto_tag:
            project_tag = _auto_increment_version(last_tag or "0.0.0")
        commit_log = _get_commit_log(last_tag or "", project_tag)

        # 用 dch 更新 changelog
        with subprocess.Popen(
            ["xargs", "-d", "\n", "-I", "{}", "dch", "-v", project_tag, "{}"],
            stdin=subprocess.PIPE, text=True, cwd=repo_dir,
        ) as p:
            p.communicate(input=commit_log)
        subprocess.run("dch -r ''", shell=True, check=True,
                       capture_output=True, text=True, cwd=repo_dir)

        subprocess.run(
            ["git", "commit", "-a", "-m",
             f"chore: bump version to {project_tag}\n\nupdate changelog to {project_tag}"],
            check=True, capture_output=True, text=True, cwd=repo_dir,
        )
    finally:
        os.chdir(old_cwd)

    return project_tag


def _create_tag_pr(repo_dir: str, project_name: str, project_org: str,
                   github_id: str, project_branch: str,
                   project_tag: str, reviewers: List[str]) -> str:
    """push dev-changelog 到 fork 并创建 PR，返回 PR URL"""
    # 确保 fork 存在
    if subprocess.run(
        ["gh", "repo", "view", f"{github_id}/{project_name}"],
        capture_output=True,
    ).returncode != 0:
        subprocess.run(
            ["gh", "repo", "fork", f"{project_org}/{project_name}", "--clone=false"],
            check=True, capture_output=True, text=True,
        )

    subprocess.run(
        "git push github dev-changelog -f",
        shell=True, check=True, capture_output=True, text=True, cwd=repo_dir,
    )

    pr_cmd = [
        "gh", "pr", "create",
        "--repo", f"{project_org}/{project_name}",
        "--head", f"{github_id}:dev-changelog",
        "--base", project_branch,
        "--title", f"chore: bump version to {project_tag}",
        "--body",  f"update changelog to {project_tag}",
    ]
    for r in reviewers:
        pr_cmd += ["--reviewer", r]

    r = subprocess.run(pr_cmd, check=True, capture_output=True, text=True)
    return r.stdout.strip()


# ============================================================================
# GitPRClient - 对外接口
# ============================================================================

class GitPRClient:
    """
    Git Tag / PR 操作客户端。

    所有参数均由调用方显式传入，无隐式配置文件读取。
    """

    def __init__(self, github_id: str, deb_email: str,
                 repo_root: str = DEFAULT_REPO_ROOT):
        self.github_id = github_id
        self.deb_email = deb_email
        self.repo_root = repo_root

    # ------------------------------------------------------------------
    # 公开操作
    # ------------------------------------------------------------------

    def tag(
        self,
        name: str,
        org: str = DEFAULT_ORG,
        branch: str = DEFAULT_BRANCH,
        version: Optional[str] = None,
        reviewers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建 changelog bump commit 并提 PR"""
        for val, fn in [
            (name,   InputValidator.validate_package_name),
            (org,    InputValidator.validate_org),
            (branch, InputValidator.validate_branch),
        ]:
            r: ValidationResult = fn(val)
            if not r.valid:
                return _err(r.message)
        if version:
            r = InputValidator.validate_version(version)
            if not r.valid:
                return _err(r.message)

        try:
            repo_dir = _prepare_repo(name, org, self.github_id, branch, self.repo_root)
            auto_tag = version is None
            used_tag = _init_tag_pr(repo_dir, branch, self.deb_email,
                                     version or "", auto_tag)
            pr_url = _create_tag_pr(repo_dir, name, org, self.github_id,
                                     branch, used_tag, reviewers or [])
            return _ok(f"PR 已创建: {pr_url}", pr_url=pr_url, tag=used_tag)
        except subprocess.CalledProcessError as e:
            return _err(e.stderr.strip() or str(e))
        except Exception as e:
            return _err(str(e))

    def merge(
        self,
        name: str,
        org: str = DEFAULT_ORG,
    ) -> Dict[str, Any]:
        """合并 dev-changelog PR"""
        for val, fn in [(name, InputValidator.validate_package_name),
                        (org,  InputValidator.validate_org)]:
            r = fn(val)
            if not r.valid:
                return _err(r.message)
        try:
            result = subprocess.run(
                ["gh", "pr", "merge",
                 "--repo", f"{org}/{name}",
                 "-r", f"{self.github_id}:dev-changelog"],
                capture_output=True, text=True, check=True,
            )
            # 尝试获取 PR URL
            pr_url = ""
            info = subprocess.run(
                ["gh", "pr", "view",
                 "--repo", f"{org}/{name}",
                 f"{self.github_id}:dev-changelog",
                 "--json", "url"],
                capture_output=True, text=True,
            )
            if info.returncode == 0:
                pr_url = json.loads(info.stdout).get("url", "")
            return _ok(f"PR 已合并{': ' + pr_url if pr_url else ''}", pr_url=pr_url)
        except subprocess.CalledProcessError as e:
            return _err(e.stderr.strip() or str(e))

    def lasttag(
        self,
        name: str,
        org: str = DEFAULT_ORG,
    ) -> Dict[str, Any]:
        """查询仓库最新 Tag"""
        for val, fn in [(name, InputValidator.validate_package_name),
                        (org,  InputValidator.validate_org)]:
            r = fn(val)
            if not r.valid:
                return _err(r.message)
        try:
            repo_dir = _prepare_repo(name, org, self.github_id,
                                      DEFAULT_BRANCH, self.repo_root)
            old_cwd = os.getcwd()
            os.chdir(repo_dir)
            try:
                subprocess.run("git fetch origin", shell=True,
                               capture_output=True, text=True)
                last_tag = _find_last_tagged_version()
            finally:
                os.chdir(old_cwd)
            if last_tag:
                return _ok(last_tag, tag=last_tag)
            return _err("未找到任何 Tag")
        except subprocess.CalledProcessError as e:
            return _err(e.stderr.strip() or str(e))

    def test(
        self,
        name: str,
        org: str = DEFAULT_ORG,
        branch: str = DEFAULT_BRANCH,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        测试模式：在本地执行 changelog 更新和 commit，打印 diff，不推送 / 不建 PR。
        """
        for val, fn in [
            (name,   InputValidator.validate_package_name),
            (org,    InputValidator.validate_org),
            (branch, InputValidator.validate_branch),
        ]:
            r = fn(val)
            if not r.valid:
                return _err(r.message)
        try:
            repo_dir = _prepare_repo(name, org, self.github_id, branch, self.repo_root)
            auto_tag = version is None
            used_tag = _init_tag_pr(repo_dir, branch, self.deb_email,
                                     version or "", auto_tag)
            diff = subprocess.run(
                "git diff HEAD^ HEAD | cat",
                shell=True, capture_output=True, text=True, cwd=repo_dir,
            )
            return _ok(f"[测试模式] tag={used_tag}，未推送",
                       tag=used_tag, diff=diff.stdout)
        except subprocess.CalledProcessError as e:
            return _err(e.stderr.strip() or str(e))
        except Exception as e:
            return _err(str(e))

    def release(
        self,
        name: str,
        org: str = DEFAULT_ORG,
    ) -> Dict[str, Any]:
        """触发 GitHub Auto Release workflow"""
        for val, fn in [(name, InputValidator.validate_package_name),
                        (org,  InputValidator.validate_org)]:
            r = fn(val)
            if not r.valid:
                return _err(r.message)

        repo_name = f"{org}/{name}"
        # 提取邮箱地址
        m = re.search(r"<([^>]+)>", self.deb_email)
        email = m.group(1) if m else self.deb_email.strip()

        try:
            subprocess.run(
                ["gh", "repo", "set-default", repo_name],
                capture_output=True, text=True,
            )
            r = subprocess.run(
                ["gh", "workflow", "run", "Auto Release",
                 "--repo", repo_name,
                 "-F", f"email={email}"],
                capture_output=True, text=True, check=True,
            )
            return _ok(
                f"Auto Release workflow 已触发，查看: https://github.com/{repo_name}/actions"
            )
        except subprocess.CalledProcessError as e:
            return _err(e.stderr.strip() or str(e))

    def projects(
        self,
        org: str = DEFAULT_ORG,
        name_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """搜索组织下的项目，按最近更新时间排序"""
        r = InputValidator.validate_org(org)
        if not r.valid:
            return _err(r.message)

        jq_filter = (
            f'.[] | select(.name | test("{name_filter}"; "i")) | {{name:.name,pushedAt:.pushedAt,url:.url}}'
            if name_filter
            else '.[] | {name:.name,pushedAt:.pushedAt,url:.url}'
        )
        try:
            result = subprocess.run(
                ["gh", "repo", "list", org,
                 "--limit", "100",
                 "--json", "name,pushedAt,url",
                 "--jq",   jq_filter],
                capture_output=True, text=True, check=True,
            )
            repos = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    try:
                        repos.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            repos.sort(key=lambda x: x.get("pushedAt", ""), reverse=True)
            return _ok(f"找到 {len(repos)} 个项目", projects=repos)
        except subprocess.CalledProcessError as e:
            return _err(e.stderr.strip() or str(e))


# ============================================================================
# CLI 入口
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub PR / Tag 操作")
    parser.add_argument("action", choices=[
        "tag", "merge", "lasttag", "test", "release", "projects"
    ])
    parser.add_argument("--name",     help="包名")
    parser.add_argument("--org",      default=DEFAULT_ORG,    help="GitHub 组织")
    parser.add_argument("--branch",   default=DEFAULT_BRANCH, help="分支")
    parser.add_argument("--version",  help="指定版本号（不填则自动递增）")
    parser.add_argument("--reviewer", action="append", dest="reviewers",
                        help="审阅者（可多次指定）")
    parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT,
                        help="本地仓库缓存根目录")
    args = parser.parse_args()

    # 认证
    creds = login_with_cached_credentials()
    if not creds:
        print(error_response(
            "auth_error",
            "未找到用户信息缓存或 gh CLI 未就绪",
            "请确认 gh auth login 已完成，并提供 github_id 和 deb_email"
        ), file=sys.stderr)
        return EXIT_AUTH

    client = GitPRClient(
        github_id=creds["github_id"],
        deb_email=creds["deb_email"],
        repo_root=args.repo_root,
    )

    try:
        if args.action == "tag":
            if not args.name:
                print(error_response("usage_error", "--name 必填"), file=sys.stderr)
                return EXIT_USAGE
            result = client.tag(args.name, args.org, args.branch, args.version, args.reviewers)

        elif args.action == "merge":
            if not args.name:
                print(error_response("usage_error", "--name 必填"), file=sys.stderr)
                return EXIT_USAGE
            result = client.merge(args.name, args.org)

        elif args.action == "lasttag":
            if not args.name:
                print(error_response("usage_error", "--name 必填"), file=sys.stderr)
                return EXIT_USAGE
            result = client.lasttag(args.name, args.org)

        elif args.action == "test":
            if not args.name:
                print(error_response("usage_error", "--name 必填"), file=sys.stderr)
                return EXIT_USAGE
            result = client.test(args.name, args.org, args.branch, args.version)

        elif args.action == "release":
            if not args.name:
                print(error_response("usage_error", "--name 必填"), file=sys.stderr)
                return EXIT_USAGE
            result = client.release(args.name, args.org)

        elif args.action == "projects":
            result = client.projects(args.org, args.name)

    except Exception as e:
        print(error_response("error", str(e)), file=sys.stderr)
        return EXIT_ERROR

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_SUCCESS if result.get("success") else EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
