# -*- coding: utf-8 -*-
"""
admin.py — экраны администратора: управление пользователями
и просмотр журнала действий.
"""
import sqlite3
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from theme import (BG, PANEL, LINE, ACCENT, ACCENT2, TEXT, MUTED, F_HEADER,
                   F_TITLE, F_TEXT, F_SMALL, fmt_date)
from ui import (ScreenCanvas, DataTable, HoverButton, card, label, dark_entry,
                placeholder, entry_value)
import db
from dialogs import UserDialog

PERIODS = [("Все время", 0), ("Сегодня", 1), ("7 дней", 7), ("30 дней", 30)]


def _filter_bar(sc, on_change, search_ph):
    """Строка фильтров: период + поиск. Возвращает (frame, period_cb, entry)."""
    fl = tk.Frame(sc, bg=PANEL)
    inner = tk.Frame(fl, bg=PANEL)
    inner.pack(fill="x", padx=12, pady=9)
    label(inner, "Период:", fg=MUTED).pack(side="left")
    period_cb = ttk.Combobox(inner, values=[p[0] for p in PERIODS],
                             state="readonly", style="Diary.TCombobox", width=11)
    period_cb.current(0)
    period_cb.pack(side="left", padx=(6, 12))
    q = dark_entry(inner, width=20)
    placeholder(q, search_ph)
    q.pack(side="left", padx=6)
    label(inner, "Сортировка — клик по заголовку столбца", fg=MUTED,
          font=F_SMALL).pack(side="right")
    period_cb.bind("<<ComboboxSelected>>", lambda e: on_change())
    q.bind("<KeyRelease>", lambda e: on_change())
    return fl, period_cb, q


# ==================================================================== пользователи
def build_users(app, search=None):
    sc = ScreenCanvas(app.host)
    me = app.user["id"]

    top = tk.Frame(sc, bg=BG)
    label(top, "Пользователи", bg=BG, fg=TEXT, font=F_HEADER).pack(side="left")
    cnt = label(top, "", bg=BG, fg=ACCENT, font=F_TITLE)
    cnt.pack(side="right")
    sc.add(top)

    def refresh():
        pass  # определена ниже; заглушка для замыкания

    fl, period_cb, q = _filter_bar(sc, lambda: refresh(),
                                   "🔍 поиск по логину/ФИО…")
    role_cb = ttk.Combobox(fl.winfo_children()[0], values=["Все роли", "user", "admin"],
                           state="readonly", style="Diary.TCombobox", width=10)
    role_cb.current(0)
    role_cb.pack(side="left", padx=(12, 0))
    role_cb.bind("<<ComboboxSelected>>", lambda e: refresh())
    sc.add(fl, gap=10)

    f_tbl, inner_tbl = card(sc, color=LINE)
    table = DataTable(inner_tbl,
                      [("id", "ID", 46, "e"), ("username", "Логин", 130, "w"),
                       ("full_name", "ФИО", 260, "w"), ("role", "Роль", 90, "w"),
                       ("weight_kg", "Вес", 70, "e"), ("created_at", "Создан", 150, "w")],
                      height=12, on_change=sc.relayout)
    table.pack(fill="x")
    sc.add(f_tbl, gap=10)

    def load():
        rows = db.all_users()
        sub = entry_value(q).lower()
        role = role_cb.get()
        out = [r for r in rows
               if (role == "Все роли" or r["role"] == role)
               and (not sub or sub in r["username"].lower()
                    or sub in r["full_name"].lower())]
        table.set_rows(out)
        cnt.configure(text=f"Пользователей: {len(out)}")
        sc.relayout()

    refresh = load

    btns = tk.Frame(sc, bg=BG)

    def sel():
        r = table.selected_row()
        if not r:
            app.toast("Выберите пользователя в таблице", ok=False)
        return r

    def add():
        UserDialog(app.main, lambda p: _save_new(p))

    def _save_new(p):
        if db.username_exists(p["username"]):
            app.toast("Такой логин уже существует", ok=False)
            return
        uid = db.add_user(p["username"], p["password"], p["full_name"],
                          p["role"], p["weight_kg"])
        db.log(me, "Добавлен пользователь", f"{p['username']} ({p['role']})")
        app.toast(f"Пользователь {p['username']} добавлен")
        load()

    def edit():
        r = sel()
        if not r:
            return
        UserDialog(app.main, lambda p: _save_edit(r, p), record=r)

    def _save_edit(r, p):
        if db.username_exists(p["username"], except_id=r["id"]):
            app.toast("Такой логин уже занят", ok=False)
            return
        db.update_user(r["id"], p["username"], p["full_name"], p["role"],
                       p["weight_kg"], p["password"])
        db.log(me, "Изменён пользователь", p["username"])
        app.toast("Пользователь сохранён")
        load()

    def delete():
        r = sel()
        if not r:
            return
        if r["id"] == me:
            app.toast("Нельзя удалить свою учётную запись", ok=False)
            return
        admins = [u for u in db.all_users() if u["role"] == "admin"]
        if r["role"] == "admin" and len(admins) <= 1:
            app.toast("Нельзя удалить последнего администратора", ok=False)
            return
        if not app.confirm(f"Удалить пользователя {r['username']}?\n"
                           "Его записи питания и тренировок будут удалены тоже."):
            return
        db.delete_user(r["id"])
        db.log(me, "Удалён пользователь", r["username"])
        app.toast("Пользователь удалён")
        load()

    HoverButton(btns, "＋ Добавить", add, width=130).pack(side="left")
    HoverButton(btns, "✎ Изменить", edit, kind="ghost", width=120).pack(side="left", padx=10)
    HoverButton(btns, "🗑 Удалить", delete, kind="danger", width=120).pack(side="left")
    sc.add(btns)

    if search:
        q.delete(0, "end")
        q.insert(0, search)
        q.configure(fg=TEXT)
    load()
    return sc


