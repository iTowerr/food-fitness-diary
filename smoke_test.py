# -*- coding: utf-8 -*-
"""
smoke_test.py — автоматическая проверка приложения без ручного кликанья:
  1) БД: схема, тестовые данные, внешние ключи;
  2) аутентификация обеих ролей;
  3) открытие всех 6 экранов по очереди (переходы);
  4) открытие/закрытие модального диалога;
  5) скриншоты окна входа и экранов.
"""
import sys
import tkinter as tk

import db

db.init_db()
print("1) БД: записи в таблицах:", db.counts())
assert db.counts()["meals"] >= 15 and db.counts()["workouts"] >= 10, "мало данных"
assert not db.fk_check(), "нарушения внешних ключей"
print("   Внешние ключи: OK")

u, a = db.authenticate("zahar", "user123"), db.authenticate("admin", "admin123")
assert u and a and u["role"] == "user" and a["role"] == "admin"
print("2) Вход по логину/паролю (user и admin): OK")

from main import App
from dialogs import UserDialog, SearchWindow

app = App(run=False)

def grab(widget, name):
    try:
        from PIL import ImageGrab
        import ctypes
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            dpi = 96
        k = dpi / 96.0
        widget.update_idletasks()
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        w, h = widget.winfo_width(), widget.winfo_height()
        ImageGrab.grab(bbox=(round(x * k), round(y * k),
                             round((x + w) * k), round((y + h) * k))).save(name)
        print("   скриншот:", name)
    except Exception as e:
        print("   (скриншот недоступен:", e, ")")

def drive():
    grab(app.login, "shot_login.png")
    app.login.destroy()
    app.open_main(a)
    win = app.main
    seq = ["dashboard", "food", "workouts", "users", "log", "about",
           "dashboard", "food"]

    def nav(i=0):
        if i >= len(seq):
            d = UserDialog(win, lambda p: None)
            win.after(350, d.destroy)
            win.after(700, s)
            return
        win.navigate(seq[i])
        delay = 300
        if seq[i] == "food" and i == 1:
            win.after(450, lambda: grab(win, "shot_food.png"))
            delay = 900
        if seq[i] == "dashboard" and i > 0:
            win.after(950, lambda: grab(win, "shot_dashboard.png"))
            delay = 1500
        if seq[i] == "about":
            win.after(500, lambda: grab(win, "shot_about.png"))
            delay = 950
        win.after(delay, lambda: nav(i + 1))

    def s():
        sw = SearchWindow(win, "курин")
        win.after(350, sw.destroy)
        win.after(600, finish)

    def finish():
        print("3) Переходы по всем экранам, диалоги и сквозной поиск: OK")
        print("SMOKE OK")
        app.destroy()

    win.after(600, lambda: nav())

app.after(900, drive)
app.mainloop()
print("Готово.")
