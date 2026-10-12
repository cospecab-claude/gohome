# -*- coding: utf-8 -*-
"""Windows 종료 신호(WM_QUERYENDSESSION) 감지.

보이지 않는 창을 만들어 종료 신호를 기다리고, 신호가 오면 종료를 잠깐 막은 채
콜백을 실행한 뒤 종료를 계속 진행시킨다.
종료 중에는 새 프로그램을 실행할 수 없으므로 콜백은 프로세스 안에서만 처리해야 한다.
"""
import ctypes
import logging
import threading
from ctypes import wintypes

log = logging.getLogger("gohome")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
ENDSESSION_LOGOFF = 0x80000000
SHUTDOWN_NORETRY = 0x00000001
CALLBACK_TIMEOUT_SEC = 40


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.ShutdownBlockReasonCreate.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.ShutdownBlockReasonDestroy.argtypes = [wintypes.HWND]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]


class ShutdownHook(threading.Thread):
    """종료/재시작 시 on_shutdown()을 실행 (로그아웃은 제외)."""

    def __init__(self, on_shutdown, block_text="퇴근 처리 중..."):
        super().__init__(daemon=True)
        self.on_shutdown = on_shutdown
        self.block_text = block_text
        self._wndproc = WNDPROC(self._proc)  # 가비지 컬렉션 방지용으로 보관

    def _run_callback(self):
        t = threading.Thread(target=self._safe_callback, daemon=True)
        t.start()
        t.join(CALLBACK_TIMEOUT_SEC)
        if t.is_alive():
            log.error("종료 처리 시간 초과 (%d초)", CALLBACK_TIMEOUT_SEC)

    def _safe_callback(self):
        try:
            self.on_shutdown()
        except Exception:
            log.exception("종료 처리 중 오류")

    def _proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_QUERYENDSESSION:
            if lparam & ENDSESSION_LOGOFF:
                log.info("로그아웃 → 통과")
                return 1
            log.info("종료 신호 수신")
            user32.ShutdownBlockReasonCreate(hwnd, self.block_text)
            self._run_callback()
            user32.ShutdownBlockReasonDestroy(hwnd)
            return 1
        if msg == WM_ENDSESSION:
            log.info("종료 진행 (wParam=%s)", wparam)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def run(self):
        # 다른 프로그램보다 먼저 종료 신호를 받도록 우선순위를 높임
        kernel32.SetProcessShutdownParameters(0x3FF, SHUTDOWN_NORETRY)
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinst
        wc.lpszClassName = "GohomeShutdownHook"
        user32.RegisterClassW(ctypes.byref(wc))
        # 메시지 전용 창은 종료 신호를 못 받으므로 숨겨진 일반 창을 사용
        hwnd = user32.CreateWindowExW(0, wc.lpszClassName, "gohome", 0, 0, 0, 0, 0,
                                      None, None, hinst, None)
        if not hwnd:
            log.error("종료 감지 창 생성 실패: %d", ctypes.get_last_error())
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
