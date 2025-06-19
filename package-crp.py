import sys
import argparse
import requests
import json
import re
import os
import logging
from datetime import datetime

class Colors:
    RESET = '\033[0m'
    RED = '\033[31m'      # 错误
    YELLOW = '\033[33m'   # 警告
    GREEN = '\033[32m'    # 成功信息
    GRAY = '\033[90m'     # 调试信息
    
    # 背景颜色用于状态显示
    BG_GREEN = '\033[42m'   # 绿色背景 - 成功
    BG_RED = '\033[41m'     # 红色背景 - 失败
    BG_YELLOW = '\033[43m'  # 黄色背景 - 进行中
    BG_GRAY = '\033[100m'   # 灰色背景 - 未知
    WHITE = '\033[97m'      # 白色文字，配合背景色使用

class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.ERROR: Colors.RED,
        logging.WARNING: Colors.YELLOW,
        logging.INFO: Colors.GREEN,
        logging.DEBUG: Colors.GRAY,
    }

    def format(self, record):
        # 先格式化消息
        formatted = super().format(record)
        
        # 只在终端中显示颜色，整行应用颜色
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            color = self.COLORS.get(record.levelno, '')
            if color:
                formatted = f"{color}{formatted}{Colors.RESET}"
        
        return formatted

def colorize_build_state(state):
    if not (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()):
        return state
        
    state_str = str(state).upper()
    
    # 成功状态 - 绿色背景
    if state_str in ['UPLOAD_OK', 'SUCCESS', 'OK']:
        return f"{Colors.BG_GREEN}{Colors.WHITE} {state} {Colors.RESET}"
    
    # 失败状态 - 红色背景  
    elif state_str in ['UPLOAD_GIVEUP', 'APPLY_FAILED']:
        return f"{Colors.BG_RED}{Colors.WHITE} {state} {Colors.RESET}"
    
    # 进行中状态 - 黄色背景
    elif state_str in ['APPLYING', 'UPLOADING']:
        return f"{Colors.BG_YELLOW}{Colors.WHITE} {state} {Colors.RESET}"
    
    # 未知状态 - 灰色背景
    elif state_str in ['UNKNOWN'] or not state_str:
        return f"{Colors.BG_GRAY}{Colors.WHITE} {state} {Colors.RESET}"
    
    # 其他未识别状态 - 灰色背景
    else:
        return f"{Colors.BG_GRAY}{Colors.WHITE} {state} {Colors.RESET}"

# 全局参数
class ArgsInfo:
    def __init__(self):
        # 默认值
        self.topicName = "test-xxxx" # 主题名称
        self.projectName = "xxxx" # 项目名称
        self.projectBranch = "upstream/master" # 项目分支
        self.projectTag = "5.0.0" # 自定义tag
        self.projectUpdateMode = True # 根据changelog自动更新版本号
        self.branchId = 119 # snipe分支
        self.archs = "amd64;arm64;loong64;sw64;mips64el"
        self.topicType = "test"
        self.userName = "xxxx" # crp用户名（过滤topic）
        self.token = "xxxx"
        self.verbose = False # 是否显示详细输出

        # 从配置文件读取参数
        config_path = os.path.expanduser('~/.config/dev-tool/package-crp-config.json')
        with open(config_path) as f:
            config = json.load(f)
        
        # 认证信息
        self.userId = config['auth']['userId']     # crp用户id（登陆获取token）
        self.password = config['auth']['password'] # crp用户密码

        # 从配置文件中读取其他参数（如果存在）
        if 'params' in config:
            params = config['params']
            self.topicType = params.get('topicType', self.topicType)
            self.archs = params.get('archs', self.archs)
            self.branchId = params.get('branchId', self.branchId)
            self.projectBranch = params.get('projectBranch', self.projectBranch)

argsInfo = ArgsInfo()