# ==================================================================== журнал
def build_log(app):
    sc = ScreenCanvas(app.host)

    top = tk.Frame(sc, bg=BG)
    label(top, "Журнал действий", bg=BG, fg=TEXT, font=F_HEADER).pack(side="left")
    cnt = label(top, "", bg=BG, fg=ACCENT, font=F_TITLE)
    cnt.pack(side="right")
    sc.add(top)

    fl = tk.Frame(sc, bg=PANEL)
    inner = tk.Frame(fl, bg=PANEL)
    inner.pack(fill="x", padx=12, pady=9)
    label(inner, "Пользователь:", fg=MUTED).pack(side="left")
    user_cb = ttk.Combobox(inner, values=["Все"] + [u["username"] for u in db.all_users()],
                           state="readonly", style="Diary.TCombobox", width=10)
    user_cb.current(0)
    user_cb.pack(side="left", padx=(6, 12))
    label(inner, "Период:", fg=MUTED).pack(side="left")
    period_cb = ttk.Combobox(inner, values=[p[0] for p in PERIODS],
                             state="readonly", style="Diary.TCombobox", width=11)
    period_cb.current(0)
    period_cb.pack(side="left", padx=6)
    q = dark_entry(inner, width=20)
    placeholder(q, "🔍 поиск по действию/детали…")
    q.pack(side="left", padx=6)
    HoverButton(inner, "Обновить ↻", lambda: load(), kind="ghost", width=110,
                height=28, radius=6).pack(side="right")
    for w in (user_cb, period_cb):
        w.bind("<<ComboboxSelected>>", lambda e: load())
    q.bind("<KeyRelease>", lambda e: load())
    sc.add(fl, gap=10)

    f_tbl, inner_tbl = card(sc, color=LINE)
    table = DataTable(inner_tbl,
                      [("created_at", "Время", 160, "w"), ("user", "Пользователь", 120, "w"),
                       ("action", "Действие", 210, "w"), ("details", "Детали", 380, "w")],
                      height=13, on_change=sc.relayout)
    table.pack(fill="x")
    sc.add(f_tbl, gap=10)

    def load():
        rows = db.log_all()
        uname = user_cb.get()
        days = dict(PERIODS)[period_cb.get()]
        cutoff = (date.today() - timedelta(days=days)).isoformat() if days else None
        sub = entry_value(q).lower()
        out = []
        for r in rows:
            if uname != "Все" and r["user"].lower() != uname.lower():
                continue
            if cutoff and r["created_at"][:10] < cutoff:
                continue
            if sub and sub not in r["action"].lower() and sub not in r["details"].lower():
                continue
            out.append(r)
        table.set_rows(out)
        cnt.configure(text=f"Событий: {len(out)}")
        sc.relayout()

    load()
    return sc
