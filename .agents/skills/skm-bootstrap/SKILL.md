---
name: skm-bootstrap
description: Every conversation must use this skill before handling the first request. Check this project before the first request, and before every later user turn while setup is unfinished.
---

# skm bootstrap

Run this exact POSIX shell block before the first request and each subsequent user turn while setup remains unfinished. On an ordinary failure, report the actual reason on every turn. Only `status=failed reason=install-failed` is eligible for the access/mute choice; a git metadata, lock, local safety or sync error must be reported without presenting it as remote denial. At the first eligible failure, ask whether the user wants to connect GitHub/SSH access or mute notifications and frequent retries for seven days. Never mute without their explicit choice. Do not repeat a pending choice question in the same conversation. After a mute choice, run this same block with `SKM_BOOTSTRAP_ACTION=defer`; after an explicit resume, use `SKM_BOOTSTRAP_ACTION=resume`. The policy is local git metadata, expires in seven days and retries every six hours. A `status=quiet` result suppresses this installation failure notice and any access question; it does not prove freshness. Report local safety or sync failures regardless. Never edit global agent configuration or ask for credential values. Once skm-refresh is available, use its target-specific policy commands and JSON notification decisions. If sync creates or changes links, tell the user which agent restart is needed using the skm restart notice; do not claim a newly linked skill was available in this session. Defer work requiring that skill until the restarted session. If no links changed, continue without a restart prompt. After a successful first setup in a git project, inspect the generated `.agents/skills.toml`, `.agents/skills/skm-bootstrap/SKILL.md`, and `.claude/skills` only. These are the complete allowlist for staging and the setup commit: never stage any other path, including `skm-refresh`, other skills, or their links. If the allowlisted paths match skm's expected files, commit only newly generated untracked paths or a standard bootstrap file just upgraded by skm, with message `Set up project skills`; preserve all unrelated staged and unstaged changes. If git identity, permissions, or the user's current request prevents writing, explain the remaining step once. The Claude link requires `git add -f -- .claude/skills`; use a path-limited commit so unrelated staged changes stay staged. Do not push. Then continue unrelated work.