def setup_logging():
    level = logging.DEBUG if argsInfo.verbose else logging.INFO
    
    # 创建logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建控制台处理器
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # 使用彩色格式化器
    formatter = ColoredFormatter(
        fmt='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger


logger = setup_logging()

class ProjectInfo:
    name = "dtk6"
    id = 0
    url = "https://gitee.com/xxxxx/dtk6.git"

class TopicInfo:
    name = "test-treeland-private1"
    id = 0

class BranchInfo:
    projectId = 0
    name = "upstream/master"
    commit = "b9e8b6b"
    changelog = "chore: update changelog"

class InstanceInfo:
    Arches = "amd64"
    BaseTag = None
    Branch = "upstream/master"
    BuildID = 0
    BuildState = None
    Changelog = ["chore: update changelog"]
    Commit = "xxxx"
    History = None
    ID = 0
    ProjectID = 4305
    ProjectName = "dtkcommon-v25"
    ProjectRepoUrl = None
    SlaveNode = None
    Tag = "1"
    TagSuffix = None
    TopicID = 20825
    TopicName = "test-treeland"
    TopicType = "test"
    ChangeLogMode = True
    RepoType = "deb"
    Custom = True
    BranchID = "55"

def fetchToken():
    try:
        url = "https://crp.uniontech.com/api/login"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "userName": argsInfo.userId,
            "password": argsInfo.password
        }

        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(data),
            timeout=30
        )
        response.raise_for_status()  # Raises HTTPError for bad responses

        result = response.json()
        token = result.get("Token", "")
        if not token:
            logger.error("Token not found in response")
            return ""

        return token

    except requests.exceptions.RequestException as e:
        logger.error(f"Login request failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return ""
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode response JSON: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return ""

def fetchUser():
    try:
        url = "https://crp.uniontech.com/api/user"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        name = result.get("Name", "")
        if not name:
            logger.error("Name not found in response")
            return ""

        return name

    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch user request failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return ""
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode response JSON: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return ""

def listPojects():
    try:
        url = "https://crp.uniontech.com/api/project"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}",
            "Content-Type": "application/json"
        }
        data = {
            "page": 0,
            "perPage": 0,
            "projectGroupID": 0,
            "newCommit": False,
            "archived": False,
            "branchID": argsInfo.branchId,
            "name": argsInfo.projectName
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()

        projects = []
        result = response.json()
        projects_data = result.get("Projects", [])
        
        for project in projects_data:
            projectName = project.get("Name", "")
            id = project.get("ID", 0)
            repoUrl = project.get("RepoUrl", "")
            
            if re.search(argsInfo.projectName, projectName, re.IGNORECASE):
                info = ProjectInfo()
                info.id = id
                info.name = projectName
                info.url = repoUrl
                projects.append(info)

        return projects

    except requests.exceptions.RequestException as e:
        logger.error(f"List projects request failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode projects response: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in listPojects: {str(e)}")
        return []

def listTopics():
    try:
        url = "https://crp.uniontech.com/api/topics/search"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}",
            "Content-Type": "application/json"
        }
        data = {
            "TopicType": argsInfo.topicType,
            "UserName": argsInfo.userName,
            "BranchID": argsInfo.branchId
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()

        topics = []
        result = response.json()
        
        for topic in result:
            id = topic.get("ID", 0)
            topicName = topic.get("Name", "")
            
            if re.search(argsInfo.topicName, topicName, re.IGNORECASE):
                info = TopicInfo()
                info.id = id
                info.name = topicName
                topics.append(info)

        return topics

    except requests.exceptions.RequestException as e:
        logger.error(f"List topics request failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode topics response: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in listTopics: {str(e)}")
        return []

def fetchCommitInfo(repoUrl, commit):
    try:
        url = "https://crp.uniontech.com/api/projects/getGerritCommitMessage"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}",
            "Content-Type": "application/json"
        }
        data = {
            "repo_url": repoUrl,
            "commit_id": commit
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()

        if response.status_code != 200:
            logger.error(f"Fetch commit info failed: {response.status_code}")
            return ""

        result = response.json()
        message = result.get("message", "")
        if not message:
            logger.warning("No commit message found in response")
        return message

    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch commit info failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return ""
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode commit info response: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error in fetchCommitInfo: {str(e)}")
        return ""

def listBranchs(projectId, projectUrl, targetName):
    try:
        url = f"https://crp.uniontech.com/api/projects/{projectId}/branches"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        branchs = []
        result = response.json()
        
        for branch in result:
            commit = branch.get("Commit", "")
            name = branch.get("Name", "")
            
            if re.search(targetName, name, re.IGNORECASE):
                info = BranchInfo()
                info.commit = commit
                info.name = name
                info.projectId = projectId
                info.changelog = fetchCommitInfo(projectUrl, commit) == "" and branch.get("Message", "") or fetchCommitInfo(projectUrl, commit)
                branchs.append(info)

        return branchs

    except requests.exceptions.RequestException as e:
        logger.error(f"List branches failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode branches response: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in listBranchs: {str(e)}")
        return []

def listCreatedInstances(topicId):
    try:
        url = f"https://crp.uniontech.com/api/topics/{topicId}/releases"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        instances = []
        result = response.json()
        
        for instance in result:
            info = InstanceInfo()
            info.ID = instance.get("ID", 0)
            info.ProjectID = instance.get("ProjectID", 0)
            info.ProjectName = instance.get("ProjectName", "")
            info.Branch = instance.get("Branch", "")
            info.Tag = instance.get("Tag", "")
            build_state = instance.get("BuildState", {})
            info.BuildState = build_state.get("state", "unknown")
            info.BuildID = instance.get("BuildID", 0)
            instances.append(info)

        return instances

    except requests.exceptions.RequestException as e:
        logger.error(f"List instances failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode instances response: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in listCreatedInstances: {str(e)}")
        return []

def deleteInstance(instanceId):
    try:
        url = f"https://crp.uniontech.com/api/topic_releases/{instanceId}"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}"
        }

        response = requests.delete(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"Successfully deleted instance: {instanceId}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Delete instance {instanceId} failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error in deleteInstance: {str(e)}")

