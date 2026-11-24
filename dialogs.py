# -*- coding: utf-8 -*-
"""
dialogs.py — модальные окна приложения (форма, расчёт «на лету», поиск).
Каждое окно открывается с анимацией (плавное появление + сдвиг вниз).
"""
import tkinter as tk
from datetime import date, datetime

from theme import (PANEL, PANEL_2, LINE, ACCENT, ACCENT2, TEXT, MUTED,
                   F_TITLE, F_TEXT, F_SMALL, APP_TITLE)
from ui import HoverButton, dark_entry, dark_spin, label, lerp

MEAL_TYPES = ["Завтрак", "Обед", "Ужин", "Перекус"]


class Dialog(tk.Toplevel):
    """Базовое модальное окно с анимацией появления (alpha + сдвиг)."""

    def __init__(self, master, title, width=430):
        super().__init__(master)
        self.configure(bg=PANEL)
        self.title(title)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.attributes("-alpha", 0)
        x = master.winfo_rootx() + max(0, (master.winfo_width() - width) // 2)
        y = master.winfo_rooty() + 90
        self.geometry(f"{width}x{self.winfo_reqheight()}+{x}+{y}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.body = tk.Frame(self, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=18, pady=16)
        self._open_anim(0)
        self.after(30, self.grab_set)

    def _open_anim(self, i):
        steps = 8
        self.attributes("-alpha", (i + 1) / steps)
        try:
            gx, gy = self.geometry().split("+")[1:]
            self.geometry(f"+{gx}+{int(gy) + (2 if i < steps else 0)}")
        except Exception:
            pass
        if i < steps - 1:
            self.after(22, lambda: self._open_anim(i + 1))

    # --- конструктор форм ---
    def field(self, caption, widget):
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x", pady=4)
        label(row, caption, font=F_TEXT, width=17).pack(side="left", anchor="n")
        widget.pack(side="left", fill="x", expand=True)
        return widget

    def buttons(self, on_save, save_text="Сохранить"):
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x", pady=(14, 0))
        HoverButton(row, save_text, command=on_save, width=140).pack(side="right")
        HoverButton(row, "Отмена", command=self.destroy, kind="ghost",
                    width=100).pack(side="right", padx=(0, 8))


def parse_date(s: str):
    """Строка -> datetime.date, иначе ValueError."""
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def parse_float(s: str, what="число") -> float:
    s = s.strip().replace(",", ".")
    v = float(s)
    if v < 0:
        raise ValueError(what)
    return v


# ==================================================================== записи
class MealDialog(Dialog):
    """Добавление/редактирование записи питания с расчётом калорий и БЖУ."""

    def __init__(self, master, products, on_done, record=None, default_user_weight=None):
        self.record = record
        self.products = products
        self.on_done = on_done
        super().__init__(master, "Редактирование записи питания" if record
                         else "Новая запись питания", width=470)

        self.product_var = tk.StringVar()
        from tkinter import ttk
        names = [f"{p['name']}  ({p['kcal_per_100g']:g} ккал/100 г)" for p in products]
        self.cb = ttk.Combobox(self.body, textvariable=self.product_var,
                               values=names, state="readonly",
                               style="Diary.TCombobox", width=36)
        self.field("Продукт:", self.cb)
        if record:
            for i, p in enumerate(products):
                if p["id"] == record["product_id"]:
                    self.cb.current(i)
                    break
        elif names:
            self.cb.current(0)

        self.grams_var = tk.StringVar(value=str(int(record["grams"])) if record else "150")
        self.sp = dark_spin(self.body, self.grams_var, 5, 3000, 5, 8)
        self.field("Граммы:", self.sp)

        self.date_var = tk.StringVar(value=record["meal_date"] if record
                                     else date.today().isoformat())
        self.field("Дата (ГГГГ-ММ-ДД):", dark_entry(self.body, self.date_var, 14))

        self.type_var = tk.StringVar(value=record["meal_type"] if record else MEAL_TYPES[0])
        self.cb_type = ttk.Combobox(self.body, textvariable=self.type_var,
                                    values=MEAL_TYPES, state="readonly",
                                    style="Diary.TCombobox", width=14)
        self.field("Приём пищи:", self.cb_type)

        self.calc_lbl = label(self.body, "", fg=ACCENT, font=F_TITLE)
        self.calc_lbl.pack(fill="x", pady=(10, 0))

        for w in (self.cb, self.cb_type):
            w.bind("<<ComboboxSelected>>", lambda e: self.recalc())
        self.sp.configure(command=self.recalc)
        self.grams_var.trace_add("write", lambda *a: self.recalc())
        self.recalc()
        self.buttons(self.save)

    def recalc(self):
        """Расчёт калорий и БЖУ прямо в окне ввода."""
        idx = self.cb.current()
        if idx < 0:
            return
        p = self.products[idx]
        try:
            g = float(self.grams_var.get().replace(",", "."))
        except ValueError:
            self.calc_lbl.configure(text="Введите граммы", fg="#E9575B")
            return
        k = p["kcal_per_100g"] * g / 100
        self.calc_lbl.configure(
            text=f"≈ {k:.0f} ккал · Б {p['protein'] * g / 100:.1f} · "
                 f"Ж {p['fat'] * g / 100:.1f} · У {p['carbs'] * g / 100:.1f}",
            fg=ACCENT)

    def save(self):
        idx = self.cb.current()
        if idx < 0:
            return
        p = self.products[idx]
        try:
            g = parse_float(self.grams_var.get(), "граммы")
            parse_date(self.date_var.get())
        except ValueError as e:
            self.calc_lbl.configure(
                text=f"Ошибка ввода: {e} (дата в формате ГГГГ-ММ-ДД)",
                fg="#E9575B")
            return
        payload = dict(product_id=p["id"], meal_date=self.date_var.get().strip(),
                       meal_type=self.type_var.get(), grams=g)
        self.destroy()
        self.on_done(payload)


class WorkoutDialog(Dialog):
    """Добавление/редактирование тренировки: расчёт ккал (ACSM) и нагрузки."""

    def __init__(self, master, exercises, weight_kg, on_done, record=None):
        self.record = record
        self.exercises = exercises
        self.weight_kg = weight_kg
        self.on_done = on_done
        super().__init__(master, "Редактирование тренировки" if record
                         else "Новая тренировка", width=470)

        from tkinter import ttk
        self.ex_var = tk.StringVar()
        names = [f"{e['name']}  (MET {e['met']:g})" for e in exercises]
        self.cb = ttk.Combobox(self.body, textvariable=self.ex_var, values=names,
                               state="readonly", style="Diary.TCombobox", width=36)
        self.field("Упражнение:", self.cb)
        if record:
            for i, e in enumerate(exercises):
                if e["id"] == record["exercise_id"]:
                    self.cb.current(i)
                    break
        elif names:
            self.cb.current(0)

        self.min_var = tk.StringVar(value=str(int(record["duration_min"])) if record else "40")
        self.sp = dark_spin(self.body, self.min_var, 5, 600, 5, 8)
        self.field("Длительность, мин:", self.sp)

        self.hr_var = tk.StringVar(value=str(record["avg_hr"] or "") if record else "")
        self.field("Средний пульс:", dark_entry(self.body, self.hr_var, 8))
        self.date_var = tk.StringVar(value=record["workout_date"] if record
                                     else date.today().isoformat())
        self.field("Дата (ГГГГ-ММ-ДД):", dark_entry(self.body, self.date_var, 14))

        self.calc_lbl = label(self.body, "", fg=ACCENT2, font=F_TITLE)
        self.calc_lbl.pack(fill="x", pady=(10, 0))

        self.cb.bind("<<ComboboxSelected>>", lambda e: self.recalc())
        self.sp.configure(command=self.recalc)
        self.min_var.trace_add("write", lambda *a: self.recalc())
        self.recalc()
        self.buttons(self.save)

    def recalc(self):
        idx = self.cb.current()
        if idx < 0:
            return
        e = self.exercises[idx]
        try:
            m = float(self.min_var.get().replace(",", "."))
        except ValueError:
            self.calc_lbl.configure(text="Введите минуты", fg="#E9575B")
            return
        kcal = e["met"] * 3.5 * self.weight_kg / 200 * m      # формула ACSM
        load = e["met"] * m / 10                              # баллы нагрузки
        self.calc_lbl.configure(text=f"Сожжено ≈ {kcal:.0f} ккал · "
                                     f"нагрузка {load:.0f} баллов", fg=ACCENT2)

    def save(self):
        idx = self.cb.current()
        if idx < 0:
            return
        e = self.exercises[idx]
        hr = None
        if self.hr_var.get().strip():
            try:
                hr = int(self.hr_var.get())
            except ValueError:
                self.calc_lbl.configure(text="Пульс — целое число", fg="#E9575B")
                return
        try:
            m = parse_float(self.min_var.get(), "минуты")
            parse_date(self.date_var.get())
        except ValueError as ex:
            self.calc_lbl.configure(text=f"Ошибка ввода: {ex}", fg="#E9575B")
            return
        payload = dict(exercise_id=e["id"], workout_date=self.date_var.get().strip(),
                       duration_min=m, avg_hr=hr)
        self.destroy()
        self.on_done(payload)


class UserDialog(Dialog):
    def __init__(self, master, on_done, record=None):
        self.record, self.on_done = record, on_done
        super().__init__(master, "Пользователь", width=440)
        self.u_var = tk.StringVar(value=record["username"] if record else "")
        self.field("Логин:", dark_entry(self.body, self.u_var, 18))
        self.f_var = tk.StringVar(value=record["full_name"] if record else "")
        self.field("ФИО:", dark_entry(self.body, self.f_var, 26))
        from tkinter import ttk
        self.r_var = tk.StringVar(value=record["role"] if record else "user")
        self.cb = ttk.Combobox(self.body, textvariable=self.r_var,
                               values=["user", "admin"], state="readonly",
                               style="Diary.TCombobox", width=10)
        self.field("Роль:", self.cb)
        self.w_var = tk.StringVar(value=str(record["weight_kg"]) if record else "70")
        self.field("Вес, кг:", dark_spin(self.body, self.w_var, 30, 250, 1, 7))
        self.p_var = tk.StringVar()
        self.field("Пароль" + (" (пусто — не менять):" if record else ":"),
                   dark_entry(self.body, self.p_var, 18, show="•"))
        self.buttons(self.save)

    def save(self):
        if not self.u_var.get().strip() or not self.f_var.get().strip():
            self.title("Логин и ФИО обязательны")
            return
        if not self.record and not self.p_var.get():
            self.title("Для нового пользователя нужен пароль")
            return
        try:
            w = parse_float(self.w_var.get(), "вес")
        except ValueError:
            self.title("Вес указан неверно")
            return
        self.destroy()
        self.on_done(dict(username=self.u_var.get(), full_name=self.f_var.get(),
                          role=self.r_var.get(), weight_kg=w,
                          password=self.p_var.get() or None))


# ==================================================================== поиск
class SearchWindow(tk.Toplevel):
    """Сквозной поиск по всему приложению (результаты со всех таблиц)."""

    def __init__(self, main, query):
        super().__init__(main)
        self.app = main          # главное окно: роли, навигация, пользователь
        self.configure(bg=PANEL)
        self.title(f"Поиск: {query}")
        self.geometry("760x420")
        self.transient(main)
        self.attributes("-alpha", 0)
        self._open_anim(0)
        tk.Label(self, text=f"Результаты поиска «{query}»", bg=PANEL,
                 fg=TEXT, font=F_TITLE, anchor="w").pack(fill="x", padx=16, pady=(14, 6))
        self.info = label(self, "", fg=MUTED, font=F_SMALL)
        self.info.pack(fill="x", padx=16)
        from tkinter import ttk
        cols = ("kind", "name", "details")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12,
                                 style="Diary.Treeview")
        for k, t, w, a in (("kind", "Тип", 150, "w"), ("name", "Название", 240, "w"),
                           ("details", "Подробности", 300, "w")):
            self.tree.heading(k, text=t)
            self.tree.column(k, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True, padx=16, pady=(8, 4))
        self.tree.bind("<Double-1>", self._go)
        HoverButton(self, "Перейти", command=self._go, width=120).pack(pady=(4, 12))
        self._fill(query)
        self.after(30, self.grab_set)

    def _open_anim(self, i):
        steps = 8
        self.attributes("-alpha", (i + 1) / steps)
        if i < steps - 1:
            self.after(22, lambda: self._open_anim(i + 1))

    def _fill(self, query):
        import db
        q = f"%{query}%"
        uid = None if self.app.is_admin else self.app.user["id"]
        rows = []
        for p in db.products_all():
            if query.lower() in p["name"].lower() or query.lower() in p["category"].lower():
                rows.append(("Продукт", p["name"],
                             f"{p['category']} · {p['kcal_per_100g']:g} ккал/100 г",
                             ("food", None, p["name"])))
        for e in db.exercises_all():
            if query.lower() in e["name"].lower() or query.lower() in e["muscle_group"].lower():
                rows.append(("Упражнение", e["name"],
                             f"{e['muscle_group']} · MET {e['met']:g}",
                             ("workouts", None, e["name"])))
        for m in db.meals_all(uid):
            if query.lower() in m["product"].lower():
                rows.append(("Запись питания", m["product"],
                             f"{m['meal_date']} · {m['meal_type']} · {m['kcal']} ккал",
                             ("food", None, m["product"])))
        for w in db.workouts_all(uid):
            if query.lower() in w["exercise"].lower():
                rows.append(("Тренировка", w["exercise"],
                             f"{w['workout_date']} · {w['duration_min']:g} мин · {w['kcal']} ккал",
                             ("workouts", None, w["exercise"])))
        if self.app.is_admin:
            for u in db.all_users():
                if query.lower() in u["username"].lower() or query.lower() in u["full_name"].lower():
                    rows.append(("Пользователь", u["username"],
                                 f"{u['full_name']} · {u['role']}",
                                 ("users", None, u["username"])))
        self.rows = rows
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            self.tree.insert("", "end", iid=str(i), values=r[:3])
        self.info.configure(text=f"Найдено записей: {len(rows)}. "
                                 "Двойной клик или кнопка «Перейти» — переход к разделу.")

    def _go(self, _e=None):
        sel = self.tree.selection()
        if not sel:
            return
        screen, tab, name = self.rows[int(sel[0])][3]
        self.destroy()
        self.app.navigate(screen, tab=tab, search=name)
