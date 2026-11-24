# -*- coding: utf-8 -*-
"""
screens.py — экраны пользователя: вход, дашборд с расчётами,
дневник питания, дневник тренировок, раздел «О программе».
"""
import tkinter as tk
from datetime import date, timedelta

from theme import (BG, PANEL, PANEL_2, LINE, ACCENT, ACCENT2, DANGER, TEXT,
                   MUTED, F_HEADER, F_TITLE, F_TEXT, F_SMALL, F_MONO,
                   APP_TITLE, APP_VERSION, AUTHOR_NAME, AUTHOR_GROUP, fmt_date,
                   long_date)
from ui import (ScreenCanvas, DataTable, ProgressArc, HoverButton, card, label,
                dark_entry, dark_spin, placeholder, entry_value, lerp)
import db
from dialogs import MealDialog, WorkoutDialog

PERIODS = [("Все время", 0), ("Сегодня", 1), ("7 дней", 7), ("30 дней", 30)]


# ==================================================================== вход
class LoginWindow(tk.Toplevel):
    """Окно входа: живой фон, прыгающий логотип, вход по логину/паролю."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        from ui import Particles
        self.title("Вход — " + APP_TITLE)
        w, h = 900, 560
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.resizable(False, False)
        self.configure(bg=BG)

        cv = tk.Canvas(self, bg=BG, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        Particles(cv, n_small=26, n_big=5)
        self._draw_logo(cv)

        # панель формы
        form = tk.Frame(cv, bg=PANEL, padx=30, pady=26)
        tk.Label(form, text=APP_TITLE, bg=PANEL, fg=TEXT, font=F_HEADER).pack(pady=(0, 2))
        tk.Label(form, text="войдите, чтобы продолжить", bg=PANEL, fg=MUTED,
                 font=F_SMALL).pack(pady=(0, 16))
        self.u = dark_entry(form, width=24)
        self.u.pack(fill="x", ipady=5)
        self.p = dark_entry(form, width=24, show="•")
        self.p.pack(fill="x", ipady=5, pady=(10, 0))
        self.err = tk.Label(form, text="", bg=PANEL, fg=DANGER, font=F_SMALL)
        self.err.pack(fill="x", pady=(6, 0))
        HoverButton(form, "Войти →", self.login, width=340, height=40)\
            .pack(pady=(12, 10), fill="x")
        tk.Label(form, text="Демо-доступ:  admin / admin123   ·   zahar / user123",
                 bg=PANEL, fg=MUTED, font=F_MONO).pack()
        self.form_win = cv.create_window(w // 2, h // 2 + 30, window=form)
        cv.bind("<Configure>", lambda e: cv.coords(
            self.form_win, e.width // 2, e.height // 2 + 30))
        self.p.bind("<Return>", lambda e: self.login())
        self.u.bind("<Return>", lambda e: self.p.focus_set())
        self.u.focus_set()

        # анимация появления окна
        self.attributes("-alpha", 0)
        self._fade(0)

    def _fade(self, i):
        steps = 12
        self.attributes("-alpha", (i + 1) / steps)
        if i < steps - 1:
            self.after(28, lambda: self._fade(i + 1))

    def _draw_logo(self, cv):
        """Логотип (тарелка + гантель) с анимацией покачивания."""
        x, y = 118, 96
        cv.create_oval(x - 58, y - 58, x + 58, y + 58, fill=PANEL,
                       outline=ACCENT, width=5, tags="logo")
        cv.create_oval(x - 32, y - 32, x + 32, y + 32, outline=ACCENT,
                       width=3, tags="logo")
        cv.create_oval(x - 18, y - 22, x + 14, y + 10, fill=ACCENT, tags="logo")
        bx = x + 58
        cv.create_rectangle(bx - 26, y + 44, bx + 40, y + 54, fill=ACCENT2, tags="logo")
        cv.create_rectangle(bx - 38, y + 30, bx - 22, y + 68, fill=ACCENT2, tags="logo")
        cv.create_rectangle(bx + 36, y + 30, bx + 52, y + 68, fill=ACCENT2, tags="logo")
        self._logo_base_y = 0
        self._logo_cv = cv
        self._bounce(0)

    def _bounce(self, i):
        import math
        dy = int(math.sin(i / 8) * 5)
        if self._logo_base_y != dy:
            self._logo_cv.move("logo", 0, dy - self._logo_base_y)
            self._logo_base_y = dy
        self.after(40, lambda: self._bounce(i + 1))

    def login(self, _e=None):
        user = db.authenticate(self.u.get(), self.p.get())
        if not user:
            self.err.configure(text="Неверный логин или пароль")
            self._shake(6)
            return
        self.app.open_main(user)

    def _shake(self, dx):
        """Анимация «тряски» формы при неверном пароле."""
        if dx == 0:
            cv = self._logo_cv
            cv.move(self.form_win, 0, 0)
            return
        cv = self._logo_cv
        cv.move(self.form_win, dx, 0)
        self.after(45, lambda: self._shake(-int(dx * 0.7)))


# ==================================================================== дашборд
def build_dashboard(app):
    sc = ScreenCanvas(app.host)
    u = db.get_user(app.user["id"])
    today = date.today().isoformat()
    meals = db.meals_all(u["id"])
    workouts = db.workouts_all(u["id"])
    eaten = round(sum(m["kcal"] for m in meals if m["meal_date"] == today))
    burned = round(sum(w["kcal"] for w in workouts if w["workout_date"] == today))
    norm = round(u["weight_kg"] * 33 / 10) * 10
    week_load = round(sum(w["load"] for w in workouts
                          if w["workout_date"] >= (date.today() - timedelta(days=7)).isoformat()))
    LOAD_TARGET = 300  # баллов в неделю (ориентир ВОЗ ~600 MET-мин)

    # --- приветствие ---
    head = tk.Frame(sc, bg=BG)
    label(head, f"Привет, {u['full_name'].split()[0]}!", bg=BG, fg=TEXT,
          font=F_HEADER).pack(side="left")
    label(head, long_date(today), bg=BG, fg=MUTED, font=F_TEXT).pack(side="right")
    sc.add(head)

    # --- карточки показателей ---
    cards = tk.Frame(sc, bg=BG)

    def stat(caption, value, sub, color):
        f, inner = card(cards, color=color)
        label(inner, caption, font=F_SMALL, fg=MUTED).pack()
        label(inner, value, font=("Segoe UI Semibold", 20), fg=TEXT).pack(pady=2)
        label(inner, sub, font=F_SMALL, fg=MUTED).pack()
        f.pack(side="left", fill="both", expand=True, padx=(0, 10))

    stat("Съедено сегодня", f"{eaten} ккал", f"из нормы {norm}", ACCENT)
    stat("Сожжено сегодня", f"{burned} ккал", "на тренировках", ACCENT2)
    bal = eaten - burned
    stat("Баланс дня", f"{bal:+d} ккал", "съедено − сожжено",
         ACCENT if bal <= 0 else DANGER)

    # вес с сохранением (ввод/расчёт нормы)
    f, inner = card(cards, "Мой вес, кг", color=LINE)
    wvar = tk.StringVar(value=str(int(u["weight_kg"])))
    row = tk.Frame(inner, bg=PANEL)
    row.pack(fill="x", pady=3)
    sp = dark_spin(row, wvar, 30, 250, 1, 6)
    sp.pack(side="left", ipady=2)

    def save_weight():
        try:
            w = float(str(wvar.get()).replace(",", "."))
            if not 30 <= w <= 250:
                raise ValueError
        except ValueError:
            app.toast("Вес должен быть числом 30–250", ok=False)
            return
        db.update_weight(u["id"], w)
        db.log(u["id"], "Изменён вес профиля", f"{w:g} кг")
        app.toast(f"Вес сохранён: {w:g} кг. Норма ≈ {round(w * 33 / 10) * 10} ккал/день")
        app.navigate("dashboard")

    HoverButton(row, "✔", save_weight, kind="ghost",
                width=30, height=26, radius=6).pack(side="left", padx=(6, 0))
    label(inner, f"Норма = вес × 33 ≈ {norm} ккал", font=F_SMALL, fg=MUTED).pack()
    f.pack(side="left", fill="both", expand=True)
    sc.add(cards, gap=14)

    # --- кольцевые индикаторы + сводка ---
    row = tk.Frame(sc, bg=BG)
    left = tk.Frame(row, bg=BG)
    left.pack(side="left", fill="y", padx=(0, 12))
    arc_eat = ProgressArc(left, color=ACCENT, title="Питание / норма", bg=BG)
    arc_eat.pack(side="left", padx=(0, 10))
    arc_load = ProgressArc(left, color=ACCENT2, title="Нагрузка за 7 дней", bg=BG)
    arc_load.pack(side="left")

    panel = tk.Frame(row, bg=PANEL)
    panel.pack(side="left", fill="both", expand=True)
    tk.Frame(panel, bg=ACCENT, width=4).pack(side="left", fill="y")
    pr = tk.Frame(panel, bg=PANEL)
    pr.pack(side="left", fill="both", expand=True, padx=14, pady=10)
    label(pr, "Сводка по нагрузке", font=F_TITLE, fg=MUTED).pack(fill="x")
    label(pr, f"За 7 дней набрано {week_load} из {LOAD_TARGET} баллов нагрузки",
          font=F_TEXT, wraplength=420).pack(fill="x", pady=(6, 2))
    label(pr, f"Средняя нагрузка в день ≈ {round(week_load / 7)} баллов",
          font=F_TEXT).pack(fill="x", pady=2)
    days_active = len({w['workout_date'] for w in workouts
                       if w['workout_date'] >= (date.today() - timedelta(days=7)).isoformat()})
    label(pr, f"Тренировочных дней за неделю: {days_active}",
          font=F_TEXT).pack(fill="x", pady=2)
    rec = "Отличный режим — держите темп!" if week_load >= LOAD_TARGET else \
          "Добавьте 20–30 минут кардио, чтобы добрать нагрузку."
    label(pr, rec, font=F_SMALL, fg=ACCENT2, wraplength=420).pack(fill="x", pady=(6, 0))
    sc.add(row, gap=14)

    # --- последние записи ---
    recent = []
    for m in meals[:6]:
        recent.append(dict(id=10000 + m["id"], rtype="Питание",
                           date=m["meal_date"], name=m["product"],
                           kcal=m["kcal"],
                           details=f"{m['meal_type']} · {m['grams']:g} г"))
    for w in workouts[:6]:
        recent.append(dict(id=20000 + w["id"], rtype="Тренировка",
                           date=w["workout_date"], name=w["exercise"],
                           kcal=w["kcal"],
                           details=f"{w['duration_min']:g} мин · пульс {w['avg_hr'] or '—'}"))
    recent.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    recent = recent[:9]
    f, inner = card(sc, "Последние записи", color=LINE)
    table = DataTable(inner, [("rtype", "Тип", 120, "w"), ("date", "Дата", 110, "w"),
                              ("name", "Название", 240, "w"), ("kcal", "Ккал", 70, "e"),
                              ("details", "Детали", 260, "w")],
                      height=8, on_change=sc.relayout)
    table.pack(fill="x")
    table.set_rows(recent)
    sc.add(f, gap=14)

    # --- кнопки ---
    btns = tk.Frame(sc, bg=BG)

    def add_meal():
        MealDialog(app.main, db.products_all(),
                   lambda p: (db.meal_add(u["id"], **p),
                              db.log(u["id"], "Добавлена запись питания",
                                     f"{p['grams']:g} г"),
                              app.toast("Запись питания добавлена"),
                              app.navigate("food")))

    def add_workout():
        WorkoutDialog(app.main, db.exercises_all(), u["weight_kg"],
                      lambda p: (db.workout_add(u["id"], **p),
                                 db.log(u["id"], "Добавлена тренировка",
                                        f"{p['duration_min']:g} мин"),
                                 app.toast("Тренировка добавлена"),
                                 app.navigate("workouts")))

    HoverButton(btns, "＋ Запись питания", add_meal, width=170).pack(side="left")
    HoverButton(btns, "＋ Тренировка", add_workout, kind="accent2",
                width=150).pack(side="left", padx=10)
    HoverButton(btns, "Обновить ↻", lambda: app.navigate("dashboard"),
                kind="ghost", width=120).pack(side="left")
    sc.add(btns)

    # --- анимация индикаторов ---
    def animate_arcs():
        arc_eat.set_value(eaten / norm if norm else 0, f"{eaten}",
                          f"из {norm} ккал", danger_over=eaten > norm)
        arc_load.set_value(week_load / LOAD_TARGET, f"{week_load}",
                           f"из {LOAD_TARGET} баллов", color=ACCENT2)
    sc.after(350, animate_arcs)
    return sc


# ==================================================================== питание
def build_food(app, search=None):
    sc = ScreenCanvas(app.host)
    uid = app.user["id"]
    is_admin = app.is_admin
    state = {"rows": []}

    top = tk.Frame(sc, bg=BG)
    label(top, "Дневник питания", bg=BG, fg=TEXT, font=F_HEADER).pack(side="left")
    totals = label(top, "", bg=BG, fg=ACCENT, font=F_TITLE)
    totals.pack(side="right")
    sc.add(top)

    # --- фильтры ---
    fl = tk.Frame(sc, bg=PANEL)
    inner_fl = tk.Frame(fl, bg=PANEL)
    inner_fl.pack(fill="x", padx=12, pady=9)
    label(inner_fl, "Период:", fg=MUTED).pack(side="left")
    from tkinter import ttk
    period_cb = ttk.Combobox(inner_fl, values=[p[0] for p in PERIODS],
                             state="readonly", style="Diary.TCombobox", width=11)
    period_cb.current(0)
    period_cb.pack(side="left", padx=(6, 12))
    label(inner_fl, "Приём:", fg=MUTED).pack(side="left")
    type_cb = ttk.Combobox(inner_fl, values=["Все"] + db.MEAL_TYPES,
                           state="readonly", style="Diary.TCombobox", width=10)
    type_cb.current(0)
    type_cb.pack(side="left", padx=6)
    user_cb = None
    if is_admin:
        label(inner_fl, "Пользователь:", fg=MUTED).pack(side="left")
        user_cb = ttk.Combobox(inner_fl, values=["Все"] +
                               [u["username"] for u in db.all_users()],
                               state="readonly", style="Diary.TCombobox", width=10)
        user_cb.current(0)
        user_cb.pack(side="left", padx=6)
    q = dark_entry(inner_fl, width=18)
    placeholder(q, "🔍 поиск продукта…")
    q.pack(side="left", padx=6)
    label(inner_fl, "Сортировка — клик по заголовку столбца",
          fg=MUTED, font=F_SMALL).pack(side="right")
    sc.add(fl, gap=10)

    cols = [("date", "Дата", 100, "w"), ("meal_type", "Приём", 90, "w"),
            ("product", "Продукт", 230, "w"), ("grams", "Граммы", 80, "e"),
            ("kcal", "Ккал", 80, "e"), ("prot", "Белки", 70, "e"),
            ("fat_g", "Жиры", 70, "e"), ("carb", "Углеводы", 80, "e")]
    if is_admin:
        cols.append(("user", "Пользователь", 160, "w"))
    f_tbl, inner_tbl = card(sc, color=LINE)
    table = DataTable(inner_tbl, cols, height=13, on_change=sc.relayout)
    table.pack(fill="x")
    sc.add(f_tbl, gap=10)

    def refresh():
        rows = db.meals_all(None if is_admin else uid)
        days = dict(PERIODS)[period_cb.get()]
        cutoff = (date.today() - timedelta(days=days)).isoformat() if days else None
        mtype = type_cb.get()
        uname = user_cb.get() if user_cb else "Все"
        sub = entry_value(q).lower()
        out = []
        for r in rows:
            r["date"] = r["meal_date"]
            if cutoff and r["meal_date"] < cutoff:
                continue
            if mtype != "Все" and r["meal_type"] != mtype:
                continue
            if uname != "Все" and not r["user"].lower().startswith(uname.lower()):
                continue
            if sub and sub not in r["product"].lower():
                continue
            out.append(r)
        state["rows"] = out
        table.set_rows(out)
        tot_k = round(sum(r["kcal"] for r in out))
        totals.configure(text=f"Записей: {len(out)}   ·   Калорий всего: {tot_k}   "
                              f"·   Б {round(sum(r['prot'] for r in out))} / "
                              f"Ж {round(sum(r['fat_g'] for r in out))} / "
                              f"У {round(sum(r['carb'] for r in out))} г")
        sc.relayout()

    filter_cbs = [period_cb, type_cb]
    if user_cb:
        filter_cbs.append(user_cb)
    for w in filter_cbs:
        w.bind("<<ComboboxSelected>>", lambda e: refresh())
    q.bind("<KeyRelease>", lambda e: refresh())

    btns = tk.Frame(sc, bg=BG)

    def sel_row():
        r = table.selected_row()
        if not r:
            app.toast("Выберите запись в таблице", ok=False)
        return r

    def add():
        MealDialog(app.main, db.products_all(), on_add, default_user_weight=None)

    def on_add(p):
        db.meal_add(uid, **p)
        db.log(uid, "Добавлена запись питания", f"{p['grams']:g} г")
        app.toast("Запись добавлена")
        refresh()

    def edit():
        r = sel_row()
        if not r:
            return
        MealDialog(app.main, db.products_all(),
                   lambda p: (db.meal_update(r["id"], **p),
                              db.log(uid, "Изменена запись питания", r["product"]),
                              app.toast("Запись изменена"), refresh()),
                   record=r)

    def delete():
        r = sel_row()
        if not r:
            return
        if not app.confirm(f"Удалить запись «{r['product']}» от {fmt_date(r['meal_date'])}?"):
            return
        db.meal_delete(r["id"])
        db.log(uid, "Удалена запись питания", r["product"])
        app.toast("Запись удалена")
        refresh()

    HoverButton(btns, "＋ Добавить", add, width=130).pack(side="left")
    HoverButton(btns, "✎ Изменить", edit, kind="ghost", width=120).pack(side="left", padx=10)
    HoverButton(btns, "🗑 Удалить", delete, kind="danger", width=120).pack(side="left")
    sc.add(btns)

    if search:
        q.delete(0, "end")
        q.insert(0, search)
        q.configure(fg=TEXT)
    refresh()
    return sc


# ==================================================================== тренировки
def build_workouts(app, search=None):
    sc = ScreenCanvas(app.host)
    uid = app.user["id"]
    is_admin = app.is_admin
    state = {"rows": []}

    top = tk.Frame(sc, bg=BG)
    label(top, "Дневник тренировок", bg=BG, fg=TEXT, font=F_HEADER).pack(side="left")
    totals = label(top, "", bg=BG, fg=ACCENT2, font=F_TITLE)
    totals.pack(side="right")
    sc.add(top)

    fl = tk.Frame(sc, bg=PANEL)
    inner_fl = tk.Frame(fl, bg=PANEL)
    inner_fl.pack(fill="x", padx=12, pady=9)
    label(inner_fl, "Период:", fg=MUTED).pack(side="left")
    from tkinter import ttk
    period_cb = ttk.Combobox(inner_fl, values=[p[0] for p in PERIODS],
                             state="readonly", style="Diary.TCombobox", width=11)
    period_cb.current(0)
    period_cb.pack(side="left", padx=(6, 12))
    label(inner_fl, "Группа мышц:", fg=MUTED).pack(side="left")
    groups = sorted({e["muscle_group"] for e in db.exercises_all()})
    grp_cb = ttk.Combobox(inner_fl, values=["Все"] + groups, state="readonly",
                          style="Diary.TCombobox", width=11)
    grp_cb.current(0)
    grp_cb.pack(side="left", padx=6)
    user_cb = None
    if is_admin:
        label(inner_fl, "Пользователь:", fg=MUTED).pack(side="left")
        user_cb = ttk.Combobox(inner_fl, values=["Все"] +
                               [u["username"] for u in db.all_users()],
                               state="readonly", style="Diary.TCombobox", width=10)
        user_cb.current(0)
        user_cb.pack(side="left", padx=6)
    q = dark_entry(inner_fl, width=18)
    placeholder(q, "🔍 поиск упражнения…")
    q.pack(side="left", padx=6)
    label(inner_fl, "Сортировка — клик по заголовку", fg=MUTED, font=F_SMALL).pack(side="right")
    sc.add(fl, gap=10)

    cols = [("date", "Дата", 100, "w"), ("exercise", "Упражнение", 220, "w"),
            ("muscle_group", "Группа", 100, "w"), ("duration_min", "Мин", 60, "e"),
            ("kcal", "Ккал", 80, "e"), ("load", "Нагрузка", 90, "e"),
            ("avg_hr", "Пульс", 65, "e")]
    if is_admin:
        cols.append(("user", "Пользователь", 160, "w"))
    f_tbl, inner_tbl = card(sc, color=LINE)
    table = DataTable(inner_tbl, cols, height=13, on_change=sc.relayout)
    table.pack(fill="x")
    sc.add(f_tbl, gap=10)

    def refresh():
        rows = db.workouts_all(None if is_admin else uid)
        days = dict(PERIODS)[period_cb.get()]
        cutoff = (date.today() - timedelta(days=days)).isoformat() if days else None
        grp = grp_cb.get()
        uname = user_cb.get() if user_cb else "Все"
        sub = entry_value(q).lower()
        out = []
        for r in rows:
            r["date"] = r["workout_date"]
            if cutoff and r["workout_date"] < cutoff:
                continue
            if grp != "Все" and r["muscle_group"] != grp:
                continue
            if uname != "Все" and not r["user"].lower().startswith(uname.lower()):
                continue
            if sub and sub not in r["exercise"].lower():
                continue
            out.append(r)
        state["rows"] = out
        table.set_rows(out)
        totals.configure(text=f"Записей: {len(out)}   ·   Сожжено: "
                              f"{round(sum(r['kcal'] for r in out))} ккал   ·   "
                              f"Нагрузка: {round(sum(r['load'] for r in out))} баллов")
        sc.relayout()

    filter_cbs = [period_cb, grp_cb]
    if user_cb:
        filter_cbs.append(user_cb)
    for w in filter_cbs:
        w.bind("<<ComboboxSelected>>", lambda e: refresh())
    q.bind("<KeyRelease>", lambda e: refresh())

    btns = tk.Frame(sc, bg=BG)

    def sel_row():
        r = table.selected_row()
        if not r:
            app.toast("Выберите тренировку в таблице", ok=False)
        return r

    def add():
        WorkoutDialog(app.main, db.exercises_all(), db.get_user(uid)["weight_kg"], on_add)

    def on_add(p):
        db.workout_add(uid, **p)
        db.log(uid, "Добавлена тренировка", f"{p['duration_min']:g} мин")
        app.toast("Тренировка добавлена")
        refresh()

    def edit():
        r = sel_row()
        if not r:
            return
        WorkoutDialog(app.main, db.exercises_all(), r["weight_kg"],
                      lambda p: (db.workout_update(r["id"], **p),
                                 db.log(uid, "Изменена тренировка", r["exercise"]),
                                 app.toast("Тренировка изменена"), refresh()),
                      record=r)

    def delete():
        r = sel_row()
        if not r:
            return
        if not app.confirm(f"Удалить тренировку «{r['exercise']}» от {fmt_date(r['workout_date'])}?"):
            return
        db.workout_delete(r["id"])
        db.log(uid, "Удалена тренировка", r["exercise"])
        app.toast("Тренировка удалена")
        refresh()

    HoverButton(btns, "＋ Добавить", add, kind="accent2", width=130).pack(side="left")
    HoverButton(btns, "✎ Изменить", edit, kind="ghost", width=120).pack(side="left", padx=10)
    HoverButton(btns, "🗑 Удалить", delete, kind="danger", width=120).pack(side="left")
    sc.add(btns)

    if search:
        q.delete(0, "end")
        q.insert(0, search)
        q.configure(fg=TEXT)
    refresh()
    return sc


# ==================================================================== о программе
def build_about(app):
    sc = ScreenCanvas(app.host)

    top = tk.Frame(sc, bg=BG)
    label(top, "О программе", bg=BG, fg=TEXT, font=F_HEADER).pack(side="left")
    sc.add(top)

    # --- карточка с автором ---
    f, inner = card(sc, color=ACCENT)
    label(inner, APP_TITLE + "  ·  версия " + APP_VERSION, font=F_HEADER,
          fg=TEXT).pack(pady=(4, 6))
    label(inner, "Разработал:", font=F_SMALL, fg=MUTED).pack()
    label(inner, AUTHOR_NAME, font=("Segoe UI Semibold", 16), fg=ACCENT).pack(pady=1)
    label(inner, f"Группа: {AUTHOR_GROUP}", font=F_TITLE, fg=TEXT).pack(pady=(0, 8))
    label(inner, "Учебный проект: дневник питания и тренировок с расчётом нагрузки.\n"
                 "Стек: Python 3.12, Tkinter (интерфейс написан вручную), SQLite (БД).\n"
                 "Расчёты: калории по формуле ACSM (MET × 3.5 × вес / 200 × мин), "
                 "нагрузка в баллах = MET × мин / 10.",
          font=F_TEXT, fg=TEXT, justify="left", wraplength=820).pack(pady=(2, 4))
    sc.add(f, gap=12)

    # --- ряд из трёх карточек ---
    row = tk.Frame(sc, bg=BG)

    # статистика БД
    f1, i1 = card(row, "Статистика базы данных", color=ACCENT2)
    c = db.counts()
    label(i1, f"Пользователей: {c['users']} · Продуктов: {c['products']} · "
              f"Упражнений: {c['exercises']}", fg=TEXT).pack(fill="x", pady=1)
    label(i1, f"Записей питания: {c['meals']} · Тренировок: {c['workouts']} · "
              f"Событий журнала: {c['action_log']}", fg=TEXT).pack(fill="x", pady=1)
    fk_lbl = label(i1, "", fg=ACCENT, font=F_SMALL, wraplength=280)
    fk_lbl.pack(fill="x", pady=(4, 0))

    def check_fk():
        bad = db.fk_check()
        fk_lbl.configure(text="✔ Целостность внешних ключей: OK, нарушений нет"
                         if not bad else f"✘ Найдены нарушения: {bad}",
                         fg=ACCENT if not bad else DANGER)
        app.toast("Проверка целостности БД выполнена")

    HoverButton(i1, "Проверить связи БД", check_fk, kind="ghost", width=170,
                height=28).pack(pady=(8, 0), anchor="w")
    f1.pack(side="left", fill="both", expand=True, padx=(0, 10))

    # палитра (клик по кружку показывает HEX)
    f2, i2 = card(row, "Палитра (кликните цвет)", color=ACCENT)
    pal = tk.Canvas(i2, bg=PANEL, width=270, height=52, highlightthickness=0)
    pal.pack()
    chosen = label(i2, "Выберите цвет", fg=MUTED, font=F_SMALL)
    chosen.pack(fill="x")
    swatches = [(ACCENT, "зелёный — питание/успех"), (ACCENT2, "оранжевый — тренировки"),
                (DANGER, "красный — ошибки"), (PANEL_2, "панели"), (BG, "фон")]
    for i, (col, name) in enumerate(swatches):
        x = 20 + i * 52
        pal.create_oval(x, 10, x + 36, 46, fill=col, outline=LINE,
                        tags=f"sw{i}")
        pal.create_text(x + 18, 28, text=col[1:].upper()[:4], fill=TEXT
                        if col not in (BG, PANEL_2) else MUTED, font=F_SMALL)
        pal.tag_bind(f"sw{i}", "<Button-1>",
                     lambda e, c_=col, n_=name: chosen.configure(
                         text=f"{n_}: {c_}", fg=c_ if c_ not in (BG,) else TEXT))
    f2.pack(side="left", fill="both", expand=True, padx=(0, 10))

    # шрифты
    f3, i3 = card(row, "Шрифтовая пара", color=LINE)
    label(i3, "Segoe UI Semibold — заголовки", font=("Segoe UI Semibold", 12),
          fg=TEXT).pack(fill="x", pady=1)
    label(i3, "Segoe UI — основной текст", font=F_TEXT, fg=TEXT).pack(fill="x", pady=1)
    label(i3, "Consolas — таблицы и цифры", font=F_MONO, fg=TEXT).pack(fill="x", pady=1)
    label(i3, "Пара подобрана по принципу «один гротеск, два веса + моноширинный "
              "для данных» (fontjoy / mixfont).", font=F_SMALL, fg=MUTED,
          wraplength=280).pack(fill="x", pady=(4, 0))
    f3.pack(side="left", fill="both", expand=True)
    sc.add(row, gap=12)

    # --- кнопки ---
    btns = tk.Frame(sc, bg=BG)

    def copy_contacts():
        app.main.clipboard_clear()
        app.main.clipboard_append(f"{AUTHOR_NAME}, группа {AUTHOR_GROUP}")
        app.toast("ФИО и группа скопированы в буфер обмена")

    HoverButton(btns, "Скопировать контакты", copy_contacts,
                width=190).pack(side="left")
    HoverButton(btns, "Журнал действий", lambda: app.navigate("log") if app.is_admin
                else app.toast("Доступно только администратору", ok=False),
                kind="ghost", width=150).pack(side="left", padx=10)
    sc.add(btns)
    return sc
