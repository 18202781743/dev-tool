<div align="center">
  <h1>🚀 CRP 工具套件</h1>
  <p>✨ 一个高效管理CRP打包流程的工具集合</p>
  
  <div>
    <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="version">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
    <img src="https://img.shields.io/badge/platform-Linux-lightgrey" alt="platform">
    <img src="https://img.shields.io/badge/python-3.8+-blue" alt="python">
  </div>
</div>

---

<div align="center">
  <table>
    <tr>
      <td width="50%">
        <h3>📦 主要功能</h3>
        <ul>
          <li>CRP包管理</li>
          <li>Git标签管理</li>
          <li>批量操作</li>
          <li>图标查找</li>
          <li>自动版本控制</li>
        </ul>
      </td>
      <td width="50%">
        <h3>⚡ 特色</h3>
        <ul>
          <li>一键安装</li>
          <li>配置集中管理</li>
          <li>智能补全</li>
          <li>安全升级</li>
          <li>完善的文档</li>
        </ul>
      </td>
    </tr>
  </table>
</div>

## 📦 快速开始

### 1️⃣ 一键安装

复制执行下面的命令
```
curl -sSL https://raw.githubusercontent.com/18202781743/dev-tool/main/install-from-github.sh | bash
```

### 2️⃣ 配置信息
```bash
# 🛠 使用config命令编辑配置
dev-tool config crp    # 编辑CRP配置
dev-tool config git    # 编辑Git标签配置
dev-tool config crp set auth.password="xxx"  # 直接编辑
```

### 3️⃣ 本地安装
```bash
# 📥 克隆仓库
git clone https://github.com/18202781743/dev-tool.git
cd dev-tool

./install.sh
```

### 🔄 升级工具
```bash
dev-tool upgrade
```

> 💡 提示：配置文件存储在 ~/.config/dev-tool/ 目录下

---

## 使用前须知

1. 安装并登录github cli 工具 -> https://cli.github.com/
2. 安装git
3. 使用前需要正确配置dev-tool的github账户和维护者邮箱
4. 若需要CRP打包,则需要在配置中设置CRP的账户和密码

## 🛠 使用示例

### 🔧 CRP包管理
```bash
# 📦 打包项目
dev-tool crp pack --topic DDE-V25-20250116 --name deepin-desktop-theme-v25 --branch upstream/master

# 🔍 查询项目
dev-tool crp projects --name deepin-desktop-theme

# 📌 查询测试主题
dev-tool crp topics --topic DDE-V25-20250116

# 📋 查询已打包列表
dev-tool crp instances --topic DDE-V25-20250116

# 🌿 查询项目分支
dev-tool crp branches --topic DDE-V25-20250116 --name deepin-desktop-theme-v25

# 🧪 测试打包
dev-tool crp test --topic DDE-V25-20250116 --name deepin-desktop-theme-v25

# 📄 生成转测文档(模板文件 `crp-gendoc.xlsx`，可放在当前目录或 `~/.config/dev-tool/` 目录下，或通过`--template`参数指定路径。)
dev-tool crp gendoc --topic DDE-V25-20250623
dev-tool crp gendoc --topic DDE-V25-20250623 --template /path/to/测试-桌面专业版-转测申请单.xlsx

# 🏭 批量打包项目 (使用配置文件)
dev-tool batch-crp pack --config batch-package-crp-config.json

# 🧪 批量测试打包
dev-tool batch-crp test --config batch-package-crp-config.json
```

