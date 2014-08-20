alias reload!='. ~/.zshrc'

alias cls='clear' # Good 'ol Clear Screen command
alias mv='nocorrect mv'       # no spelling correction on mv
alias cp='nocorrect cp'       # no spelling correction on cp
alias mkdir='nocorrect mkdir' # no spelling correction on mkdir
alias pu=pushd
alias po=popd
alias d='dirs -v'
alias h=history
alias grep=egrep
alias ll='ls -l'
alias la='ls -a'

# List only directories and symbolic
# links that point to directories
alias lsd='ls -ld *(-/DN)'

# List only file beginning with "."
alias lsa='ls -ld .*'

alias gvimdiff="mvimdiff"
alias vim="vim -p"

# Global aliases -- These do not have to be
# at the beginning of the command line.
alias -g M='| more'
alias -g H='| head'
alias -g T='| tail'
alias -g L='| less'
alias -g G="| grep"
alias -g L="| less"

# copy with a progress bar.
alias cpv="rsync -poghb --backup-dir=/tmp/rsync -e /dev/null --progress --"
