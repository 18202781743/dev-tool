import requests
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .config_manager import config_manager

class CRPManager:
    """CRP包管理器"""
    
    def __init__(self):
        self.base_url = "https://crp.uniontech.com/api"
        self.token = None
        self.user_name = None
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
    
    def _get_headers(self, need_auth: bool = True) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if need_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _make_request(self, method: str, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """统一的请求方法"""
        try:
            headers = self._get_headers()
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed ({method} {url}): {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in request ({method} {url}): {e}")
            return None
    
    def login(self) -> bool:
        """登录获取token"""
        try:
            config = config_manager.get_crp_config()
            auth = config.get('auth', {})
            
            user_id = auth.get('userId', '')
            password = auth.get('password', '')
            
            self.logger.info(f"尝试登录CRP，用户ID: {user_id}")
            self.logger.info(f"密码长度: {len(password) if password else 0}")
            
            if not user_id or not password:
                self.logger.error("用户ID或密码为空")
                return False
            
            url = f"{self.base_url}/login"
            data = {
                "userName": user_id,
                "password": password
            }
            
            self.logger.info(f"发送登录请求到: {url}")
            self.logger.debug(f"请求数据: {json.dumps(data, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                headers=self._get_headers(False),
                data=json.dumps(data),
                timeout=30
            )
            
            self.logger.info(f"响应状态码: {response.status_code}")
            self.logger.debug(f"响应头: {dict(response.headers)}")
            self.logger.debug(f"响应内容: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            self.token = result.get("Token", "")
            
            if not self.token:
                self.logger.error("响应中未找到Token")
                self.logger.error(f"完整响应: {result}")
                return False
            
            self.logger.info("登录成功，获取到Token")
            
            # 获取用户信息
            self.user_name = self.fetch_user()
            self.logger.info(f"用户名: {self.user_name}")
            return True
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP错误: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"错误响应: {e.response.text}")
            return False
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            return False
    
    def fetch_user(self) -> str:
        """获取用户信息"""
        try:
            url = f"{self.base_url}/user"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("Name", "")
            
        except Exception as e:
            self.logger.error(f"Fetch user failed: {str(e)}")
            return ""
    
    def list_projects(self, filter_name: str = "", page: int = 1, per_page: int = 20) -> Dict:
        """获取项目列表"""
        try:
            url = f"{self.base_url}/project"
            data = {
                "page": page,
                "perPage": per_page,
                "projectGroupID": 0,
                "newCommit": False,
                "archived": False,
                "branchID": 123,
                "name": filter_name if filter_name else ""
            }
            
            response = self._make_request("POST", url, data=data)
            
            if response:
                return {
                    "projects": response.get("Projects", []),
                    "pagination": response.get("Pagination", {})
                }
            return {"projects": [], "pagination": {}}
        except Exception as e:
            self.logger.error(f"List projects failed: {e}")
            return {"projects": [], "pagination": {}}
    
    def list_topics(self, topic_filter: str = "") -> List[Dict[str, Any]]:
        """获取主题列表"""
        try:
            # 使用搜索API来获取主题列表，这样可以更好地过滤
            url = f"{self.base_url}/topics/search"
            config = config_manager.get_crp_config()
            params = config.get('params', {})
            
            data = {
                "TopicType": params.get('topicType', 'test'),
                "UserName": self.user_name or '',
                "BranchID": params.get('branchId', 123)
            }
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            topics = response.json()
            
            # 如果有主题过滤器，进行模糊匹配
            if topic_filter:
                import re
                filtered_topics = []
                for topic in topics:
                    topic_name = topic.get('Name', '')
                    if re.search(topic_filter, topic_name, re.IGNORECASE):
                        filtered_topics.append(topic)
                return filtered_topics
            
            return topics
            
        except Exception as e:
            self.logger.error(f"List topics failed: {str(e)}")
            # 如果搜索API失败，回退到原来的方法
            try:
                url = f"{self.base_url}/topic"
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                
                topics = response.json()
                
                # 过滤当前用户的主题
                if self.user_name:
                    topics = [t for t in topics if t.get('Creator') == self.user_name]
                
                # 如果有主题过滤器，进行模糊匹配
                if topic_filter:
                    topics = [t for t in topics if topic_filter.lower() in t.get('Name', '').lower()]
                
                return topics
                
            except Exception as e2:
                self.logger.error(f"Fallback list topics also failed: {str(e2)}")
                return []
    
    def list_instances(self, topic_name: str) -> List[Dict[str, Any]]:
        """获取主题下的打包实例列表"""
        try:
            # 首先需要通过主题名称找到主题ID
            topic_id = self._get_topic_id_by_name(topic_name)
            if not topic_id:
                self.logger.error(f"找不到主题: {topic_name}")
                return []
            
            # 使用正确的API端点
            url = f"{self.base_url}/topics/{topic_id}/releases"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"List instances failed: {str(e)}")
            return []
    
    def _get_topic_id_by_name(self, topic_name: str) -> Optional[int]:
        """通过主题名称获取主题ID"""
        try:
            # 获取所有主题，找到匹配的ID
            topics = self.list_topics()
            for topic in topics:
                if topic.get('Name') == topic_name:
                    return topic.get('ID')
            return None
        except Exception as e:
            self.logger.error(f"Get topic ID failed: {str(e)}")
            return None
    
    def get_topic_id(self, topic_name: str) -> Optional[int]:
        """获取主题ID"""
        try:
            topics = self.list_topics()
            for topic in topics:
                if topic.get("Name") == topic_name:
                    return topic.get("ID")
            return None
        except Exception as e:
            self.logger.error(f"Get topic ID failed: {str(e)}")
            return None
    

    
    def create_package(self, topic_name: str, project_name: str, 
                      branch: str = None, archs: List[str] = None, 
                      tag: str = None) -> Dict[str, Any]:
        """创建打包任务"""
        try:
            config = config_manager.get_crp_config()
            params = config.get('params', {})
            
            if not branch:
                branch = params.get('projectBranch', 'upstream/master')
            
            if not archs:
                default_archs = params.get('defaultArchs', ['amd64'])
                archs = default_archs
            
            # 首先获取topic ID
            topic_id = self.get_topic_id(topic_name)
            if not topic_id:
                return {"error": f"Topic '{topic_name}' not found"}
            
            # 获取项目ID和详细信息
            projects_result = self.list_projects(project_name, 1, 5)
            projects = projects_result.get("projects", [])
            target_project = None
            
            for project in projects:
                if project.get("Name") == project_name:
                    target_project = project
                    break
            
            if not target_project:
                return {"error": f"Project '{project_name}' not found"}
            
            project_id = target_project.get("ID")
            repo_url = target_project.get("RepoUrl", "")
            
            # 获取分支的commit信息
            branches = self.get_project_branches(project_id)
            target_branch = None
            
            for b in branches:
                if b.get("Name") == branch:
                    target_branch = b
                    break
            
            if not target_branch:
                return {"error": f"Branch '{branch}' not found in project '{project_name}'"}
            
            commit_hash = target_branch.get("Commit", "")
            commit_message = target_branch.get("Message", "")
            
            # 获取详细的提交信息
            if repo_url and commit_hash:
                detailed_message = self._fetch_commit_message(repo_url, commit_hash)
                if detailed_message:
                    commit_message = detailed_message
            
            # 使用正确的API端点
            url = f"{self.base_url}/topics/{topic_id}/new_release"
            
            # 获取配置中的默认值
            crp_config = self.config_manager.get_crp_config()
            params = crp_config.get('params', {})
            
            data = {
                "Arches": ";".join(archs),  # 转换为字符串格式
                "BaseTag": None,
                "Branch": branch,
                "BuildID": 0,
                "BuildState": None,
                "Changelog": [commit_message or "chore: update changelog"],
                "Commit": commit_hash,
                "History": None,
                "ID": 0,
                "ProjectID": project_id,
                "ProjectName": project_name,
                "ProjectRepoUrl": repo_url,
                "SlaveNode": None,
                "Tag": tag or "1",
                "TagSuffix": None,
                "TopicID": topic_id,
                "TopicType": params.get('topicType', 'test'),
                "ChangeLogMode": True,  # 布尔值
                "RepoType": "deb",  # 固定值
                "Custom": True,  # 布尔值
                "BranchID": str(params.get('branchId', '123'))  # 字符串格式
            }
            
            self.logger.debug(f"Creating package with data: {json.dumps(data, indent=2)}")
            
            response = self._make_request("POST", url, data=data)
            
            if response:
                return {"success": True, "data": response}
            else:
                return {"error": "Failed to create package"}
            
        except Exception as e:
            self.logger.error(f"Create package failed: {str(e)}")
            return {"error": str(e)}
    
    def batch_create_packages(self, topic_name: str, 
                            packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量创建打包任务"""
        results = []
        for package_info in packages:
            result = self.create_package(
                topic_name=topic_name,
                project_name=package_info['name'],
                branch=package_info.get('branch'),
                archs=package_info.get('archs'),
                tag=package_info.get('tag')
            )
            results.append({
                'name': package_info['name'],
                'result': result
            })
        return results
    
    def get_instance_detail(self, instance_id: int) -> Dict[str, Any]:
        """获取打包实例详情"""
        try:
            url = f"{self.base_url}/instance/{instance_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Get instance detail failed: {str(e)}")
            return {}
    
    def get_project_branches(self, project_id: int) -> List[Dict]:
        """获取项目分支列表"""
        try:
            url = f"{self.base_url}/projects/{project_id}/branches"
            response = self._make_request("GET", url)
            
            if response and isinstance(response, list):
                return response
            return []
        except Exception as e:
            self.logger.error(f"Get project branches failed: {e}")
            return []

    def get_latest_commit(self, project_name: str, branch: str = "upstream/master") -> Dict:
        """获取项目最新提交信息"""
        try:
            # 首先搜索项目获取项目ID
            projects_result = self.list_projects(project_name, 1, 5)
            projects = projects_result.get("projects", [])
            
            # 找到匹配的项目
            target_project = None
            for project in projects:
                if project.get("Name") == project_name:
                    target_project = project
                    break
            
            if not target_project:
                self.logger.error(f"Project not found: {project_name}")
                return {}
            
            project_id = target_project.get("ID")
            if not project_id:
                self.logger.error(f"Project ID not found for: {project_name}")
                return {}
            
            # 获取项目的详细分支信息
            branches = self.get_project_branches(project_id)
            self.logger.debug(f"Got branches for project {project_name} (ID: {project_id}): {type(branches)}, length: {len(branches) if branches else 'None'}")
            
            if not branches:
                self.logger.error(f"No branches found for project: {project_name}")
                return {}
            
            # 找到目标分支
            target_branch = None
            
            # 先尝试精确匹配分支名
            for b in branches:
                if b.get("Name") == branch:
                    target_branch = b
                    break
            
            # 如果没有找到，尝试匹配master分支
            if not target_branch and branch == "upstream/master":
                for b in branches:
                    if b.get("Name") == "master":
                        target_branch = b
                        break
            
            # 如果还是没有找到，取第一个分支
            if not target_branch and branches:
                target_branch = branches[0]
            
            if not target_branch:
                self.logger.error(f"Branch not found: {branch}")
                return {}
            
            commit_hash = target_branch.get("Commit", "")
            timestamp = target_branch.get("Ts", 0)
            
            # 转换时间戳为可读格式
            import datetime
            if timestamp:
                try:
                    date_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    date_str = "Unknown"
            else:
                date_str = "Unknown"
            
            # 获取详细的提交信息
            repo_url = target_project.get("RepoUrl", "")
            commit_message = target_branch.get("Message", "")  # 备用信息
            
            if repo_url and commit_hash:
                detailed_message = self._fetch_commit_message(repo_url, commit_hash)
                if detailed_message:
                    commit_message = detailed_message
            
            return {
                "hash": commit_hash,
                "message": commit_message or "No commit message",
                "author": "Unknown",  # CRP API不返回作者信息
                "date": date_str,
                "branch": target_branch.get("Name", ""),
                "timestamp": timestamp,
                "repo_url": repo_url
            }
            
        except Exception as e:
            self.logger.error(f"Get latest commit failed: {e}")
            return {}
    
    def _fetch_commit_message(self, repo_url: str, commit_id: str) -> str:
        """获取提交信息详情"""
        try:
            url = f"{self.base_url}/projects/getGerritCommitMessage"
            data = {
                "repo_url": repo_url,
                "commit_id": commit_id
            }
            
            self.logger.debug(f"Fetching commit message for {repo_url}, commit: {commit_id}")
            response = self._make_request("POST", url, data=data)
            
            if response:
                self.logger.debug(f"Commit message response: {response}")
                # API返回格式: {code: 200, message: "commit message", status: "success"}
                if response.get("status") == "success" and response.get("code") == 200:
                    return response.get("message", "")
                else:
                    self.logger.warning(f"API returned error: {response}")
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Fetch commit message failed: {e}")
            return ""

# 全局CRP管理器实例
crp_manager = CRPManager()