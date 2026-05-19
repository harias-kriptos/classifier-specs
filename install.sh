#!/usr/bin/env bash
# install.sh — instala los comandos globales de Claude Code de classifier-specs.
#
# Después de correr esto, los comandos /brainstorm, /spec, /plan, /implement y
# /review quedan disponibles en CUALQUIER repo donde el dev abra Claude Code,
# sin tocar ese repo.
#
# Estrategia: symlinks desde ~/.claude/commands/*.md → este repo.
# Cuando hagas `git pull` en este repo, los comandos quedan actualizados solos.
#
# Uso:
#   cd ~/path/to/classifier-specs
#   ./install.sh
#
# Para actualizar:
#   cd ~/path/to/classifier-specs && git pull
#   (los symlinks ya apuntan acá, no hay que reinstalar)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_CMD_DIR="$HOME/.claude/commands"

COMMANDS=(
  "brainstorm"
  "spec"
  "plan"
  "implement"
  "review"
)

echo "==> Installing classifier-specs commands from: $REPO_DIR"
echo "==> Target: $GLOBAL_CMD_DIR"
echo ""

mkdir -p "$GLOBAL_CMD_DIR"

for cmd in "${COMMANDS[@]}"; do
  src="$REPO_DIR/.claude/commands/${cmd}.md"
  dst="$GLOBAL_CMD_DIR/${cmd}.md"

  if [ ! -f "$src" ]; then
    echo "    [skip] $cmd: source not found ($src)"
    continue
  fi

  if [ -L "$dst" ] || [ -f "$dst" ]; then
    existing="$(readlink "$dst" 2>/dev/null || echo "")"
    if [ "$existing" = "$src" ]; then
      echo "    [ok]   /$cmd (already linked)"
      continue
    fi
    echo "    [warn] /$cmd existe pero apunta a otro lado: $existing"
    read -r -p "           ¿Sobrescribir? [y/N] " yn
    if [ "$yn" != "y" ] && [ "$yn" != "Y" ]; then
      echo "    [skip] /$cmd"
      continue
    fi
    rm "$dst"
  fi

  ln -s "$src" "$dst"
  echo "    [+]    /$cmd → $src"
done

echo ""
echo "==> Done. Comandos disponibles en Claude Code dentro de cualquier repo:"
echo "      /brainstorm    refina un ticket (Skill 01)"
echo "      /spec          genera spec + threat model (Skill 02)"
echo "      /plan          descompone en todo.md TDD-ready (Skill 03)"
echo "      /implement     ejecuta el loop TDD + tdd-trace.md (Skill 04)"
echo "      /review        valida gates y emite READY/BLOCKED (Skill 05)"
echo ""
echo "Para actualizar los comandos:"
echo "      cd $REPO_DIR && git pull"
