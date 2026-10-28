#!/usr/bin/env bash
# zgp-video-skills 安裝程式（macOS／Linux／WSL）
#   curl -fsSL https://raw.githubusercontent.com/gtc65/zgp-video-skills/main/install/install.sh | bash
set -euo pipefail
REPO="gtc65/zgp-video-skills"
SKILLS="taiwan-narration photo-recap-video hyperframes-explainer"
tmp="$(mktemp -d)"
curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$tmp"
src="$(find "$tmp" -maxdepth 1 -mindepth 1 -type d | head -1)/plugins/school-video/skills"
dst="$HOME/.claude/skills"; mkdir -p "$dst"
for s in $SKILLS; do rm -rf "$dst/$s"; cp -R "$src/$s" "$dst/$s"; echo "已安裝技能：$s"; done
rm -rf "$tmp"
command -v ffmpeg >/dev/null || echo "⚠ 沒有 ffmpeg（Ubuntu：sudo apt install ffmpeg；macOS：brew install ffmpeg）"
command -v fluidsynth >/dev/null || echo "（選用）照片回顧片配樂需要 fluidsynth＋fluid-soundfont-gm"
if command -v python3 >/dev/null; then
  python3 -m pip install --user --upgrade edge-tts pillow fonttools brotli numpy mido playwright || \
  python3 -m pip install --break-system-packages --upgrade edge-tts pillow fonttools brotli numpy mido playwright
fi
echo "完成！重新開啟 Claude Code 即可使用。"
