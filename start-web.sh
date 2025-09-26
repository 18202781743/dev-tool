#!/bin/bash

# Web开发工具套件启动脚本

# 检查Python版本
python3 --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$SCRIPT_DIR/web"

echo "🚀 启动Web开发工具套件..."

# 检查web目录是否存在
if [ ! -d "$WEB_DIR" ]; then
    echo "错误: web目录不存在"
    exit 1
fi

# 进入web目录
cd "$WEB_DIR"

# 检查requirements.txt是否存在
if [ ! -f "requirements.txt" ]; then
    echo "错误: requirements.txt不存在"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误: 创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📋 安装Python依赖..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 安装依赖失败"
    exit 1
fi

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    echo "⚠️  配置文件不存在，将使用默认配置"
    echo "   请访问 http://localhost:5000/config 进行配置"
fi

# 启动应用
echo "🌐 启动Web应用..."
echo "   访问地址: http://localhost:5000"
echo "   按 Ctrl+C 停止服务"
echo ""

python app.py