def createInstance(instanceInfo):
    try:
        url = f"https://crp.uniontech.com/api/topics/{instanceInfo.TopicID}/new_release"
        headers = {
            "Authorization": f"Bearer {argsInfo.token}",
            "Content-Type": "application/json"
        }
        data = {
            "Arches": instanceInfo.Arches,
            "BaseTag": instanceInfo.BaseTag,
            "Branch": instanceInfo.Branch,
            "BuildID": instanceInfo.BuildID,
            "BuildState": instanceInfo.BuildState,
            "Changelog": [instanceInfo.Changelog],
            "Commit": instanceInfo.Commit,
            "History": instanceInfo.History,
            "ID": instanceInfo.ID,
            "ProjectID": instanceInfo.ProjectID,
            "ProjectName": instanceInfo.ProjectName,
            "ProjectRepoUrl": instanceInfo.ProjectRepoUrl,
            "SlaveNode": instanceInfo.SlaveNode,
            "Tag": instanceInfo.Tag,
            "TagSuffix": instanceInfo.TagSuffix,
            "TopicID": instanceInfo.TopicID,
            "TopicType": instanceInfo.TopicType,
            "ChangeLogMode": instanceInfo.ChangeLogMode,
            "RepoType": instanceInfo.RepoType,
            "Custom": instanceInfo.Custom,
            "BranchID": instanceInfo.BranchID
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"Successfully created instance: {response.text}")
        logger.debug(f"Instance creation response: {response.json()}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Create instance failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Server response: {e.response.text}")
        logger.debug(f"Request data: {data}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode create instance response: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Raw response: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in createInstance: {str(e)}")
        raise

def listInstances():
    instances = []
    topics = listTopics()
    if len(topics) == 0:
        logger.warning("No topics found matching criteria")
        return []

    for topic in topics:
        projects = listPojects()
        if len(projects) == 0:
            continue
        for project in projects:
            branchs = listBranchs(project.id, project.url, argsInfo.projectBranch)
            if len(branchs) == 0:
                continue
            for branch in branchs:
                info = InstanceInfo()
                info.Commit = branch.commit
                info.Branch = branch.name
                info.Arches = argsInfo.archs
                info.BranchID = argsInfo.branchId
                info.TopicType = argsInfo.topicType
                info.TopicID = topic.id
                info.TopicName = topic.name
                info.ProjectID = project.id
                info.ProjectName = project.name
                info.Changelog = branch.changelog
                info.Tag = argsInfo.projectTag
                info.ChangeLogMode = argsInfo.projectUpdateMode
                instances.append(info)

    return instances

