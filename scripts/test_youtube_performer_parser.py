#!/usr/bin/env python3
"""Regression tests for the strict YouTube-description performer parser."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "collect_youtube_performers",
    Path(__file__).with_name("collect_youtube_performers.py"),
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

cases = [
    (
        "five-person verified description",
        "前文\n【出演者】\n永田 → link\n原宿 → link\nダ･ヴィンチ･恐山 → link\nARuFa → link\n加藤 → link\n【スタッフ】\n編集",
        ["永田", "原宿", "ダ･ヴィンチ･恐山", "ARuFa", "加藤"],
    ),
    (
        "seven-person verified description",
        "【出演者】\n永田 → link\n原宿 → link\nダ･ヴィンチ･恐山 → link\nARuFa → link\n加藤 → link\nヤスミノ → link\nかんち → link\n【関連リンク】\nURL",
        ["永田", "原宿", "ダ･ヴィンチ･恐山", "ARuFa", "加藤", "ヤスミノ", "かんち"],
    ),
    (
        "missing heading must not guess",
        "出演者は永田とARuFaです",
        None,
    ),
    (
        "empty heading must not guess",
        "【出演者】\n【スタッフ】\n編集",
        None,
    ),
]
for label, description, expected in cases:
    actual = module.extract_performers(description)
    if actual != expected:
        raise SystemExit(f"FAIL: {label}: expected={expected!r}, actual={actual!r}")
    print(f"PASS: {label}")
print("TEST_RESULT: PASS")
