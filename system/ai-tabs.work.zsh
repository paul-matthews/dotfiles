# Work machines: Antigravity's internal build (jetski, usually reached through
# the jc alias from ~/.localrc) gets the same treatment as Claude tabs. The
# names are registered here and wrapped by _ai_tabs_finalize at the end of
# zshrc, after ~/.localrc has loaded, so an alias is converted, not shadowed.
_AI_TAB_CMDS+=(jc:JETSKI jetski:JETSKI)