def createOrUpdate():
    instances = listInstances()
    for item in instances:
        logger.info(f"Creating instance - Topic: {item.TopicName}, Project: {item.ProjectName}, Branch: {item.Branch}, Changelog: {item.Changelog}")
        createdInstance = listCreatedInstances(item.TopicID)
        for (createdInstance) in createdInstance:
            if (createdInstance.ProjectName == item.ProjectName and createdInstance.Branch == item.Branch):
                deleteInstance(createdInstance.ID)
        createInstance(item)

def main(argv):
    parser = argparse.ArgumentParser(description='Pack for CRP.')
    parser.add_argument('command', nargs='?', default='pack', choices=['pack', 'test', 'projects', 'topics', 'instances', 'branches'], help='The command type (list or pack)')

    parser.add_argument('--topic', type=str, default=None, help='The topic name parameter')
    parser.add_argument('--name', type=str, default=None, help='The project name parameter')
    parser.add_argument('--branch', type=str, default=None, help='The project branch parameter')
    parser.add_argument('--tag', type=str, default=None, help='The project tag parameter')
    parser.add_argument('--verbose', action='store_true', help='Show verbose debug output')

    args = parser.parse_args()
    argsInfo.verbose = args.verbose
    global logger
    logger = setup_logging()  # Reinitialize logger with new level

    if (args.topic is not None):
        argsInfo.topicName = args.topic
    if (args.name is not None):
        argsInfo.projectName = args.name
    if (args.branch is not None):
        argsInfo.projectBranch = args.branch
    if (args.tag is not None):
        argsInfo.projectTag = args.tag
        argsInfo.projectUpdateMode = False
    
    token = fetchToken()
    argsInfo.token = token
    userName = fetchUser()
    argsInfo.userName = userName
    
    if (args.command == 'projects'):
        projects = listPojects()
        for project in projects:
            logger.info(f"Found project: {project.name}")
    if (args.command == 'topics'):
        topics = listTopics()
        for topic in topics:
            logger.info(f"Found topic: {topic.name}")
    if (args.command == 'instances'):
        topics = listTopics()
        if (len(topics) == 0):
            logger.warning("No topics found")
            return
        for topic in topics:
            instances = listCreatedInstances(topic.id)
            for instance in instances:
                colored_state = colorize_build_state(instance.BuildState)
                if instance.BuildState == "UPLOAD_OK":
                    logger.info(f"Instance found - Topic: {topic.name}, Project: {instance.ProjectName}, Branch: {instance.Branch}, Tag: {instance.Tag}, State: {colored_state}")
                else:
                    logger.info(f"Instance found - Topic: {topic.name}, Project: {instance.ProjectName}, Branch: {instance.Branch}, Tag: {instance.Tag}, State: {colored_state}\n查看详情: https://shuttle.uniontech.com/#/tasks/task?taskid={instance.BuildID}")
    if (args.command == 'test'):
        instances = listInstances()
        for item in instances:
            logger.info(f"Test instance - Topic: {item.TopicName}, Project: {item.ProjectName}, Branch: {item.Branch}, Changelog: {item.Changelog}")
    if (args.command == 'branches'):
        topics = listTopics()
        if len(topics) == 0:
            logger.warning("No topics found for branches listing")
            return []
        for topic in topics:
            projects = listPojects()
            if len(projects) == 0:
                continue
            for project in projects:
                branchs = listBranchs(project.id, project.url, "")
                for branch in branchs:
                    logger.info(f"Branch info - Topic: {topic.name}, Project: {project.name}, Branch: {branch.name}, Changelog: {branch.changelog}")
    if (args.command == 'pack'):
        createOrUpdate()

if(__name__=="__main__"):
    os.environ.pop("https_proxy", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("all_proxy", None)
    main(sys.argv)
