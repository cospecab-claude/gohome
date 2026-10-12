# -*- coding: utf-8 -*-
"""시작 프로그램 등록/해제, 제거. exe는 복사하지 않고 실행한 자리에서 그대로 사용."""
import sys
import winreg

import config
import credential

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = config.APP_NAME


def register_startup():
    """현재 exe 경로로 시작 프로그램 등록 (exe를 옮겨도 다시 실행하면 갱신됨)."""
    if not config.FROZEN:
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, '"%s"' % sys.executable)


def unregister_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, RUN_VALUE)
    except FileNotFoundError:
        pass


def uninstall():
    """시작 프로그램 해제 + 자격 증명 삭제. exe 파일은 사용자가 직접 삭제."""
    unregister_startup()
    credential.delete()
