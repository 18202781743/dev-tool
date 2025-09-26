import os
import yaml
import json
import rsa
import base64
from typing import Dict, Any, Optional

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), '../config')
        self.config_dir = os.path.abspath(config_dir)
        self.config_file = os.path.join(self.config_dir, 'config.yaml')
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._get_default_config()
            self.save_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'crp': {
                'auth': {
                    'userId': '',
                    'password': ''
                },
                'params': {
                    'topicType': 'test',
                    'archs': 'amd64;arm64;loong64;sw64;mips64el',
                    'branchId': 123,
                    'projectBranch': 'upstream/master',
                    'defaultArchs': ['amd64', 'arm64', 'loong64']
                }
            },
            'git': {
                'auth': {
                    'githubID': '',
                    'debEmail': '',
                    'githubToken': '',
                    'proxy': ''
                },
                'params': {
                    'projectBranch': 'master',
                    'projectOrg': 'linuxdeepin',
                    'projectReviewers': [],
                    'projectRootDir': '~/.cache/web-dev-tool-git',
                    'watchRepos': []
                }
            },
            'web': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': True,
                'secret_key': 'dev-tool-web-secret-key-change-in-production'
            }
        }
    
    def get_config(self, section: str = None) -> Dict[str, Any]:
        """获取配置"""
        if section:
            return self._config.get(section, {})
        return self._config
    
    def set_config(self, section: str, key: str, value: Any):
        """设置配置"""
        if section not in self._config:
            self._config[section] = {}
        
        # 支持嵌套键，如 auth.userId
        keys = key.split('.')
        current = self._config[section]
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    def save_config(self):
        """保存配置到文件"""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
    
    def encrypt_crp_password(self, password: str) -> str:
        """加密CRP密码"""
        # 公钥 PEM 格式字符串（来自原项目的gen-crp-pwd.py）
        pub_key_pem = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCkA9WqirWQII3D8/M9UG8X8ybQ
Ou+cPSNTgR9b4HenJ7A5zSfkXZnetb5q6MmKTJLGCl9MSsHveQPHmLGDG+xw2MlB
w3Yefd/jJ1Cg8pP69wlHRX+wiyh5p8KY55ehFNsQLm3kDGXgVJdtrZn/MiBOlCtE
fe9YvvT0lqy2BtBpaQIDAQAB
-----END PUBLIC KEY-----"""
        
        # 加载公钥
        pub_key = rsa.PublicKey.load_pkcs1_openssl_pem(pub_key_pem.encode())
        
        # 用公钥加密
        cipher = rsa.encrypt(password.encode(), pub_key)
        
        # 转 base64，和前端 jsencrypt 的输出一样
        cipher_base64 = base64.b64encode(cipher).decode()
        
        return cipher_base64
    
    def get_crp_config(self) -> Dict[str, Any]:
        """获取CRP配置"""
        return self.get_config('crp')
    
    def get_git_config(self) -> Dict[str, Any]:
        """获取Git配置"""
        return self.get_config('git')
    
    def get_web_config(self) -> Dict[str, Any]:
        """获取Web配置"""
        return self.get_config('web')
    
    def update_crp_config(self, config_data: Dict[str, Any]):
        """更新CRP配置"""
        crp_config = self.get_config('crp')
        
        # 处理认证信息
        if 'auth' in config_data:
            auth = config_data['auth']
            if 'userId' in auth:
                self.set_config('crp', 'auth.userId', auth['userId'])
            if 'password' in auth and auth['password'] and auth['password'] != '***':
                # 只有在密码不是占位符时才加密和保存
                encrypted_pwd = self.encrypt_crp_password(auth['password'])
                self.set_config('crp', 'auth.password', encrypted_pwd)
        
        # 处理参数
        if 'params' in config_data:
            params = config_data['params']
            for key, value in params.items():
                self.set_config('crp', f'params.{key}', value)
        
        self.save_config()
    
    def update_git_config(self, config_data: Dict[str, Any]):
        """更新Git配置"""
        # 处理认证信息
        if 'auth' in config_data:
            auth = config_data['auth']
            for key, value in auth.items():
                self.set_config('git', f'auth.{key}', value)
        
        # 处理参数
        if 'params' in config_data:
            params = config_data['params']
            for key, value in params.items():
                self.set_config('git', f'params.{key}', value)
        
        self.save_config()

# 全局配置管理器实例
config_manager = ConfigManager()