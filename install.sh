#!/usr/bin/env bash
# Install python-quality-review skill into Claude Code skills directory.
#
# Usage:
#   ./install.sh                # user-level (~/.claude/skills)
#   ./install.sh /path/to/proj  # project-level (<proj>/.claude/skills)
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -f "$REPO_DIR/SKILL.md" ]]; then
  echo "❌ Cannot find SKILL.md at $REPO_DIR" >&2
  exit 1
fi

if [[ $# -ge 1 ]]; then
  TARGET="$1/.claude/skills/python-quality-review"
else
  TARGET="$HOME/.claude/skills/python-quality-review"
fi

mkdir -p "$(dirname "$TARGET")"

if [[ -e "$TARGET" ]]; then
  echo "⚠️  $TARGET already exists. Remove it first or pick another target." >&2
  exit 1
fi

mkdir -p "$TARGET"
cp "$REPO_DIR/SKILL.md" "$TARGET/"
cp -R "$REPO_DIR/references" "$TARGET/"
if [[ -d "$REPO_DIR/scripts" ]]; then
  cp -R "$REPO_DIR/scripts" "$TARGET/"
fi

echo "✅ Installed to $TARGET"
echo ""
echo "Now restart Claude Code and say:"
echo "  python-quality-review: 全面审查当前项目"
echo ""
echo "预检脚本（零依赖，可直接拷到被审项目跑）："
echo "  python $TARGET/scripts/preflight.py /path/to/project --min-severity P1"
