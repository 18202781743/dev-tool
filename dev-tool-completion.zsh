#compdef dev-tool
#autoload

local curcontext="$curcontext" state line
typeset -A opt_args

_dev-tool() {
    _arguments -C \
        '1: :->command' \
        '*: :->args'

    case $state in
        (command)
            local -a commands
            commands=(
                'crp:Manage CRP packages'
                'git:Manage git tags' 
                'batch-git:Batch process git tags'
                'batch-crp:Batch process CRP packages'
                'config:Edit configuration'
                'upgrade:Upgrade dev-tool'
                'findicon:Find deepin system icons'
                'help:Show help'
            )
            _describe 'command' commands
            ;;
        (args)
            case $words[2] in
                (crp)
                    _arguments -C \
                        '1: :->crp_command' \
                        '*: :->crp_args'
                    
                    case $state in
                        (crp_command)
                            local -a crp_commands
                            crp_commands=(
                                'pack:Create CRP package'
                                'test:Test CRP package'
                                'projects:List projects'
                                'topics:List topics'
                                'instances:List instances'
                                'branches:List branches'
                            )
                            _describe 'crp command' crp_commands
                            ;;
                        (crp_args)
                            _arguments \
                                '--name[Package name]' \
                                '--topic[Topic name]' \
                                '--branch[Branch name]' \
                                '--tag[Tag name]' \
                                '--help[Show help]'
                            ;;
                    esac
                    ;;
                (git)
                    _arguments -C \
                        '1: :->git_command' \
                        '*: :->git_args'
                    
                    case $state in
                        (git_command)
                            local -a git_commands
                            git_commands=(
                                'tag:Create git tag'
                                'merge:Merge git PR'
                                'test:Test git tag'
                                'lasttag:Show last git tag'
                            )
                            _describe 'git command' git_commands
                            ;;
                        (git_args)
                            _arguments \
                                '--name[Project name]' \
                                '--org[Organization]' \
                                '--branch[Branch name]' \
                                '--tag[Tag name]' \
                                '--reviewer[Reviewer]' \
                                '--help[Show help]'
                            ;;
                    esac
                    ;;
                (batch-git)
                    _arguments -C \
                        '1: :->batch_git_command' \
                        '*: :->batch_git_args'
                    
                    case $state in
                        (batch_git_command)
                            local -a batch_git_commands
                            batch_git_commands=(
                                'tag:Create batch git tags'
                                'merge:Merge batch git PRs'
                                'test:Test batch git tags'
                                'lasttag:Show last batch git tags'
                            )
                            _describe 'batch-git command' batch_git_commands
                            ;;
                        (batch_git_args)
                            _arguments \
                                '--config[Config file]' \
                                '--org[Organization]' \
                                '--branch[Branch name]' \
                                '--tag[Tag name]' \
                                '--reviewer[Reviewer]' \
                                '--help[Show help]'
                            ;;
                    esac
                    ;;
                (batch-crp)
                    _arguments -C \
                        '1: :->batch_crp_command' \
                        '*: :->batch_crp_args'
                    
                    case $state in
                        (batch_crp_command)
                            local -a batch_crp_commands
                            batch_crp_commands=(
                                'pack:Create batch CRP packages'
                                'test:Test batch CRP packages'
                            )
                            _describe 'batch-crp command' batch_crp_commands
                            ;;
                        (batch_crp_args)
                            _arguments \
                                '--config[Config file]' \
                                '--topic[Topic name]' \
                                '--branch[Branch name]' \
                                '--tag[Tag name]' \
                                '--help[Show help]'
                            ;;
                    esac
                    ;;
                (findicon)
                    _arguments \
                        '--help[Show help]' \
                        '*:icon-name: '
                    ;;
                (config)
                    _arguments \
                        '1: :(crp git batch-git batch-crp)'
                    ;;
            esac
            ;;
    esac
}

compdef _dev-tool dev-tool
