# -*- coding: utf-8 -*-
"""gohome: PC를 끌 때 G2Works 퇴근을 자동으로 찍는 상주 프로그램.

실행 방법:
    gohome.exe              실행한 자리에서 트레이에 상주 (처음이면 설정 창, 시작 프로그램 등록)
    gohome.exe --settings   설정 창만 띄움 (트레이 메뉴에서 사용)
    python app.py           소스로 실행 (설치/시작 프로그램 등록 없이 동작 확인용)
"""
import ctypes
import datetime
import logging
import os
import subprocess
import sys
import threading

import config
import credential
import g2works
import icon as app_icon
import installer
import settings_ui
from shutdown_hook import ShutdownHook

log = logging.getLogger("gohome")

TITLE = "gohome"
MUTEX_NAME = "Local\\gohome_single_instance"
ERROR_ALREADY_EXISTS = 183

MB_OK = 0x0
MB_YESNO = 0x4
MB_ICONERROR = 0x10
MB_ICONQUESTION = 0x20
MB_ICONWARNING = 0x30
MB_ICONINFORMATION = 0x40
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000
IDYES = 6

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_leave_lock = threading.Lock()


def msgbox(text, flags=MB_OK | MB_ICONINFORMATION):
    return ctypes.windll.user32.MessageBoxW(None, text, TITLE, flags | MB_TOPMOST | MB_SETFOREGROUND)


def ask(text):
    return msgbox(text, MB_YESNO | MB_ICONQUESTION) == IDYES


def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(config.LOG_DIR, datetime.datetime.now().strftime("gohome_%Y-%m.log"))
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(handler)
    if sys.stdout is not None:  # exe(콘솔 없음)로 실행하면 None
        log.addHandler(logging.StreamHandler(sys.stdout))
    log.setLevel(logging.INFO)


# ---------- 실패 기록 ----------

def write_fail(reason):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(config.FAIL_FLAG, "w", encoding="utf-8") as f:
        f.write("%s\n%s\n" % (now, reason))


def show_pending_fail():
    """지난번 퇴근 처리 실패 기록이 있으면 알림 후 삭제."""
    if not os.path.exists(config.FAIL_FLAG):
        return
    with open(config.FAIL_FLAG, encoding="utf-8") as f:
        lines = f.read().splitlines()
    when = lines[0] if lines else "알 수 없음"
    reason = lines[1] if len(lines) > 1 else "알 수 없음"
    os.remove(config.FAIL_FLAG)
    if reason == g2works.MSG_NO_ATTEND:
        text = "%s\n\n시각: %s" % (reason, when)
    else:
        text = ("지난번 퇴근 자동 처리에 실패했습니다.\n\n시각: %s\n사유: %s\n\n"
                "G2Works에서 퇴근 기록을 확인해 주세요.") % (when, reason)
    msgbox(text, MB_OK | MB_ICONWARNING)


# ---------- 퇴근 처리 ----------

def do_leave():
    """퇴근 처리. (성공 여부, 메시지)."""
    with _leave_lock:
        cred = credential.load()
        if cred is None:
            return False, "저장된 사번/비밀번호가 없습니다. 트레이 메뉴 > 설정 변경에서 입력해 주세요."
        try:
            edate = g2works.leave(*cred)
        except g2works.G2Error as e:
            return False, str(e)
        except Exception as e:  # 네트워크 오류 등
            return False, "오류: %s" % e
        return True, "퇴근 처리되었습니다. (퇴근 시각: %s)" % edate


def on_shutdown():
    cfg = config.load()
    now = datetime.datetime.now()
    if (now.hour, now.minute) < (cfg["leave_hour"], cfg["leave_minute"]):
        log.info("퇴근 기준 시각(%s) 이전이라 건너뜀", config.leave_time_text(cfg))
        return
    ok, message = do_leave()
    if ok:
        log.info(message)
    else:
        log.error("퇴근 처리 실패: %s", message)
        write_fail(message)


# ---------- 트레이 메뉴 ----------

def open_settings_process():
    """설정 창은 별도 프로세스로 띄움 (트레이와 tkinter를 한 프로세스에서 섞지 않기 위해)."""
    if config.FROZEN:
        args = [sys.executable, "--settings"]
    else:
        args = [sys.executable, os.path.abspath(__file__), "--settings"]
    subprocess.Popen(args, cwd=config.BASE_DIR, close_fds=True)


def run_tray():
    import pystray

    def title(item):
        return "퇴근 기준 시각 %s" % config.leave_time_text(config.load())

    def on_settings(icon, item):
        open_settings_process()

    def on_leave_now(icon, item):
        def work():
            if not ask("지금 퇴근을 찍을까요?"):
                return
            ok, message = do_leave()
            (log.info if ok else log.error)("수동 퇴근: %s", message)
            msgbox(message, MB_OK | (MB_ICONINFORMATION if ok else MB_ICONERROR))
        threading.Thread(target=work, daemon=True).start()

    def on_open_logs(icon, item):
        os.makedirs(config.LOG_DIR, exist_ok=True)
        os.startfile(config.LOG_DIR)

    def on_quit(icon, item):
        if ask("프로그램을 끄면 다음 로그인 전까지 자동 퇴근이 동작하지 않습니다.\n끌까요?"):
            log.info("사용자가 프로그램을 끔")
            icon.stop()

    def on_uninstall(icon, item):
        if not ask("gohome을 제거할까요?\n\n시작 프로그램 등록과 저장된 사번/비밀번호가 삭제되고, "
                   "더 이상 자동 퇴근이 동작하지 않습니다."):
            return
        log.info("제거")
        installer.uninstall()
        msgbox("제거했습니다.\n필요 없으면 gohome.exe가 있는 폴더를 직접 삭제해 주세요.\n\n%s"
               % config.BASE_DIR)
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(title, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("설정 변경", on_settings),
        pystray.MenuItem("지금 퇴근 찍기", on_leave_now),
        pystray.MenuItem("로그 폴더 열기", on_open_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("프로그램 끄기", on_quit),
        pystray.MenuItem("제거", on_uninstall),
    )
    pystray.Icon(TITLE, app_icon.make(), "gohome - 퇴근 자동 처리", menu).run()


# ---------- 진입점 ----------

def main():
    if "--settings" in sys.argv:
        settings_ui.run()
        return

    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        msgbox("gohome이 이미 실행 중입니다.\n작업 표시줄 오른쪽 아래 트레이 아이콘을 확인해 주세요.")
        return

    setup_logging()
    log.info("===== 시작 (%s) =====", sys.executable)
    show_pending_fail()

    if credential.load() is None:
        if not settings_ui.run(first_time=True):
            msgbox("사번/비밀번호가 없어 자동 퇴근이 동작하지 않습니다.\n"
                   "트레이 메뉴 > 설정 변경에서 입력해 주세요.", MB_OK | MB_ICONWARNING)

    installer.register_startup()
    ShutdownHook(on_shutdown).start()
    log.info("상주 시작 (퇴근 기준 시각 %s)", config.leave_time_text(config.load()))
    run_tray()
    log.info("===== 종료 =====")


if __name__ == "__main__":
    main()
