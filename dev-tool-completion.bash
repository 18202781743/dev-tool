# bash completion for dev-tool

_dev-tool() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        dev-tool)
            COMPREPLY=( $(compgen -W "crp git batch-git batch-crp config upgrade findicon help" -- "$cur") )
            return 0
            ;;
        crp)
            COMPREPLY=( $(compgen -W "pack test projects topics instances branches gendoc" -- "$cur") )
            return 0
            ;;
        git)
            COMPREPLY=( $(compgen -W "tag merge test lasttag" -- "$cur") )
            return 0
            ;;
        batch-git)
            COMPREPLY=( $(compgen -W "tag merge test lasttag" -- "$cur") )
            return 0
            ;;
        batch-crp)
            COMPREPLY=( $(compgen -W "pack test" -- "$cur") )
            return 0
            ;;
        findicon)
            # 只补全选项，不补全图标名称以避免误导
            return 0
            ;;
    esac

    case ${words[1]} in
        crp)
            _dev-tool_crp
            ;;
        git)
            _dev-tool_git
            ;;
        batch-git)
            _dev-tool_batch_git
            ;;
        batch-crp)
            _dev-tool_batch_crp
            ;;
        findicon)
            _dev-tool_findicon
            ;;
    esac
}

_dev-tool_crp() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        --name|--topic|--branch|--tag)
            return 0
            ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=( $(compgen -W "--name --topic --branch --tag --help" -- "$cur") )
    fi
}

_dev-tool_git() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        --name|--org|--branch|--tag|--reviewer)
            return 0
            ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=( $(compgen -W "--name --org --branch --tag --reviewer --help" -- "$cur") )
    fi
}

_dev-tool_batch_git() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        --config|--org|--branch|--tag|--reviewer)
            return 0
            ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=( $(compgen -W "--config --org --branch --tag --reviewer --help" -- "$cur") )
    fi
}

_dev-tool_batch_crp() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        --config|--topic|--branch|--tag)
            return 0
            ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=( $(compgen -W "--config --topic --branch --tag --help" -- "$cur") )
    fi
}

_dev-tool_findicon() {
    local cur prev words cword
    _init_completion || return

    # 只为选项参数提供补全，不为图标名称提供补全
    if [[ $cur == -* ]]; then
        COMPREPLY=( $(compgen -W "--help" -- "$cur") )
    fi
    # 对于图标名称不提供补全，让用户自己输入
}

complete -F _dev-tool dev-tool
