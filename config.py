# -*- coding: utf-8 -*-
"""경로와 설정(퇴근 기준 시각) 관리."""
import json
import os
import sys

APP_NAME = "gohome"
FROZEN = getattr(sys, "frozen", False)  # PyInstaller exe로 실행 중인지

# 로그, 실패 기록, 설정은 실행 파일이 있는 폴더에 저장
BASE_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
FAIL_FLAG = os.path.join(BASE_DIR, "fail_flag.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULTS = {"leave_hour": 18, "leave_minute": 0}


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def leave_time_text(cfg):
    return "%02d:%02d" % (cfg["leave_hour"], cfg["leave_minute"])
