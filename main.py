# -*- coding: utf-8 -*-
"""
main.py — точка входа «Дневника питания и тренировок».
Главное окно: шапка (header) с меню, хлебными крошками и сквозным поиском,
подвал (footer) с данными автора и часами, рабочая область с экранами.
Запуск: python main.py
"""
import math
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import db
from theme import (BG, PANEL, PANEL_2, LINE, ACCENT, ACCENT2, DANGER, TEXT,
                   MUTED, F_HEADER, F_TITLE, F_TEXT, F_SMALL, F_LOGO,
                   APP_TITLE, APP_VERSION, AUTHOR_NAME, AUTHOR_GROUP)
from ui import setup_styles, HoverButton, placeholder, lerp
import screens
import admin
from dialogs import SearchWindow

ICON = Path(__file__).with_name("icon.ico")

SCREENS = {  # имя: (заголовок для крошек, строитель, только для админа?)
    "dashboard": ("Главная", screens.build_dashboard, False),
    "food": ("Дневник питания", screens.build_food, False),
    "workouts": ("Дневник тренировок", screens.build_workouts, False),
    "users": ("Пользователи", admin.build_users, True),
    "log": ("Журнал действий", admin.build_log, True),
    "about": ("О программе", screens.build_about, False),
}


class App(tk.Tk):
    """Скрытый корень: держит сеанс и переключает окна входа/работы."""

    def __init__(self, run=True):
        super().__init__()
        self.withdraw()
        db.init_db()
        self.open_login()
        if run:
            self.mainloop()

    def open_login(self):
        self.login = screens.LoginWindow(self)
        self.login.protocol("WM_DELETE_WINDOW", self.destroy)

    def open_main(self, user):
        self.main = MainWindow(self, user)

    def logout(self):
        db.log(self.main.user["id"], "Выход из системы")
        self.main.destroy()
        self.open_login()


