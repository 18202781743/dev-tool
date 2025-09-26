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
    
    def get_latest_tag(self, org: str, repo: str) -> str:
        """获取最新标签"""
        tags = self.get_repo_tags(org, repo)
        if not tags:
            return "0.0.0"
        return tags[0].get('name', '0.0.0')
    
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
                # 获取最新提交
                commits = self.get_repo_commits(org, repo_name)
                latest_commit = commits[0] if commits else {}
                
                # 获取最新标签
                latest_tag = self.get_latest_tag(org, repo_name)
                
                # 预测下一个标签
                next_tag = self.generate_next_tag(latest_tag)
                
                repo_status = {
                    'name': repo_name,
                    'org': org,
                    'latest_commit': latest_commit,
                    'latest_tag': latest_tag,
                    'next_tag': next_tag,
                    'last_updated': latest_commit.get('commit', {}).get('author', {}).get('date', '')
                }
                repos_status.append(repo_status)
            
            # 按最后更新时间排序
            repos_status.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
            return repos_status
            
        except Exception as e:
            self.logger.error(f"Get watch repos status failed: {str(e)}")
            return []

# 全局Git管理器实例
git_manager = GitManager()