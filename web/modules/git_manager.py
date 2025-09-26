import subprocess
import requests
import json
import os
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .config_manager import config_manager

class GitManager:
    """Git标签管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.github_api_base = "https://api.github.com"
    
    def _run_command(self, cmd: List[str], cwd: str = None) -> Dict[str, Any]:
        """执行命令"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timeout',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def _get_github_headers(self) -> Dict[str, str]:
        """获取GitHub API请求头"""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        # 添加GitHub token如果配置了
        try:
            git_config = config_manager.get_git_config()
            token = git_config.get('auth', {}).get('githubToken', '')
            if token:
                headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            self.logger.warning(f"Failed to get GitHub token: {e}")
        
        return headers
    
    def get_org_repos(self, org: str = None, name_filter: str = "") -> List[Dict[str, Any]]:
        """获取组织下的仓库列表"""
        try:
            if not org:
                config = config_manager.get_git_config()
                org = config.get('params', {}).get('projectOrg', 'linuxdeepin')
            
            url = f"{self.github_api_base}/orgs/{org}/repos"
            params = {
                'type': 'all',
                'sort': 'updated',
                'direction': 'desc',
                'per_page': 100
            }
            
            # 设置代理
            git_config = config_manager.get_git_config()
            proxy = git_config.get('auth', {}).get('proxy', '')
            proxies = None
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            response = requests.get(
                url,
                headers=self._get_github_headers(),
                params=params,
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            
            repos = response.json()
            
            # 如果有名称过滤器，进行模糊匹配
            if name_filter:
                repos = [r for r in repos if name_filter.lower() in r.get('name', '').lower()]
            
            return repos
            
        except Exception as e:
            self.logger.error(f"Get org repos failed: {str(e)}")
            return []
    
    def get_repo_commits(self, org: str, repo: str, branch: str = 'master') -> List[Dict[str, Any]]:
        """获取仓库提交历史"""
        try:
            url = f"{self.github_api_base}/repos/{org}/{repo}/commits"
            params = {
                'sha': branch,
                'per_page': 10
            }
            
            # 设置代理
            git_config = config_manager.get_git_config()
            proxy = git_config.get('auth', {}).get('proxy', '')
            proxies = None
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            response = requests.get(
                url,
                headers=self._get_github_headers(),
                params=params,
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Get repo commits failed: {str(e)}")
            return []
    
    def get_repo_tags(self, org: str, repo: str) -> List[Dict[str, Any]]:
        """获取仓库标签列表"""
        try:
            url = f"{self.github_api_base}/repos/{org}/{repo}/tags"
            params = {'per_page': 20}
            
            # 设置代理
            git_config = config_manager.get_git_config()
            proxy = git_config.get('auth', {}).get('proxy', '')
            proxies = None
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            response = requests.get(
                url,
                headers=self._get_github_headers(),
                params=params,
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Get repo tags failed: {str(e)}")
            return []
    
    def get_latest_tag_from_commits(self, org: str, repo: str) -> Dict[str, Any]:
        """
        获取最新标签信息（基于提交历史，类似git describe --tags --abbrev=0的逻辑）
        返回标签信息和对应的提交SHA
        """
        try:
            # 获取提交历史
            commits = self.get_repo_commits(org, repo)
            if not commits:
                return {'tag': '0.0.0', 'commit_sha': '', 'found': False}
            
            # 获取所有标签
            tags = self.get_repo_tags(org, repo)
            if not tags:
                return {'tag': '0.0.0', 'commit_sha': '', 'found': False}
            
            # 遍历提交历史，找到第一个有标签的提交
            for commit in commits:
                commit_sha = commit.get('sha', '')
                # 检查这个提交是否有标签
                for tag in tags:
                    tag_commit_sha = tag.get('commit', {}).get('sha', '')
                    if commit_sha == tag_commit_sha:
                        tag_name = tag.get('name', '')
                        self.logger.debug(f"Found tag {tag_name} at commit {commit_sha[:8]}")
                        return {
                            'tag': tag_name,
                            'commit_sha': tag_commit_sha,
                            'found': True,
                            'tag_info': tag
                        }
            
            # 如果没有找到匹配的提交，使用最新的版本号格式的标签
            version_pattern = r'^\d+\.\d+\.\d+$'
            version_tags = []
            
            for tag in tags:
                tag_name = tag.get('name', '')
                if re.match(version_pattern, tag_name):
                    version_tags.append(tag)
            
            if version_tags:
                # 按版本号排序，获取最新版本
                def version_key(tag):
                    tag_name = tag.get('name', '0.0.0')
                    try:
                        parts = tag_name.split('.')
                        return (int(parts[0]), int(parts[1]), int(parts[2]))
                    except (ValueError, IndexError):
                        return (0, 0, 0)
                
                version_tags.sort(key=version_key, reverse=True)
                latest_version_tag = version_tags[0]
                return {
                    'tag': latest_version_tag.get('name', '0.0.0'),
                    'commit_sha': latest_version_tag.get('commit', {}).get('sha', ''),
                    'found': True,
                    'tag_info': latest_version_tag
                }
            
            # 最后退化到第一个标签
            first_tag = tags[0]
            return {
                'tag': first_tag.get('name', '0.0.0'),
                'commit_sha': first_tag.get('commit', {}).get('sha', ''),
                'found': True,
                'tag_info': first_tag
            }
            
        except Exception as e:
            self.logger.error(f"Get latest tag from commits failed: {str(e)}")
            return {'tag': '0.0.0', 'commit_sha': '', 'found': False}
    
    def get_latest_tag(self, org: str, repo: str) -> str:
        """获取最新标签（保持向后兼容）"""
        result = self.get_latest_tag_from_commits(org, repo)
        return result.get('tag', '0.0.0')
    
    def generate_next_tag(self, current_tag: str) -> str:
        """生成下一个标签版本号"""
        # 解析版本号
        version_pattern = r'(\d+)\.(\d+)\.(\d+)'
        match = re.match(version_pattern, current_tag)
        
        if match:
            major, minor, patch = map(int, match.groups())
            # 默认递增patch版本
            return f"{major}.{minor}.{patch + 1}"
        else:
            return "1.0.0"
    
    def create_changelog(self, org: str, repo: str, branch: str = 'master') -> str:
        """生成changelog"""
        try:
            commits = self.get_repo_commits(org, repo, branch)
            if not commits:
                return "No recent commits found"
            
            changelog_lines = []
            for commit in commits[:5]:  # 只取最近5个提交
                commit_msg = commit.get('commit', {}).get('message', '').split('\n')[0]
                commit_date = commit.get('commit', {}).get('author', {}).get('date', '')
                changelog_lines.append(f"  * {commit_msg} ({commit_date[:10]})")
            
            return '\n'.join(changelog_lines)
            
        except Exception as e:
            self.logger.error(f"Create changelog failed: {str(e)}")
            return "Failed to generate changelog"
    
    def create_tag_pr(self, org: str, repo: str, tag: str, 
                     branch: str = 'master', reviewers: List[str] = None) -> Dict[str, Any]:
        """创建标签PR"""
        try:
            config = config_manager.get_git_config()
            github_id = config.get('auth', {}).get('githubID', '')
            deb_email = config.get('auth', {}).get('debEmail', '')
            
            if not github_id or not deb_email:
                return {'error': 'GitHub ID or Debian email not configured'}
            
            # 这里需要使用gh CLI来创建PR
            # 首先检查gh CLI是否可用
            gh_check = self._run_command(['gh', '--version'])
            if not gh_check['success']:
                return {'error': 'GitHub CLI (gh) not available'}
            
            # 获取项目根目录
            project_root = config.get('params', {}).get('projectRootDir', '~/.cache/web-dev-tool-git')
            project_root = os.path.expanduser(project_root)
            repo_dir = os.path.join(project_root, repo)
            
            # 确保目录存在
            os.makedirs(project_root, exist_ok=True)
            
            # 克隆或更新仓库
            if not os.path.exists(repo_dir):
                clone_cmd = ['git', 'clone', f'https://github.com/{org}/{repo}.git', repo_dir]
                clone_result = self._run_command(clone_cmd)
                if not clone_result['success']:
                    return {'error': f'Failed to clone repository: {clone_result["stderr"]}'}
            else:
                # 更新仓库
                pull_result = self._run_command(['git', 'pull'], cwd=repo_dir)
                if not pull_result['success']:
                    return {'error': f'Failed to update repository: {pull_result["stderr"]}'}
            
            # 生成changelog
            changelog = self.create_changelog(org, repo, branch)
            
            # 创建新分支
            branch_name = f"tag-{tag}"
            create_branch_cmd = ['git', 'checkout', '-b', branch_name]
            branch_result = self._run_command(create_branch_cmd, cwd=repo_dir)
            if not branch_result['success']:
                # 如果分支已存在，切换到该分支
                checkout_result = self._run_command(['git', 'checkout', branch_name], cwd=repo_dir)
                if not checkout_result['success']:
                    return {'error': f'Failed to create/checkout branch: {branch_result["stderr"]}'}
            
            # 这里应该实际修改debian/changelog文件，但为了简化，我们创建一个PR描述
            pr_title = f"chore: release {tag}"
            pr_body = f"""Release {tag}

Recent changes:
{changelog}

Signed-off-by: {deb_email}"""
            
            # 使用gh CLI创建PR
            if not reviewers:
                reviewers = config.get('params', {}).get('projectReviewers', [])
            
            create_pr_cmd = ['gh', 'pr', 'create', 
                           '--title', pr_title,
                           '--body', pr_body,
                           '--base', branch]
            
            if reviewers:
                create_pr_cmd.extend(['--reviewer', ','.join(reviewers)])
            
            pr_result = self._run_command(create_pr_cmd, cwd=repo_dir)
            
            if pr_result['success']:
                # 解析PR URL
                pr_url = pr_result['stdout'].strip()
                return {
                    'success': True,
                    'pr_url': pr_url,
                    'tag': tag,
                    'changelog': changelog
                }
            else:
                return {'error': f'Failed to create PR: {pr_result["stderr"]}'}
            
        except Exception as e:
            self.logger.error(f"Create tag PR failed: {str(e)}")
            return {'error': str(e)}
    
    def get_pr_status(self, org: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """获取PR状态"""
        try:
            url = f"{self.github_api_base}/repos/{org}/{repo}/pulls/{pr_number}"
            
            # 设置代理
            git_config = config_manager.get_git_config()
            proxy = git_config.get('auth', {}).get('proxy', '')
            proxies = None
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            response = requests.get(
                url,
                headers=self._get_github_headers(),
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Get PR status failed: {str(e)}")
            return {}
    
    def get_watch_repos_status(self) -> List[Dict[str, Any]]:
        """获取关注仓库的状态"""
        try:
            config = config_manager.get_git_config()
            watch_repos = config.get('params', {}).get('watchRepos', [])
            org = config.get('params', {}).get('projectOrg', 'linuxdeepin')
            
            repos_status = []
            for repo_name in watch_repos:
                self.logger.info(f"Processing repo: {org}/{repo_name}")
                
                # 获取最新提交
                commits = self.get_repo_commits(org, repo_name)
                latest_commit = commits[0] if commits else {}
                
                # 获取标签信息（使用基于提交历史的智能算法）
                tag_info = self.get_latest_tag_from_commits(org, repo_name)
                latest_tag = tag_info.get('tag', '')
                tag_commit_sha = tag_info.get('commit_sha', '')
                
                if tag_info.get('found', False):
                    self.logger.debug(f"Latest tag for {repo_name}: {latest_tag} (commit: {tag_commit_sha[:8] if tag_commit_sha else 'N/A'})")
                else:
                    self.logger.debug(f"No tags found for {repo_name}, using default")
                
                # 计算自上次标签以来的提交数量
                commits_since_tag = 0
                commits_since_tag_list = []
                
                if tag_commit_sha and commits:
                    for commit in commits:
                        if commit.get('sha') == tag_commit_sha:
                            break
                        commits_since_tag += 1
                        commits_since_tag_list.append(commit)
                elif not tags and commits:
                    # 如果没有标签，显示所有提交
                    commits_since_tag = len(commits)
                    commits_since_tag_list = commits
                
                # 预测下一个标签
                next_tag = self.generate_next_tag(latest_tag or "0.0.0")
                
                repo_status = {
                    'name': repo_name,
                    'org': org,
                    'latest_commit': latest_commit,
                    'latest_tag': latest_tag or "无标签",
                    'next_tag': next_tag,
                    'commits_since_tag': commits_since_tag,
                    'commits_since_tag_list': commits_since_tag_list[:10],  # 只保留前10个提交用于显示
                    'last_updated': latest_commit.get('commit', {}).get('author', {}).get('date', ''),
                    'tag_commit_sha': tag_commit_sha
                }
                repos_status.append(repo_status)
            
            # 按最后更新时间排序
            repos_status.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
            return repos_status
            
        except Exception as e:
            self.logger.error(f"Get watch repos status failed: {str(e)}")
            return []
    
    def get_commits_since_tag(self, org: str, repo: str, tag_sha: str) -> List[Dict[str, Any]]:
        """获取自指定标签以来的提交列表"""
        try:
            # 使用GitHub API的比较功能
            url = f"{self.github_api_base}/repos/{org}/{repo}/compare/{tag_sha}...HEAD"
            
            # 设置代理
            git_config = config_manager.get_git_config()
            proxy = git_config.get('auth', {}).get('proxy', '')
            proxies = None
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            response = requests.get(
                url,
                headers=self._get_github_headers(),
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            
            comparison = response.json()
            return comparison.get('commits', [])
            
        except Exception as e:
            self.logger.error(f"Get commits since tag failed: {str(e)}")
            return []
    
    def get_commits_since_tag_detailed(self, org: str, repo: str, tag: str) -> List[Dict[str, Any]]:
        """获取自指定标签以来的详细提交信息"""
        try:
            # 首先获取标签信息
            tags = self.get_repo_tags(org, repo)
            tag_commit_sha = None
            
            for tag_info in tags:
                if tag_info.get('name') == tag:
                    tag_commit_sha = tag_info.get('commit', {}).get('sha')
                    break
            
            if not tag_commit_sha:
                self.logger.error(f"Tag {tag} not found in {org}/{repo}")
                return []
            
            # 使用GitHub API的比较功能获取详细提交信息
            url = f"{self.github_api_base}/repos/{org}/{repo}/compare/{tag_commit_sha}...HEAD"
            
            # 设置代理
            git_config = config_manager.get_git_config()
            proxy = git_config.get('auth', {}).get('proxy', '')
            proxies = None
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            response = requests.get(
                url,
                headers=self._get_github_headers(),
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            
            comparison = response.json()
            commits = comparison.get('commits', [])
            
            # 按时间倒序排序
            commits.sort(key=lambda x: x.get('commit', {}).get('author', {}).get('date', ''), reverse=True)
            
            return commits
            
        except Exception as e:
            self.logger.error(f"Get detailed commits since tag failed: {str(e)}")
            return []

# 全局Git管理器实例
git_manager = GitManager()