class MainWindow(tk.Toplevel):
    def __init__(self, app: App, user: dict):
        super().__init__(app)
        self.app = app
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.current = None
        self._spin_job = None
        setup_styles(self)

        self.title(f"{APP_TITLE} — {user['full_name']}")
        self.geometry("1200x740")
        self.minsize(1020, 660)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        if ICON.exists():
            try:
                self.iconbitmap(str(ICON))
            except tk.TclError:
                pass
        self.configure(bg=BG)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        db.log(user["id"], "Вход в систему", f"Роль: {user['role']}")

        self._build_header()
        self._build_crumbs_bar()
        self.host = tk.Frame(self, bg=BG)
        self.host.grid(row=2, column=0, sticky="nsew")
        self._build_footer()
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set())

        self.navigate("dashboard")

    # ---------------------------------------------------------------- шапка
    def _build_header(self):
        head = tk.Frame(self, bg=PANEL)
        head.grid(row=0, column=0, sticky="ew")

        # логотип со «спиннером» при переходах
        self.logo = tk.Canvas(head, width=44, height=44, bg=PANEL,
                              highlightthickness=0)
        self.logo.pack(side="left", padx=(14, 8), pady=8)
        self.logo.create_oval(4, 4, 40, 40, fill=PANEL_2, outline=ACCENT, width=3)
        self.logo.create_oval(16, 16, 28, 28, fill=ACCENT)
        self.spinner = self.logo.create_arc(6, 6, 38, 38, start=90, extent=60,
                                            style="arc", outline=ACCENT2, width=3,
                                            state="hidden")
        tk.Label(head, text=APP_TITLE, bg=PANEL, fg=TEXT, font=F_LOGO)\
            .pack(side="left", padx=(0, 18))

        # меню-навигация
        items = [("Главная", "dashboard"), ("Питание", "food"),
                 ("Тренировки", "workouts")]
        if self.is_admin:
            items += [("Пользователи", "users"), ("Журнал", "log")]
        items.append(("О программе", "about"))
        for text, name in items:
            HoverButton(head, text, lambda n=name: self.navigate(n),
                        kind="ghost", width=104, height=30, font=("Segoe UI Semibold", 9),
                        radius=7).pack(side="left", padx=2)

        # сквозной поиск
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(head, textvariable=self.search_var, width=24,
                                     bg=PANEL_2, fg=MUTED, insertbackground=TEXT,
                                     relief="flat", font=F_TEXT)
        placeholder(self.search_entry, "🔍 сквозной поиск… (Ctrl+F)")
        self.search_entry.pack(side="left", padx=(12, 4), ipady=4)
        self.search_entry.bind("<Return>", self._do_search)
        HoverButton(head, "Найти", self._do_search, kind="accent", width=72,
                    height=30, font=("Segoe UI Semibold", 9), radius=7)\
            .pack(side="left")

        # пользователь и выход
        tk.Label(head, text=f"👤 {self.user['username']} · {self.user['role']}",
                 bg=PANEL, fg=ACCENT, font=("Segoe UI Semibold", 10))\
            .pack(side="right", padx=(8, 14))
        HoverButton(head, "Выход", self.app.logout, kind="danger", width=86,
                    height=30, font=("Segoe UI Semibold", 9), radius=7)\
            .pack(side="right")

    def _build_crumbs_bar(self):
        """Отдельная строка под шапкой — «хлебные крошки»."""
        self.crumbs = tk.Frame(self, bg=PANEL)
        self.crumbs.grid(row=1, column=0, sticky="ew")

    def _do_search(self, _e=None):
        q = self.search_entry.get()
        if q and not getattr(self.search_entry, "_ph", None) == q:
            SearchWindow(self, q)

    def _set_crumbs(self, name):
        for w in self.crumbs.winfo_children():
            w.destroy()
        path = [("Главная", "dashboard")]
        if name != "dashboard":
            path.append((SCREENS[name][0], name))
        for i, (title, target) in enumerate(path):
            if i:
                tk.Label(self.crumbs, text="  /  ", bg=PANEL, fg=MUTED,
                         font=F_SMALL).pack(side="left")
            last = i == len(path) - 1
            lbl = tk.Label(self.crumbs, text=title, bg=PANEL,
                           fg=TEXT if last else ACCENT,
                           font=("Segoe UI Semibold", 11) if last else F_TEXT,
                           cursor="hand2")
            lbl.pack(side="left")
            if not last:
                lbl.bind("<Button-1>", lambda e, n=target: self.navigate(n))
                lbl.bind("<Enter>", lambda e, l=lbl: l.configure(fg=ACCENT2))
                lbl.bind("<Leave>", lambda e, l=lbl: l.configure(fg=ACCENT))

    # ---------------------------------------------------------------- экраны
    def navigate(self, name, **kw):
        if name not in SCREENS:
            return
        title, builder, admin_only = SCREENS[name]
        if admin_only and not self.is_admin:
            self.toast("Раздел доступен только администратору", ok=False)
            return
        kw = {k: v for k, v in kw.items() if v is not None}
        self._set_crumbs(name)
        self._spin()
        old, self.current = self.current, None
        screen = builder(self, **kw) if kw else builder(self)
        self.current = screen
        screen.place(in_=self.host, relwidth=1, relheight=1, x=70)
        screen.slide_in()
        if old is not None:
            self.host.after(260, lambda: old.destroy()
                            if old.winfo_exists() else None)

    def _spin(self):
        """Анимация «спиннера» на логотипе при каждом переходе."""
        if self._spin_job:
            try:
                self.after_cancel(self._spin_job)
            except Exception:
                pass
        self.logo.itemconfigure(self.spinner, state="normal")

        def step(i=0):
            if i > 16:
                self.logo.itemconfigure(self.spinner, state="hidden")
                self._spin_job = None
                return
            self.logo.itemconfigure(self.spinner, start=90 + i * 22)
            self._spin_job = self.after(30, lambda: step(i + 1))
        step()

    # ---------------------------------------------------------------- подвал
    def _build_footer(self):
        foot = tk.Frame(self, bg=PANEL_2)
        foot.grid(row=3, column=0, sticky="ew")
        tk.Label(foot, text=f"{AUTHOR_NAME} · группа {AUTHOR_GROUP}",
                 bg=PANEL_2, fg=TEXT, font=F_SMALL).pack(side="left", padx=14, pady=6)
        tk.Label(foot, text=f"{APP_TITLE} v{APP_VERSION} · SQLite · Python",
                 bg=PANEL_2, fg=MUTED, font=F_SMALL).pack(side="right", padx=14)
        self.clock = tk.Label(foot, text="", bg=PANEL_2, fg=MUTED, font=F_SMALL)
        self.clock.pack(side="right", padx=14)
        self.toast_lbl = tk.Label(foot, text="", bg=PANEL_2, fg=MUTED, font=F_SMALL)
        self.toast_lbl.pack(side="right", padx=14)
        self._tick_clock()

    def _tick_clock(self):
        import datetime
        self.clock.configure(text=datetime.datetime.now().strftime("%H:%M:%S  ·  %d.%m.%Y"))
        self.after(1000, self._tick_clock)

    # ---------------------------------------------------------------- сервис
    def toast(self, msg, ok=True):
        """Всплывающее уведомление в подвале с плавным затуханием цвета."""
        target = ACCENT if ok else DANGER
        self.toast_lbl.configure(text=("✔ " if ok else "✘ ") + msg, fg=target)

        def fade(i=0):
            t = i / 14
            self.toast_lbl.configure(fg=lerp(target, MUTED, t))
            if i < 14:
                self.after(160, lambda: fade(i + 1))
        self.after(1400, fade)

    def confirm(self, msg):
        from tkinter import messagebox
        return messagebox.askyesno(APP_TITLE, msg, parent=self)


def main():
    App()


if __name__ == "__main__":
    main()