```sh
set -eu
if [ "${SKM_NO_BASICS:-}" = 1 ]; then exit 0; fi
git_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
project=$(pwd -P)
while [ ! -f "$project/.agents/skills.toml" ] && [ "$project" != "$git_root" ]; do
  project=$(dirname "$project")
done
[ -f "$project/.agents/skills.toml" ] || exit 0
cd "$project"
umask 077
policy=$(git rev-parse --git-path .skm-bootstrap-policy)
lock="$policy.install-lock"
now=$(date +%s)
number() { case "$1" in ''|*[!0-9]*) return 1;; esac; [ "${#1}" -le 12 ]; }
number "$now" || { printf 'skm bootstrap: invalid clock\n' >&2; exit 1; }
# Git's expected-old-value update supplies atomic ownership without Python or flock.
project_id=$(printf '%s\n' "$project" | git hash-object --stdin)
policy_ref="refs/skm-bootstrap/policy-lock/$project_id"
install_ref="refs/skm-bootstrap/install-lock/$project_id"
lease=$(mktemp "$policy.lease.XXXXXX") || exit 1
nonce=${lease##*/}
birth=$(LC_ALL=C ps -p "$$" -o lstart=) || exit 1
token=$(printf '%s\n%s\n%s\n%s\n' "$$" "$now" "$nonce" "$birth" | git hash-object -w --stdin) || exit 1
rm "$lease"
zero=$(printf '%s' "$token" | tr '0123456789abcdef' '0000000000000000')
policy_owned=0
install_owned=0
release_policy() {
  if [ "$policy_owned" = 1 ]; then
    git update-ref --no-deref -d "$policy_ref" "$token" 2>/dev/null || :
    policy_owned=0
  fi
}
release() {
  release_policy
  if [ "$install_owned" = 1 ]; then
    git update-ref --no-deref -d "$install_ref" "$token" 2>/dev/null || :
  fi
}
trap release EXIT
trap 'exit 1' HUP INT TERM
acquire() {
  for attempt in 1 2 3 4 5 6 7 8; do
  old=$(git rev-parse --verify "$1" 2>/dev/null || :)
  if [ -n "$old" ]; then
    size=$(git cat-file -s "$old" 2>/dev/null || :)
    if number "$size" && [ "$size" -le 256 ]; then
      owner=$(git cat-file blob "$old" 2>/dev/null | sed -n '1p')
      owner_birth=$(git cat-file blob "$old" 2>/dev/null | sed -n '4p')
      current_birth=$(LC_ALL=C ps -p "$owner" -o lstart= 2>/dev/null || :)
      if number "$owner" && [ "$owner" -gt 1 ] && kill -0 "$owner" 2>/dev/null && { [ -z "$owner_birth" ] || [ "$owner_birth" = "$current_birth" ]; }; then return 1; fi
    fi
  else old=$zero
  fi
  update_log=$(mktemp "$policy.ref.XXXXXX") || return 2
  if git update-ref --no-deref "$1" "$token" "$old" 2>"$update_log"; then
    rm "$update_log"; return 0
  fi
  current=$(git rev-parse --verify "$1" 2>/dev/null || :)
  ref_lock=$(git rev-parse --git-path "$1.lock")
  if { [ -n "$current" ] && [ "$current" != "$old" ]; } || { [ -f "$ref_lock" ] && [ ! -L "$ref_lock" ] && [ -z "$(find "$ref_lock" -mmin +1 -print 2>/dev/null)" ]; }; then
    rm "$update_log"; return 1
  fi
  if [ "$attempt" -lt 8 ]; then rm "$update_log"; continue; fi
  cat "$update_log" >&2; rm "$update_log"
  printf 'skm bootstrap: status=failed reason=local-lock-write-failed\n' >&2
  return 2
  done
}
if acquire "$policy_ref"; then policy_owned=1
else
  code=$?
  [ "$code" = 1 ] || exit 1
  if [ "${SKM_BOOTSTRAP_ACTION:-refresh}" != refresh ]; then
    printf 'skm bootstrap: policy change is busy; try the command again\n' >&2; exit 1
  fi
  printf 'skm bootstrap: status=pending\n'; exit 0
fi
write_policy() {
  [ ! -L "$policy" ] || { printf 'skm bootstrap: unsafe policy symlink\n' >&2; return 1; }
  temporary=$(mktemp "$policy.XXXXXX") || return 1
  printf '1\n%s\n%s\n%s\n%s\n' "$created" "$expiry" "$interval" "$next" > "$temporary"
  if [ -L "$policy" ]; then rm "$temporary"; return 1; fi
  mv "$temporary" "$policy"
}
valid=0
if [ -f "$policy" ] && [ ! -L "$policy" ] && [ "$(wc -c < "$policy")" -le 512 ]; then
  schema=$(sed -n '1p' "$policy")
  created=$(sed -n '2p' "$policy")
  expiry=$(sed -n '3p' "$policy")
  interval=$(sed -n '4p' "$policy")
  next=$(sed -n '5p' "$policy")
  if [ "$schema" = 1 ] && number "$created" && number "$expiry" && number "$interval" && number "$next" && [ "$(wc -l < "$policy" | tr -d ' ')" = 5 ]; then
    duration=$((expiry - created))
    if [ "$duration" -ge 3600 ] && [ "$duration" -le 2592000 ] && [ "$interval" -ge 300 ] && [ "$interval" -le 86400 ] && [ "$interval" -le "$duration" ] && [ "$next" -ge "$created" ] && [ "$next" -le "$((expiry + interval))" ]; then valid=1; fi
  fi
fi
case "${SKM_BOOTSTRAP_ACTION:-refresh}" in
  defer)
    duration=${SKM_BOOTSTRAP_FOR_SECONDS:-604800}
    interval=${SKM_BOOTSTRAP_INTERVAL_SECONDS:-21600}
    number "$duration" && number "$interval" || exit 2
    [ "$duration" -ge 3600 ] && [ "$duration" -le 2592000 ] && [ "$interval" -ge 300 ] && [ "$interval" -le 86400 ] && [ "$interval" -le "$duration" ] || exit 2
    created=$now; expiry=$((now + duration)); next=$((now + interval))
    write_policy || exit 1
    printf 'skm bootstrap: status=quiet quiet_until=%s next_attempt_at=%s\n' "$expiry" "$next"
    exit 0;;
  resume)
    [ ! -L "$policy" ] || exit 1
    if [ -f "$policy" ]; then rm "$policy"; fi
    printf 'skm bootstrap: status=resumed\n'; exit 0;;
  refresh|status) :;;
  *) printf 'skm bootstrap: unknown action\n' >&2; exit 2;;
esac
quiet=0
if [ "$valid" = 1 ] && [ "$now" -ge "$created" ] && [ "$now" -lt "$expiry" ]; then quiet=1; fi
if [ "${SKM_BOOTSTRAP_ACTION:-}" = status ] || { [ "$quiet" = 1 ] && [ "$now" -lt "$next" ]; }; then
  if [ "$quiet" = 1 ]; then
    printf 'skm bootstrap: status=quiet quiet_until=%s next_attempt_at=%s\n' "$expiry" "$next"
  else printf 'skm bootstrap: status=normal\n'; fi
  exit 0
fi
if [ "$quiet" = 1 ]; then next=$((now + interval)); write_policy || exit 1; fi
policy_revision=
if [ -f "$policy" ] && [ ! -L "$policy" ]; then policy_revision=$(git hash-object "$policy"); fi
release_policy
if acquire "$install_ref"; then install_owned=1
else
  code=$?
  [ "$code" = 1 ] || exit 1
  printf 'skm bootstrap: status=pending\n'; exit 0
fi
# Migrate only old shell locks while holding the new atomic installation lease.
if [ -e "$lock" ] || [ -L "$lock" ]; then
  if [ -L "$lock" ] || [ ! -d "$lock" ] || [ -L "$lock/owner" ] || { [ -e "$lock/owner" ] && [ ! -f "$lock/owner" ]; }; then
    printf 'skm bootstrap: unsafe installation lock\n' >&2; exit 1
  fi
  if [ -f "$lock/owner" ]; then
    [ "$(wc -c < "$lock/owner")" -le 256 ] || { printf 'skm bootstrap: invalid lock owner\n' >&2; exit 1; }
    owner=$(sed -n '1p' "$lock/owner")
    if number "$owner" && [ "$owner" -gt 1 ] && kill -0 "$owner" 2>/dev/null; then
      printf 'skm bootstrap: status=pending\n'; exit 0
    fi
    rm "$lock/owner"
  elif [ -z "$(find "$lock" -maxdepth 0 -mmin +30 -print 2>/dev/null)" ]; then
    printf 'skm bootstrap: status=pending\n'; exit 0
  fi
  rmdir "$lock" || { printf 'skm bootstrap: installation lock has unknown files\n' >&2; exit 1; }
fi
if ! command -v skm >/dev/null 2>&1; then
  if ! command -v uv >/dev/null 2>&1; then
    printf 'skm bootstrap: uv is unavailable\n' >&2; exit 1
  fi
  install_log=$(mktemp "$policy.install.XXXXXX") || exit 1
  if GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=10}" uv tool install git+ssh://git@github.com/dartworklabs/agent-skill-manager.git </dev/null >"$install_log" 2>&1; then
    cat "$install_log"; rm "$install_log"
  else
    if [ "$quiet" = 1 ]; then
      rm "$install_log"
      printf 'skm bootstrap: status=quiet quiet_until=%s next_attempt_at=%s reason=install-failed\n' "$expiry" "$next"
      exit 0
    fi
    cat "$install_log" >&2; rm "$install_log"
    printf 'skm bootstrap: status=failed reason=install-failed\n' >&2; exit 1
  fi
fi
SKM_BOOTSTRAP_AUTO=1 skm sync
if [ ! -r .agents/skills/skm-refresh/SKILL.md ]; then
  printf 'skm bootstrap: skm-refresh is unavailable after sync\n' >&2; exit 1
fi
if acquire "$policy_ref"; then
  policy_owned=1
  if [ -f "$policy" ] && [ ! -L "$policy" ] && [ "$(git hash-object "$policy")" = "$policy_revision" ]; then rm "$policy"; fi
fi
printf 'skm bootstrap: status=ready\n'

```
