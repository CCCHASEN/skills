#!/bin/bash
# My-AI Setup Script — 一键初始化自包含环境
# 完全可移植：基于脚本位置自动推导路径，复制到任何电脑可用
# 用法: cd <skill-dir> && bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
MEMORY_DIR="$SCRIPT_DIR/memory"

echo "=== My-AI 自包含环境初始化 ==="
echo "目录: $SCRIPT_DIR"
echo ""

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo "错误: 未找到 uv。请先安装 uv:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "--- Step 1: 创建虚拟环境 ---"
if [ -d "$VENV_DIR" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    uv venv --python 3.13 "$VENV_DIR"
    echo "虚拟环境创建完成"
fi

VENV_PY="$VENV_DIR/bin/python"

echo ""
echo "--- Step 2: 安装依赖 ---"
uv pip install chromadb jieba networkx --python "$VENV_PY"

echo ""
echo "--- Step 3: 验证安装 ---"
$VENV_PY -c "import chromadb, jieba, networkx; print('所有依赖安装成功')"

echo ""
echo "--- Step 4: 初始化 SessionDB ---"
$VENV_PY "$SCRIPTS_DIR/session_db.py" init

echo ""
echo "--- Step 5: 验证核心文件 ---"
for f in memory/identity/SOUL.md memory/identity/USER.md memory/knowledge/KNOWLEDGE.md memory/context/ACTIVE.md; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ $f (缺失)"
    fi
done

echo ""
echo "=== 初始化完成 ==="
echo ""
echo "使用方法:"
echo "  1. 对 Kimi CLI 说 'My AI' 激活模式"
echo "  2. 所有命令使用虚拟环境 Python:"
echo "     $VENV_PY scripts/my_ai_turn.py pre '<query>'"
echo "     $VENV_PY scripts/my_ai_turn.py post '<json>'"
echo ""
echo "可复制性:"
echo "  整个 $SCRIPT_DIR 文件夹可以复制到任何电脑"
echo "  在新电脑上运行 'bash setup.sh' 重新创建虚拟环境即可"
