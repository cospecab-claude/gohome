# -*- coding: utf-8 -*-
"""설정 창: 사번, 비밀번호, 퇴근 기준 시각."""
import tkinter as tk
from tkinter import messagebox

import config
import credential
import g2works

TITLE = "gohome 설정"


def run(first_time=False):
    """설정 창을 띄우고, 저장했으면 True."""
    cfg = config.load()
    saved_cred = credential.load()
    result = {"saved": False}

    root = tk.Tk()
    root.title(TITLE)
    root.resizable(False, False)
    root.attributes("-topmost", True)

    frm = tk.Frame(root, padx=16, pady=14)
    frm.pack()

    intro = ("처음 실행입니다. G2Works 사번과 비밀번호를 입력해 주세요."
             if first_time else "변경할 항목을 입력해 주세요.")
    tk.Label(frm, text=intro).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

    tk.Label(frm, text="사번").grid(row=1, column=0, sticky="w")
    emp_var = tk.StringVar(value=saved_cred[0] if saved_cred else "")
    tk.Entry(frm, textvariable=emp_var, width=24).grid(row=1, column=1, columnspan=3, sticky="w", pady=2)

    tk.Label(frm, text="비밀번호").grid(row=2, column=0, sticky="w")
    pw_var = tk.StringVar()
    tk.Entry(frm, textvariable=pw_var, show="*", width=24).grid(row=2, column=1, columnspan=3, sticky="w", pady=2)
    if saved_cred:
        tk.Label(frm, text="(비워 두면 기존 비밀번호 유지)", fg="gray").grid(
            row=3, column=1, columnspan=3, sticky="w")

    tk.Label(frm, text="퇴근 기준 시각").grid(row=4, column=0, sticky="w", pady=(8, 0))
    hour_var = tk.StringVar(value="%02d" % cfg["leave_hour"])
    min_var = tk.StringVar(value="%02d" % cfg["leave_minute"])
    tk.Spinbox(frm, from_=0, to=23, width=4, textvariable=hour_var, format="%02.0f").grid(
        row=4, column=1, sticky="w", pady=(8, 0))
    tk.Label(frm, text=":").grid(row=4, column=2, pady=(8, 0))
    tk.Spinbox(frm, from_=0, to=59, width=4, textvariable=min_var, format="%02.0f").grid(
        row=4, column=3, sticky="w", pady=(8, 0))
    tk.Label(frm, text="이 시각 이후에 PC를 끄면 자동으로 퇴근을 찍습니다.", fg="gray").grid(
        row=5, column=0, columnspan=4, sticky="w")

    def on_save():
        emp = emp_var.get().strip()
        pw = pw_var.get() or (saved_cred[1] if saved_cred and emp == saved_cred[0] else "")
        if not emp or not pw:
            messagebox.showwarning(TITLE, "사번과 비밀번호를 입력해 주세요.", parent=root)
            return
        try:
            hour, minute = int(hour_var.get()), int(min_var.get())
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            messagebox.showwarning(TITLE, "퇴근 기준 시각이 올바르지 않습니다.", parent=root)
            return

        root.config(cursor="watch")
        root.update()
        try:
            g2works.check_login(emp, pw)
        except Exception as e:
            root.config(cursor="")
            messagebox.showerror(TITLE, "로그인 확인에 실패했습니다.\n\n%s" % e, parent=root)
            return
        root.config(cursor="")

        credential.save(emp, pw)
        cfg.update(leave_hour=hour, leave_minute=minute)
        config.save(cfg)
        result["saved"] = True
        messagebox.showinfo(TITLE, "저장했습니다.\n퇴근 기준 시각: %02d:%02d" % (hour, minute), parent=root)
        root.destroy()

    btns = tk.Frame(frm)
    btns.grid(row=6, column=0, columnspan=4, sticky="e", pady=(12, 0))
    tk.Button(btns, text="로그인 확인 후 저장", command=on_save, width=18).pack(side="left", padx=4)
    tk.Button(btns, text="취소", command=root.destroy, width=8).pack(side="left")

    root.mainloop()
    return result["saved"]
