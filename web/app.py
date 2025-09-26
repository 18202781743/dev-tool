from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import logging
import os
import sys

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.config_manager import config_manager
from modules.crp_manager import crp_manager
from modules.git_manager import git_manager

# 创建Flask应用
app = Flask(__name__)

# 配置应用
web_config = config_manager.get_web_config()
app.config['SECRET_KEY'] = web_config.get('secret_key', 'dev-tool-web-secret-key')

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/config')
def config_page():
    """配置页面"""
    crp_config = config_manager.get_crp_config()
    git_config = config_manager.get_git_config()
    return render_template('config.html', crp_config=crp_config, git_config=git_config)

@app.route('/api/config/crp', methods=['GET', 'POST'])
def api_crp_config():
    """CRP配置API"""
    if request.method == 'GET':
        config = config_manager.get_crp_config()
        # 创建配置的深拷贝，避免修改原始配置
        import copy
        display_config = copy.deepcopy(config)
        # 根据密码是否存在来决定显示内容
        if 'auth' in display_config and 'password' in display_config['auth']:
            if display_config['auth']['password']:
                display_config['auth']['password'] = '***'  # 有密码时显示占位符
            else:
                display_config['auth']['password'] = ''     # 无密码时显示空
        return jsonify(display_config)
    
    elif request.method == 'POST':
        try:
            config_data = request.get_json()
            config_manager.update_crp_config(config_data)
            return jsonify({'success': True, 'message': 'CRP配置已保存'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

@app.route('/api/config/git', methods=['GET', 'POST'])
def api_git_config():
    """Git配置API"""
    if request.method == 'GET':
        config = config_manager.get_git_config()
        # 创建配置的深拷贝，避免修改原始配置
        import copy
        display_config = copy.deepcopy(config)
        # 隐藏GitHub token的真实值
        if 'auth' in display_config and 'githubToken' in display_config['auth']:
            if display_config['auth']['githubToken']:
                display_config['auth']['githubToken'] = '***'  # 有token时显示占位符
            else:
                display_config['auth']['githubToken'] = ''  # 无token时显示空
        return jsonify(display_config)
    
    elif request.method == 'POST':
        try:
            config_data = request.get_json()
            config_manager.update_git_config(config_data)
            return jsonify({'success': True, 'message': 'Git配置已保存'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

@app.route('/crp')
def crp_page():
    """CRP打包页面"""
    return render_template('crp.html')

@app.route('/crp/topic/<topic_name>')
def crp_topic_page(topic_name):
    """CRP主题详情页面"""
    return render_template('crp_topic.html', topic_name=topic_name)

@app.route('/api/crp/login', methods=['POST'])
def api_crp_login():
    """CRP登录API"""
    try:
        if crp_manager.login():
            return jsonify({
                'success': True, 
                'message': '登录成功',
                'user': crp_manager.user_name
            })
        else:
            return jsonify({'success': False, 'message': '登录失败，请检查用户名和密码'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'})

@app.route('/api/crp/topics')
def api_crp_topics():
    """获取CRP主题列表"""
    try:
        if not crp_manager.token:
            return jsonify({'success': False, 'message': '请先登录'})
        
        topic_filter = request.args.get('filter', '')
        topics = crp_manager.list_topics(topic_filter)
        return jsonify({'success': True, 'topics': topics})
    except Exception as e:
        app.logger.error(f"获取主题列表失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取主题列表失败: {str(e)}'})

@app.route('/api/crp/projects')
def get_crp_projects():
    """获取CRP项目列表"""
    filter_name = request.args.get('filter', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    if not crp_manager.token:
        if not crp_manager.login():
            return jsonify({"success": False, "message": "未登录CRP"})
    
    result = crp_manager.list_projects(filter_name, page, per_page)
    return jsonify({"success": True, **result})

@app.route('/api/crp/projects/<int:project_id>/branches')
def get_project_branches(project_id):
    """获取项目分支列表"""
    if not crp_manager.token:
        if not crp_manager.login():
            return jsonify({"success": False, "message": "未登录CRP"})
    
    branches = crp_manager.get_project_branches(project_id)
    return jsonify({"success": True, "branches": branches})

@app.route('/api/crp/commit/<project_name>')
def get_project_commit_info(project_name):
    """获取项目提交信息"""
    if not crp_manager.token:
        if not crp_manager.login():
            return jsonify({"success": False, "message": "未登录CRP"})
    
    commit_info = crp_manager.get_latest_commit(project_name)
    return jsonify({"success": True, "commit": commit_info})

@app.route('/api/crp/config')
def api_crp_config_info():
    """获取CRP配置信息（用于前端）"""
    try:
        config = config_manager.get_crp_config()
        params = config.get('params', {})
        
        return jsonify({
            'success': True,
            'config': {
                'defaultArchs': params.get('defaultArchs', ['amd64']),
                'branchId': params.get('branchId', 123),
                'topicType': params.get('topicType', 'test'),
                'projectBranch': params.get('projectBranch', 'upstream/master')
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取配置失败: {str(e)}'})

@app.route('/api/crp/status')
def api_crp_status():
    """获取CRP连接状态"""
    try:
        is_connected = bool(crp_manager.token)
        user_name = crp_manager.user_name if is_connected else None
        
        return jsonify({
            'success': True,
            'connected': is_connected,
            'user_name': user_name
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取状态失败: {str(e)}'})

@app.route('/api/crp/instances/<topic_name>')
def api_crp_instances(topic_name):
    """获取主题下的打包实例列表"""
    try:
        if not crp_manager.token:
            return jsonify({'success': False, 'message': '请先登录'})
        
        instances = crp_manager.list_instances(topic_name)
        return jsonify({'success': True, 'instances': instances})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取打包列表失败: {str(e)}'})

@app.route('/api/crp/branches')
def api_crp_branches():
    """获取项目分支信息"""
    try:
        if not crp_manager.token:
            return jsonify({'success': False, 'message': '请先登录'})
        
        topic_name = request.args.get('topic')
        project_name = request.args.get('project')
        
        if not project_name:
            return jsonify({'success': False, 'message': '缺少项目名称参数'})
        
        branches = crp_manager.get_project_branches(topic_name, project_name)
        return jsonify({'success': True, 'branches': branches})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取分支信息失败: {str(e)}'})

@app.route('/api/crp/latest-commit')
def api_crp_latest_commit():
    """获取项目最新提交信息"""
    try:
        if not crp_manager.token:
            return jsonify({'success': False, 'message': '请先登录'})
        
        project_name = request.args.get('project')
        branch = request.args.get('branch', 'upstream/master')
        
        if not project_name:
            return jsonify({'success': False, 'message': '缺少项目名称参数'})
        
        commit_info = crp_manager.get_latest_commit(project_name, branch)
        
        if commit_info:
            return jsonify({'success': True, 'commit': commit_info})
        else:
            return jsonify({'success': False, 'message': '无法获取提交信息'})
    except Exception as e:
        app.logger.error(f"获取最新提交失败: {str(e)}")
        return jsonify({'success': False, 'message': f'获取提交信息失败: {str(e)}'})

@app.route('/api/crp/package', methods=['POST'])
def api_crp_package():
    """创建打包任务"""
    try:
        if not crp_manager.token:
            return jsonify({'success': False, 'message': '请先登录'})
        
        data = request.get_json()
        result = crp_manager.create_package(
            topic_name=data.get('topic'),
            project_name=data.get('project'),
            branch=data.get('branch'),
            archs=data.get('archs'),
            tag=data.get('tag')
        )
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']})
        else:
            return jsonify({'success': True, 'message': '打包任务创建成功', 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建打包任务失败: {str(e)}'})

@app.route('/api/crp/batch-package', methods=['POST'])
def api_crp_batch_package():
    """批量创建打包任务"""
    try:
        if not crp_manager.token:
            return jsonify({'success': False, 'message': '请先登录'})
        
        data = request.get_json()
        results = crp_manager.batch_create_packages(
            topic_name=data.get('topic'),
            packages=data.get('packages', [])
        )
        
        return jsonify({'success': True, 'message': '批量打包任务创建完成', 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'message': f'批量创建打包任务失败: {str(e)}'})

@app.route('/git')
def git_page():
    """Git标签管理页面"""
    return render_template('git.html')

@app.route('/api/git/repos')
def api_git_repos():
    """获取组织仓库列表"""
    try:
        org = request.args.get('org', '')
        name_filter = request.args.get('filter', '')
        repos = git_manager.get_org_repos(org, name_filter)
        return jsonify({'success': True, 'repos': repos})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取仓库列表失败: {str(e)}'})

@app.route('/api/git/watch-repos')
def api_git_watch_repos():
    """获取关注仓库状态"""
    try:
        repos_status = git_manager.get_watch_repos_status()
        return jsonify({'success': True, 'repos': repos_status})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取关注仓库状态失败: {str(e)}'})

@app.route('/api/git/latest-tag')
def api_git_latest_tag():
    """获取最新标签"""
    try:
        org = request.args.get('org')
        repo = request.args.get('repo')
        
        if not org or not repo:
            return jsonify({'success': False, 'message': '参数缺失'})
        
        latest_tag = git_manager.get_latest_tag(org, repo)
        next_tag = git_manager.generate_next_tag(latest_tag)
        
        return jsonify({
            'success': True, 
            'latest_tag': latest_tag,
            'next_tag': next_tag
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取标签信息失败: {str(e)}'})

@app.route('/api/git/commits-detail')
def api_git_commits_detail():
    """获取提交详情"""
    try:
        org = request.args.get('org')
        repo = request.args.get('repo')
        since_tag = request.args.get('since_tag')
        
        if not org or not repo:
            return jsonify({'success': False, 'message': '参数缺失'})
        
        if since_tag:
            # 获取自指定标签以来的提交
            commits = git_manager.get_commits_since_tag_detailed(org, repo, since_tag)
        else:
            # 获取最近的提交
            commits = git_manager.get_repo_commits(org, repo)[:20]  # 限制20个提交
        
        return jsonify({'success': True, 'commits': commits})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取提交详情失败: {str(e)}'})

@app.route('/api/git/create-tag', methods=['POST'])
def api_git_create_tag():
    """创建标签PR"""
    try:
        data = request.get_json()
        result = git_manager.create_tag_pr(
            org=data.get('org'),
            repo=data.get('repo'),
            tag=data.get('tag'),
            branch=data.get('branch', 'master'),
            reviewers=data.get('reviewers', [])
        )
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']})
        else:
            return jsonify({'success': True, 'message': '标签PR创建成功', 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建标签PR失败: {str(e)}'})

@app.route('/api/git/pr-status')
def api_git_pr_status():
    """获取PR状态"""
    try:
        org = request.args.get('org')
        repo = request.args.get('repo')
        pr_number = request.args.get('pr_number')
        
        if not org or not repo or not pr_number:
            return jsonify({'success': False, 'message': '参数缺失'})
        
        pr_status = git_manager.get_pr_status(org, repo, int(pr_number))
        return jsonify({'success': True, 'pr_status': pr_status})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取PR状态失败: {str(e)}'})

def init_app():
    """初始化应用，自动连接CRP"""
    try:
        # 自动尝试登录CRP
        if crp_manager.login():
            app.logger.info("CRP自动登录成功")
        else:
            app.logger.warning("CRP自动登录失败，请检查配置")
    except Exception as e:
        app.logger.error(f"CRP自动登录异常: {str(e)}")

if __name__ == '__main__':
    # 初始化应用
    init_app()
    
    web_config = config_manager.get_web_config()
    app.run(
        host=web_config.get('host', '0.0.0.0'),
        port=web_config.get('port', 5000),
        debug=web_config.get('debug', True)
    )