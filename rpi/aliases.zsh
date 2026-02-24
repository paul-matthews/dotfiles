# RPi 5 helpers
# SSH: Add 'rpi5' host to ~/.ssh/config (not tracked — has keys/secrets context):
#   Host rpi5
#     HostName 192.168.50.3
#     User pmatthews
#     # IP may change — use: nmap -sn 192.168.50.0/24 | grep -i raspberry
alias rpi='ssh rpi5'
alias rpi-find='nmap -sn 192.168.50.0/24 | grep -B2 -i "raspberry\|dc:a6:32\|e4:5f:01\|2c:cf:67\|d8:3a:dd"'
alias rpi-sync='rsync -avz --exclude .git'