### 🔧 Git标签管理
```bash
# 🏷 创建新标签 (自动递增版本号)
dev-tool git tag --name deepin-desktop-theme-v25 --org linuxdeepin

# 🏷 指定版本号创建标签
dev-tool git tag --name deepin-desktop-theme-v25 --org linuxdeepin --tag 1.1.1

# 🔄 合并标签PR
dev-tool git merge --name deepin-desktop-theme-v25

# 🧪 测试标签变更
dev-tool git test --name deepin-desktop-theme-v25

# 🔍 查看最新标签
dev-tool git lasttag --name deepin-desktop-theme-v25

# 🚀 触发自动发布 (使用GitHub Auto Release workflow)
dev-tool git release --name deepin-desktop-theme-v25 --org linuxdeepin

# 🏷 批量创建标签 (使用配置文件)
dev-tool batch-git tag --config batch-git-config.json

# 🔄 批量合并标签PR
dev-tool batch-git merge --config batch-git-config.json

# 🧪 测试批量标签变更
dev-tool batch-git test --config batch-git-config.json

# 🔍 查看批量最新标签
dev-tool batch-git lasttag --config batch-git-config.json

# 🚀 批量触发自动发布
dev-tool batch-git release --config batch-git-config.json
```

### 🎨 图标查找管理
```bash
# 🔍 查找deepin系统图标
dev-tool findicon deepin-music

# 🔍 查找应用程序图标
dev-tool findicon deepin-terminal

# 🔍 查找系统图标
dev-tool findicon user-home

# 🔍 查找主题图标
dev-tool findicon applications-multimedia

# ❓ 查看帮助信息
dev-tool findicon --help
```

### 🔍 常用参数
```bash
# CRP参数
--topic   测试主题名称 (必填)
--name    项目名称 (必填)
--branch  分支名称 (默认: upstream/master)

# Batch-CRP参数
--config  配置文件路径 (必填)
--topic   测试主题名称 (可选)
--branch  分支名称 (默认: upstream/master)

# Git参数
--name    项目名称 (必填)
--org     组织名称 (默认: linuxdeepin)
--branch  分支名称 (默认: master)
--tag     指定版本号 (不指定则自动递增)
--reviewer 评审人员 (可多个)

# Git Release参数
--name    项目名称 (必填)
--org     组织名称 (默认: linuxdeepin)

# Batch-Git参数
--config  配置文件路径 (必填)
--org     组织名称 (默认: linuxdeepin)
--branch  分支名称 (默认: master)
--tag     指定版本号 (不指定则自动递增)
--reviewer 评审人员 (可多个)

# findicon参数
icon-name 图标名称 (必填)
--help    显示帮助信息
```

### ⚙️ 配置管理
```bash
# 编辑CRP配置
dev-tool config crp

# 编辑Git标签配置
dev-tool config git
```

---

## 📌 使用提示

<div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;">
  <div style="flex: 1; min-width: 200px; padding: 15px; background: #f8f9fa; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
    <h4>🌐 网络连接</h4>
    <p>确保网络连接正常，特别是访问CRP和GitHub时</p>
  </div>
  
  <div style="flex: 1; min-width: 200px; padding: 15px; background: #f8f9fa; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
    <h4>🔐 权限管理</h4>
    <p>需要有CRP和GitHub的相应权限才能执行操作</p>
  </div>
  
  <div style="flex: 1; min-width: 200px; padding: 15px; background: #f8f9fa; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
    <h4>📝 日志查看</h4>
    <p>操作日志保存在 ~/.cache/dev-tool.log</p>
  </div>
  
  <div style="flex: 1; min-width: 200px; padding: 15px; background: #f8f9fa; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
    <h4>🎨 图标依赖</h4>
    <p>findicon功能需要安装libdtk6gui-bin和qtxdg-dev-tools包</p>
  </div>
</div>

---

## 🤝 贡献指南

<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
  <h3 style="text-align: center;">欢迎贡献！</h3>
  <p style="text-align: center;">我们欢迎各种形式的贡献：</p>
  
  <div style="display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin: 20px 0;">
    <div style="flex: 1; min-width: 200px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
      <h4>🐛 报告问题</h4>
      <p>提交Issue报告bug或建议</p>
    </div>
    
    <div style="flex: 1; min-width: 200px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
      <h4>💻 代码贡献</h4>
      <p>提交PR改进代码</p>
    </div>
    
    <div style="flex: 1; min-width: 200px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)">
      <h4>📖 文档改进</h4>
      <p>完善使用文档和示例</p>
    </div>
  </div>
</div>

---

## 📄 许可证

本项目使用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
