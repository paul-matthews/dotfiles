# Work machines: Antigravity (jetski) tabs get the same treatment as Claude tabs.
# jc is usually an alias from ~/.localrc, so it is registered here and wrapped
# by _ai_tabs_finalize at the end of zshrc, after ~/.localrc has loaded.
_AI_TAB_CMDS+=(jc:JETSKI)
jc() { _ai_tab_wrap jc JETSKI "$@"; }
