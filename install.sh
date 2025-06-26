#!/bin/bash

set -e

# 检查并安装python3-venv
if ! dpkg -s python3-venv &> /dev/null; then
    echo "Installing python3-venv..."
    sudo apt install -y python3-venv
else
    echo "python3-venv is already installed, skipping..."
fi

# 设置用户本地bin目录
USER_BIN="$HOME/.local/bin"
mkdir -p "$USER_BIN"

# 检测并设置PATH
USER_BIN="$HOME/.local/bin"
mkdir -p "$USER_BIN"

# 检查PATH是否已包含$USER_BIN
path_exists_in_env=$(echo ":$PATH:" | grep -q ":$USER_BIN:" && echo "yes" || echo "no")

if [[ "$path_exists_in_env" == "no" ]]; then
    current_shell=$(basename "$SHELL")
    
    # 检查各shell配置文件是否已设置
    case "$current_shell" in
        bash)
            config_file="$HOME/.bashrc"
            path_line="export PATH=\"\$PATH:$USER_BIN\""
            ;;
        zsh)
            config_file="$HOME/.zshrc"
            path_line="export PATH=\"\$PATH:$USER_BIN\""
            ;;
        fish)
            config_file="$HOME/.config/fish/config.fish"
            path_line="set -gx PATH \$PATH $USER_BIN"
            ;;
        *)
            config_file="$HOME/.bashrc"
            path_line="export PATH=\"\$PATH:$USER_BIN\""
            ;;
    esac

    # 检查配置文件是否已包含该路径
    if [[ ! -f "$config_file" ]] || ! grep -qF "$USER_BIN" "$config_file"; then
        echo "$path_line" >> "$config_file"
    fi
    
    export PATH="$PATH:$USER_BIN"
fi

# 检查并设置虚拟环境
VENV_DIR="$HOME/.local/venv"
REQUIREMENTS="$(dirname "$(readlink -f "$0")")/requirements.txt"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    
fi
# 安装依赖
if [[ -f "$REQUIREMENTS" ]]; then
    source "$VENV_DIR/bin/activate"
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    pip install -r "$REQUIREMENTS"
    deactivate
else
    echo "Warning: requirements.txt not found, skipping dependency installation"
fi

# 安装脚本到用户目录
chmod +x ./dev-tool ./deepin-iconfinder ./package-crp.py ./git-tag.py ./batch-git-tag.py ./batch-package-crp.py ./gen-crp-pwd.py
cp ./dev-tool "$USER_BIN/dev-tool"
cp ./deepin-iconfinder "$USER_BIN/deepin-iconfinder"
cp ./package-crp.py "$USER_BIN/package-crp.py"
cp ./git-tag.py "$USER_BIN/git-tag.py"
cp ./batch-git-tag.py "$USER_BIN/batch-git-tag.py"
cp ./batch-package-crp.py "$USER_BIN/batch-package-crp.py"
cp ./gen-crp-pwd.py "$USER_BIN/gen-crp-pwd.py"

# 安装自动补全脚本到用户目录
COMPLETION_DIR="$HOME/.config/dev-tool/completions"
mkdir -p "$COMPLETION_DIR"

if [ -n "$BASH_VERSION" ]; then
    cp ./dev-tool-completion.bash "$COMPLETION_DIR/dev-tool"
    if ! grep -q "source \"$COMPLETION_DIR/dev-tool\"" ~/.bashrc; then
        echo "# dev-tool completion" >> ~/.bashrc
        echo "source \"$COMPLETION_DIR/dev-tool\"" >> ~/.bashrc
    fi
    echo "Bash completion installed to $COMPLETION_DIR/dev-tool"
    echo "Please run: source ~/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
    # Ensure completion directory exists
    mkdir -p "$COMPLETION_DIR"
    
    # Install completion script with proper name
    cp ./dev-tool-completion.zsh "$COMPLETION_DIR/_dev-tool"
    chmod +x "$COMPLETION_DIR/_dev-tool"
    
    # Install argcomplete for Python command completion
    if ! "$VENV_DIR/bin/pip" show argcomplete &> /dev/null; then
        "$VENV_DIR/bin/pip" install argcomplete
    fi
    "$VENV_DIR/bin/activate-global-python-argcomplete" --user
    
    # Add to fpath if not already present
    if ! grep -q "fpath+=(\"$COMPLETION_DIR\")" ~/.zshrc; then
        echo "# dev-tool completion" >> ~/.zshrc
        echo "fpath+=(\"$COMPLETION_DIR\")" >> ~/.zshrc
        echo "autoload -Uz compinit" >> ~/.zshrc
        echo "compinit -i -d ~/.zcompdump" >> ~/.zshrc
    fi
    
    echo "Zsh completion installed to $COMPLETION_DIR/_dev-tool"
    echo "To activate completion, run:"
    echo "  rm -f ~/.zcompdump*"
    echo "  exec zsh -l"
    echo "Or open a new terminal"
fi

# 安装配置文件和packages到标准目录
CONFIG_DIR="$HOME/.config/dev-tool"
mkdir -p "$CONFIG_DIR"

# 检查配置文件是否会被覆盖
for config in package-crp-config.json git-tag-config.json; do
    if [ -f "$CONFIG_DIR/$config" ] && [ -f "./$config" ]; then
        echo "Warning: $config already exists in $CONFIG_DIR"
        read -p "Overwrite? [y/N] " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "Skipping $config installation"
            continue
        fi
    fi
    cp "./$config" "$CONFIG_DIR/"
done

# 安装packages目录下的文件（直接覆盖）
PACKAGES_DIR="$CONFIG_DIR/packages"
mkdir -p "$PACKAGES_DIR"
for pkg in packages/*; do
    cp -f "$pkg" "$PACKAGES_DIR/"
done

echo "##################### 安装完成 #####################"
echo ""
echo "已安装的工具："
echo "  - dev-tool: 主工具"
echo "  - deepin-iconfinder: 图标查找工具"
echo ""

# 根据当前shell自动source对应的配置文件
if [ -n "$BASH_VERSION" ]; then
    source ~/.bashrc
elif [ -n "$ZSH_VERSION" ]; then
    source ~/.zshrc
elif [ -n "$FISH_VERSION" ]; then
    source ~/.config/fish/config.fish
else
    source ~/.bashrc
fi
