# -*- coding: utf-8 -*-
"""G2Works 직접 통신 (브라우저 없이 로그인 → 출퇴근 상태 조회 → 퇴근 요청).

종료 중에는 새 프로그램(브라우저 등)을 실행할 수 없어서 HTTP 요청으로 처리한다.
"""
import base64
import hashlib
import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

BASE_URL = "https://cospecab.g2works.kr"
LEAVE_KIND = "900788"  # 퇴근하기 attend('900788')
TIMEOUT = 10
EMPTY_DATE = "0000-00-00 00:00:00"

MSG_NO_ATTEND = "출근기록이 없어 퇴근 처리가 되지 않았습니다."


class G2Error(Exception):
    pass


def cryptojs_encrypt(text, passphrase):
    """CryptoJS.AES.encrypt(text, passphrase).toString()과 같은 결과."""
    salt = os.urandom(8)
    data, prev = b"", b""
    while len(data) < 48:  # OpenSSL EVP_BytesToKey(MD5) → 키 32 + IV 16
        prev = hashlib.md5(prev + passphrase.encode("utf-8") + salt).digest()
        data += prev
    key, iv = data[:32], data[32:48]
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(text.encode("utf-8"), 16))
    return base64.b64encode(b"Salted__" + salt + ct).decode("ascii")


class G2Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) gohome")]

    def _get(self, url):
        with self.opener.open(urllib.parse.urljoin(BASE_URL + "/", url), timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")

    def _post(self, path, data=None):
        body = urllib.parse.urlencode(data or {}).encode("utf-8")
        req = urllib.request.Request(BASE_URL + path, data=body, headers={
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": BASE_URL + "/",
        })
        with self.opener.open(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    def login(self, emp_no, password):
        page = self._get("/")
        m = re.search(r'var enc_key = "([^"]+)"', page)
        if not m:
            raise G2Error("로그인 화면이 바뀌어 암호화 키를 찾지 못했습니다.")
        key = m.group(1)
        msg = {}
        for _ in range(2):  # 서버가 키를 바꾸라고 하면 한 번 더 시도
            res = self._post("/g2works/login/ajaxLogin.do", {
                "emp_no": cryptojs_encrypt(emp_no, key),
                "passwd": cryptojs_encrypt(password, key),
                "keepid": "false",
                "login_type": "emp_no",
            })
            msg = res.get("jsonMessage", {})
            if msg.get("result") == "fail" and msg.get("message") == "aes_auth_login":
                key = msg.get("aes_key")
                continue
            break
        if msg.get("result") == "fail":
            raise G2Error("로그인 실패: %s" % msg.get("message"))
        if msg.get("ipChk") == "fail":
            raise G2Error("로그인 실패: 접속 IP 제한")
        if msg.get("passChange") == "fail":
            raise G2Error("로그인 실패: 비밀번호 변경이 필요합니다.")
        urls = msg.get("urls") or {}
        nxt = urls.get("directUrl") or urls.get("default")
        if nxt:  # 브라우저처럼 메인 화면을 한 번 열어 둠
            self._get(nxt)

    def attend_info(self):
        info = self._post("/g2works/main/attendInfo.json").get("dataAttendMap", {})
        if info.get("result") != "success":
            raise G2Error("출퇴근 상태 조회 실패")
        return info

    def send_leave(self, is_attend_new):
        cmd = "attendPostNew" if is_attend_new else "attendPost1"
        return self._post("/emp.auth.do?command=" + cmd, {"kind": LEAVE_KIND}).get("jsonMessage", {})


def has_attend(today):
    """사이트의 attend() 검사와 같은 기준으로 오늘 출근 기록이 있는지 판단."""
    sdate = today.get("sdate") or ""
    return bool(today.get("type")) and sdate not in ("", EMPTY_DATE) and sdate != today.get("todate")


def leave(emp_no, password):
    """퇴근 처리. 성공하면 퇴근 시각 문자열을 돌려주고, 실패하면 G2Error."""
    c = G2Client()
    c.login(emp_no, password)
    info = c.attend_info()
    if not has_attend(info.get("attendInfo") or {}):
        raise G2Error(MSG_NO_ATTEND)

    res = c.send_leave(bool(info.get("isAttendNew")))
    if res.get("result") == "fail":
        raise G2Error("퇴근 요청 실패: %s" % res.get("message"))

    edate = (c.attend_info().get("attendInfo") or {}).get("edate") or EMPTY_DATE
    if edate == EMPTY_DATE:
        raise G2Error("퇴근 요청 후에도 퇴근 기록이 없습니다: %s" % res.get("message"))
    return edate


def check_login(emp_no, password):
    """설정 창에서 사번/비밀번호 확인용. 실패하면 G2Error."""
    G2Client().login(emp_no, password)
