#!/usr/bin/env python3
"""通用工具函数"""

import json
import re
import subprocess
from pathlib import Path

from config import PYTHON, SCRIPT_DIR


def run_cmd(cmd_list, cwd=None):
    try:
        result = subprocess.run(
            cmd_list, capture_output=True, text=True, cwd=cwd, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_script(script_name, *args):
    return run_cmd([PYTHON, str(SCRIPT_DIR / script_name), *args])


def estimate_tokens_fast(text):
    """快速估算 token 数（无需 subprocess）
    
    规则：
    - 英文单词：~1.3 tokens/词
    - 中文字符：~1 token/字  
    - 其他字符：~0.25 tokens/字符
    """
    if not text:
        return 0
    # 中文字符
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 英文单词
    en_words = len(re.findall(r'[a-zA-Z]+', text))
    # 其他（数字、标点、空格等）
    other = len(text) - cn_chars - sum(len(w) for w in re.findall(r'[a-zA-Z]+', text))
    
    return int(cn_chars * 1.0 + en_words * 1.3 + other * 0.25)


def _sanitize_text(text):
    """移除无效的 Unicode surrogate pairs 和非法控制字符，避免编码错误。"""
    if not text:
        return text
    # 移除 U+D800-U+DFFF 的 surrogate pairs
    text = text.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
    # 替换控制字符（除了 \t, \n, \r）
    return "".join(ch for ch in text if ch in ("\t", "\n", "\r") or not (0x00 <= ord(ch) <= 0x1F or 0x7F <= ord(ch) <= 0x9F))
