# Runbook: give the work Linux box its own secrets key

Read `handoff/README.md` first. This runbook is for a machine that has already
completed `handoff/work-linux.md` and is on `master`.

Why: this machine's age key is a copy of the office Mac's, made during the old
setup, so the two machines count as one recipient. After this runbook the
Linux box has a key of its own and the office Mac keeps the original. Nothing
is removed from `.sops.yaml`.

`age-keygen` is needed to generate a key. On this machine it was unpacked into
`~/.local/bin`, so every step below starts by putting that on the PATH.

## 1. Confirm the starting state

```sh
export PATH="$HOME/.local/bin:$PATH"
bin/handoff note "runbook work-linux-rekey.md, run $(date +%F)"
git checkout master && bin/git-safe-pull
bin/handoff branch
bin/handoff capture "command -v age-keygen"
bin/handoff capture "bin/secrets status"
bin/handoff capture "ls -la ~/.age ~/.config/sops/age"
bin/handoff capture "grep -n SOPS_AGE_KEY_FILE ~/.localrc"
```

Expect: `age-keygen` found under `~/.local/bin`; `secrets status` shows
`public key: age1huzhkqpnun7ch5npze3x5wlz3z8ht3q0y77ut6c8mnnt98pq7eystfghnp`,
`recipient: yes` and `state: in sync`; key files at both `~/.age/key.txt` and
`~/.config/sops/age/keys.txt`; one `SOPS_AGE_KEY_FILE` line in `~/.localrc`.

If the public key is anything other than the one above, stop and report: this
machine already has its own key and this runbook does not apply.

## 2. Set the shared key aside

This step renames two files outside the repo. That is allowed here, by name,
as an exception to the README rule; nothing is deleted yet.

```sh
mv ~/.config/sops/age/keys.txt ~/.config/sops/age/keys.shared.txt
mv ~/.age/key.txt ~/.age/key.shared.txt
sed -i 's|^export SOPS_AGE_KEY_FILE=.*|# SOPS_AGE_KEY_FILE now defaults to ~/.config/sops/age/keys.txt (set in system/env.zsh)|' ~/.localrc
unset SOPS_AGE_KEY_FILE
bin/handoff capture "grep -n SOPS_AGE_KEY_FILE ~/.localrc; ls -la ~/.age ~/.config/sops/age"
```

Expect: the `.localrc` line is now a comment, and both directories hold only the
`*.shared.*` files.

## 3. Generate this machine's own key

```sh
bin/secrets keygen
bin/handoff capture "bin/secrets status"
```

Expect: `generated this machine's age key at .../.config/sops/age/keys.txt`, and
`secrets status` showing a **different** public key with `recipient: NO`. If it
says `adopted` instead, stop and report: a copy of the shared key is still
somewhere the tool looks.

`~/.localrc.secrets` is untouched and still holds the decrypted secrets, so the
shell keeps working while the new key waits to become a recipient.

## 4. Report and wait

```sh
bin/handoff key
bin/handoff result "done" "add my NEW key as a recipient: handoff/keys/$(bin/handoff id).age.pub (keep the old shared key in .sops.yaml, the office Mac uses it)"
bin/handoff report
bin/handoff commit
```

## After home has merged

You will be told to run again. This time the new key is a recipient.

```sh
export PATH="$HOME/.local/bin:$PATH"
git checkout master && bin/git-safe-pull && bin/handoff branch
bin/handoff capture "bin/secrets status"
bin/handoff capture "script/test"
```

Expect: `recipient: yes`, `state: in sync` (`gsp` pulls secrets after a pull),
and `script/test` ending in `PASS`. Only then remove the shared key copies. This
is the one deletion this runbook allows, of exactly these two files:

```sh
rm ~/.config/sops/age/keys.shared.txt ~/.age/key.shared.txt
bin/handoff capture "ls -la ~/.age ~/.config/sops/age"
bin/handoff result "done" "nothing"
bin/handoff report
bin/handoff commit
```

If `secrets status` did not say `recipient: yes`, do not delete anything: report
`stopped at step 5` with the status output.
