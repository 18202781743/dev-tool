#!/bin/bash

set -e

# 一键安装命令：
# curl -sSL https://raw.githubusercontent.com/18202781743/dev-tool/main/install-from-github.sh | bash
# 或
# wget -qO- https://raw.githubusercontent.com/18202781743/dev-tool/main/install-from-github.sh | bash

REPO_URL="https://github.com/18202781743/dev-tool.git"
INSTALL_DIR="$HOME/.local/share/dev-tool"
BIN_DIR="$HOME/.local/bin"

# 确保必要的依赖已安装
echo "Checking basic dependencies..."

# 检查并安装git
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    sudo apt-get update
    sudo apt-get install -y git
fi

# 检查并安装curl（用于下载）
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    sudo apt-get update
    sudo apt-get install -y curl
fi

# 克隆或更新仓库
echo "Installing dev-tool from GitHub..."
if [ ! -d "$INSTALL_DIR" ]; then
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    cd "$INSTALL_DIR"
    git pull origin main
fi

# 执行安装
cd "$INSTALL_DIR"
chmod +x install.sh
./install.sh

# 创建快捷命令
if [ ! -f "$BIN_DIR/dev-tool" ]; then
    ln -sf "$INSTALL_DIR/dev-tool" "$BIN_DIR/dev-tool"
fi

echo -e "\nDev-tool installed successfully!"
echo "Run 'dev-tool --help' to get started"
