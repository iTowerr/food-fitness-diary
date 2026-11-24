# -*- coding: utf-8 -*-
"""
ui.py — переиспользуемые компоненты интерфейса и все анимации приложения:
  • HoverButton    — кнопка с анимацией наведения/нажатия (плавная смена цвета)
  • Particles      — живой анимированный фон (работает сам, без пользователя)
  • ScreenCanvas   — экран-холст с плавным «въездом» (переход между экранами)
  • ProgressArc    — кольцевой индикатор с анимацией заполнения
  • DataTable      — таблица с сортировкой кликом по заголовку
"""
import math
import random
import tkinter as tk
from tkinter import ttk

from theme import (BG, PANEL, PANEL_2, LINE, ACCENT, ACCENT_D, ACCENT2, DANGER,
                   TEXT, MUTED, ENTRY_BG, F_TEXT, F_SMALL, F_TITLE, F_BTN)

# ------------------------------------------------------------------ утилиты
def lerp(c1: str, c2: str, t: float) -> str:
    """Смешивание hex-цветов для плавных переходов."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def rounded_pts(x1, y1, x2, y2, r):
    """Точки для create_polygon(smooth=True) — скруглённый прямоугольник."""
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


_STYLES_DONE = False


def setup_styles(root):
    """Тёмная тема для ttk-виджетов (таблицы, комбобоксы, вкладки)."""
    global _STYLES_DONE
    if _STYLES_DONE:
        return
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Diary.Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=TEXT, rowheight=26, borderwidth=0, font=F_TEXT)
    style.map("Diary.Treeview",
              background=[("selected", ACCENT_D)],
              foreground=[("selected", "#06130b")])
    style.configure("Diary.Treeview.Heading", background=PANEL_2, foreground=TEXT,
                    font=("Segoe UI Semibold", 9), borderwidth=0, padding=(6, 5))
    style.map("Diary.Treeview.Heading", background=[("active", LINE)])
    style.configure("Diary.TCombobox", fieldbackground=ENTRY_BG, background=PANEL_2,
                    foreground=TEXT, arrowcolor=ACCENT, bordercolor=LINE,
                    lightcolor=PANEL_2, darkcolor=PANEL_2, borderwidth=1, padding=4)
    style.map("Diary.TCombobox",
              fieldbackground=[("readonly", ENTRY_BG)],
              foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background", PANEL_2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_D)
    root.option_add("*TCombobox*Listbox.selectForeground", "#06130b")
    style.configure("Diary.TNotebook", background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("Diary.TNotebook.Tab", background=PANEL_2, foreground=MUTED,
                    padding=[18, 8], font=("Segoe UI Semibold", 10), borderwidth=0)
    style.map("Diary.TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#06130b")])
    style.configure("Diary.Vertical.TScrollbar", background=PANEL_2, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED)
    style.configure("Diary.Horizontal.TScrollbar", background=PANEL_2, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED)
    _STYLES_DONE = True


# ------------------------------------------------------------------ кнопка
class HoverButton(tk.Canvas):
    """Кнопка-холст: скруглённые углы + анимации наведения, нажатия, возврата."""
    KINDS = {
        "accent":  dict(base=ACCENT,  hover="#4bdc8a", press=ACCENT_D,  fg="#06130b"),
        "accent2": dict(base=ACCENT2, hover="#ffb26a", press="#e8862f", fg="#241203"),
        "ghost":   dict(base=PANEL_2, hover=LINE,      press="#182731", fg=TEXT),
        "danger":  dict(base=DANGER,  hover="#ef7672", press="#c7443f", fg="#2a0708"),
    }

    def __init__(self, master, text, command=None, kind="accent", width=150,
                 height=36, font=None, radius=9):
        super().__init__(master, width=width, height=height, highlightthickness=0,
                         bd=0, cursor="hand2", bg=master["bg"])
        self.command = command
        self.text = text
        self.font = font or F_BTN
        self.radius = radius
        self.k = self.KINDS[kind]
        self.fill = self.k["base"]
        self._pressed = False
        self._job = None
        self.bind("<Enter>", lambda e: self._glide(self.k["hover"]))
        self.bind("<Leave>", lambda e: self._glide(self.k["base"]))
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def _glide(self, target):
        """Плавная интерполяция цвета к целевому (анимация)."""
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

        def step():
            if self.fill == target:
                self._draw()
                return
            self.fill = lerp(self.fill, target, 0.38)
            self._draw()
            self._job = self.after(26, step)
        step()

    def _on_press(self, _e):
        self._pressed = True
        self._glide(self.k["press"])
        self._draw()

    def _on_release(self, e):
        if not self._pressed:
            return
        self._pressed = False
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._glide(self.k["hover"] if inside else self.k["base"])
        self._draw()
        if inside and self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or int(self["width"])
        h = self.winfo_height() or int(self["height"])
        dy = 2 if self._pressed else 0
        self.create_polygon(rounded_pts(1, 1 + dy, w - 2, h - 1, self.radius),
                            smooth=True, fill=self.fill, outline="")
        self.create_text(w // 2, h // 2 + dy, text=self.text,
                         fill=self.k["fg"], font=self.font)


# ------------------------------------------------------------------ фон
class Particles:
    """Живой фон: пузырьки всплывают, большие «орбы» медленно тонут.
    Работает постоянно сам по себе (after-цикл ~30 к/с)."""

    def __init__(self, canvas: tk.Canvas, n_small=22, n_big=4):
        self.cv = canvas
        self.n_small, self.n_big = n_small, n_big
        self.parts = []
        self.spawned = False
        self.job = None
        canvas.bind("<Configure>", self._on_cfg, add="+")
        canvas.bind("<Destroy>", lambda e: self.stop(), add="+")

    def _on_cfg(self, e):
        if not self.spawned and e.width > 80 and e.height > 60:
            self._spawn(e.width, e.height)
        elif self.spawned:
            w, h = self.cv.winfo_width(), self.cv.winfo_height()
            for p in self.parts:
                p["x"] = min(max(p["x"], -p["r"]), w + p["r"])
                p["y"] = min(max(p["y"], -p["r"]), h + p["r"])

    def _spawn(self, w, h):
        rnd = random.Random()
        big_cols = ["#152631", "#122230", "#142a2b", "#132430"]
        sml_cols = ["#1c4a39", "#1a4034", "#1e5541", "#193a4a"]
        for i in range(self.n_small + self.n_big):
            big = i >= self.n_small
            r = rnd.randint(60, 130) if big else rnd.randint(3, 12)
            col = rnd.choice(big_cols if big else sml_cols)
            pid = self.cv.create_oval(-r, -r, r, r, fill=col, outline="")
            self.cv.tag_lower(pid)
            self.parts.append(dict(
                id=pid, r=r,
                x=rnd.uniform(0, w), y=rnd.uniform(0, h),
                vy=(rnd.uniform(0.04, 0.16) if big else -rnd.uniform(0.18, 0.8)),
                phase=rnd.uniform(0, 6.28),
                amp=rnd.uniform(0.08, 0.5),
                spd=rnd.uniform(0.004, 0.013),
                up=not big))
        self.spawned = True
        self._loop()

    def _loop(self):
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        for p in self.parts:
            p["y"] += p["vy"]
            p["phase"] += p["spd"]
            p["x"] += math.sin(p["phase"]) * p["amp"]
            if p["up"] and p["y"] < -p["r"] - 4:
                p["y"] = h + p["r"]
                p["x"] = random.uniform(0, w)
            if not p["up"] and p["y"] > h + p["r"] + 4:
                p["y"] = -p["r"]
                p["x"] = random.uniform(0, w)
            if p["x"] < -p["r"]:
                p["x"] = w + p["r"]
            elif p["x"] > w + p["r"]:
                p["x"] = -p["r"]
            self.cv.coords(p["id"], p["x"] - p["r"], p["y"] - p["r"],
                           p["x"] + p["r"], p["y"] + p["r"])
        self.job = self.cv.after(33, self._loop)

    def stop(self):
        if self.job:
            try:
                self.cv.after_cancel(self.job)
            except Exception:
                pass
            self.job = None


# ------------------------------------------------------------------ экран
class ScreenCanvas(tk.Canvas):
    """Холст-экран: вертикальная раскладка блоков поверх живого фона.
    Анимация перехода: экран плавно «въезжает» справа (ease-out)."""

    PAD = 24

    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0)
        self._blocks = []          # [win_id, widget, anchor, gap, padx]
        self._spawned_layout = False
        self.bind("<Configure>", lambda e: self.after_idle(self.relayout), add="+")
        self.bind("<MouseWheel>", lambda e: self.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.bind("<Button-4>", lambda e: self.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.yview_scroll(1, "units"))
        Particles(self)

    # --- добавление блоков ---
    def add(self, widget, anchor="fill", gap=12, padx=None):
        padx = self.PAD if padx is None else padx
        wid = self.create_window(0, 0, window=widget, anchor="nw")
        self._blocks.append([wid, widget, anchor, gap, padx])
        self.after_idle(self.relayout)
        return widget

    def relayout(self):
        w = self.winfo_width()
        if w < 60:
            return
        y = 16
        for wid, widget, anchor, gap, padx in self._blocks:
            ww, wh = widget.winfo_reqwidth(), widget.winfo_reqheight()
            if anchor == "fill":
                self.itemconfigure(wid, width=w - 2 * padx, height=wh)
                self.coords(wid, padx, y)
            else:
                self.itemconfigure(wid, width=0, height=0)
                x = (w - ww) // 2 if anchor == "center" else padx
                self.coords(wid, max(padx, x), y)
            y += wh + gap
        self.configure(scrollregion=(0, 0, w, y))

    # --- анимация перехода (slide-in) ---
    def slide_in(self, dist=70, steps=9, ms=24):
        def step(i):
            t = i / steps
            e = 1 - (1 - t) ** 3              # ease-out cubic
            self.place_configure(x=int(dist * (1 - e)))
            if i < steps:
                self.after(ms, lambda: step(i + 1))
            else:
                self.place_configure(x=0)
        step(0)


# ------------------------------------------------------------------ индикатор
class ProgressArc(tk.Canvas):
    """Кольцевой прогресс с анимацией заполнения дуги (ease-out)."""

    def __init__(self, master, size=168, color=ACCENT, title="", bg=None):
        super().__init__(master, width=size + 20, height=size + 40,
                         highlightthickness=0, bg=bg or master["bg"])
        self.color = color
        pad = 16
        self.create_arc(pad, pad, size - pad, size - pad, start=90, extent=359.9,
                        style="arc", outline=PANEL_2, width=13)
        self.val = self.create_arc(pad, pad, size - pad, size - pad, start=90,
                                   extent=0.01, style="arc", outline=color, width=13)
        self.t_main = self.create_text(size // 2 + 2, size // 2 - 8, text="",
                                       fill=TEXT, font=("Segoe UI Semibold", 15))
        self.t_sub = self.create_text(size // 2 + 2, size // 2 + 16, text="",
                                      fill=MUTED, font=F_SMALL)
        self.t_title = self.create_text(size // 2 + 2, size + 16, text=title,
                                        fill=MUTED, font=F_TITLE)
        self._cur = 0.0
        self._job = None

    def set_value(self, frac, main, sub="", color=None, danger_over=False):
        """Анимированно привести дугу к значению frac (0..1)."""
        if color:
            self.itemconfigure(self.val, outline=color)
        elif danger_over:
            self.itemconfigure(self.val, outline=DANGER)
        frac = max(0.0, min(1.0, frac))
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        start, target, steps = self._cur, frac, 34
        i = 0

        def step():
            nonlocal i
            i += 1
            t = i / steps
            e = 1 - (1 - t) ** 3
            self._cur = start + (target - start) * e
            self.itemconfigure(self.val, extent=max(0.01, 360 * self._cur))
            if i < steps:
                self._job = self.after(22, step)
            else:
                self._cur = target
                self._job = None
        step()
        self.itemconfigure(self.t_main, text=main)
        self.itemconfigure(self.t_sub, text=sub)


# ------------------------------------------------------------------ таблица
class DataTable(tk.Frame):
    """Таблица ttk.Treeview с сортировкой кликом по заголовку столбца."""

    def __init__(self, master, columns, height=9, on_change=None, on_double=None):
        super().__init__(master, bg=PANEL)
        self.columns = columns            # (key, title, width, anchor)
        self.on_change = on_change
        self._rows = []
        self._sort_key = None
        self._desc = False
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns],
                                 show="headings", height=height, style="Diary.Treeview")
        for key, title, width, anchor in columns:
            self.tree.heading(key, text=title,
                              command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, anchor=anchor,
                             stretch=(anchor == "w"), minwidth=44)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview,
                            style="Diary.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        self.tree.tag_configure("odd", background=PANEL)
        self.tree.tag_configure("even", background="#16222b")
        if on_double:
            self.tree.bind("<Double-1>", on_double)

    def set_rows(self, rows):
        self._rows = list(rows)
        self._render()
        if self.on_change:
            self.after_idle(self.on_change)

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self._rows):
            vals = [self._fmt(r.get(k, "")) for k, _t, _w, _a in self.columns]
            self.tree.insert("", "end", iid=str(i),
                             values=vals,
                             tags=("even" if i % 2 else "odd",))

    @staticmethod
    def _fmt(v):
        if isinstance(v, float):
            s = f"{v:.1f}".rstrip("0").rstrip(".")
            return s if s else "0"
        return v

    def sort_by(self, key):
        """Фильтрация/сортировка: клик по заголовку — сортировка asc/desc."""
        if self._sort_key == key:
            self._desc = not self._desc
        else:
            self._sort_key, self._desc = key, False

        def sk(r):
            v = r.get(key, "")
            if isinstance(v, (int, float)):
                return (0, v, "")
            return (1, 0, str(v).lower())
        self._rows.sort(key=sk, reverse=self._desc)
        for k, title, *_ in self.columns:
            mark = ("  ▼" if self._desc else "  ▲") if k == self._sort_key else ""
            self.tree.heading(k, text=title + mark)
        self._render()

    def selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self._rows[int(sel[0])]


# ------------------------------------------------------------------ прочее
def card(master, title=None, color=None):
    """Карточка-панель с цветной полоской слева и (необязательным) заголовком."""
    f = tk.Frame(master, bg=PANEL)
    strip_color = color or ACCENT
    tk.Frame(f, bg=strip_color, width=4).pack(side="left", fill="y")
    inner = tk.Frame(f, bg=PANEL)
    inner.pack(side="left", fill="both", expand=True, padx=12, pady=9)
    if title:
        tk.Label(inner, text=title, bg=PANEL, fg=MUTED,
                 font=F_TITLE, anchor="w").pack(fill="x")
    return f, inner


def dark_entry(master, textvariable=None, width=24, show=None):
    e = tk.Entry(master, bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", width=width, textvariable=textvariable,
                 show=show, font=F_TEXT)
    return e


def dark_spin(master, textvariable=None, from_=0, to=100, increment=1, width=8):
    return tk.Spinbox(master, bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                      buttonbackground=PANEL_2, relief="flat", width=width,
                      from_=from_, to=to, increment=increment,
                      textvariable=textvariable, font=F_TEXT,
                      highlightthickness=1, highlightbackground=LINE)


def placeholder(entry, text):
    """Серая подсказка в поле ввода (сквозной поиск и фильтры)."""
    entry.insert(0, text)
    entry.configure(fg=MUTED)
    entry._ph = text

    def focus_in(_e):
        if entry.get() == entry._ph:
            entry.delete(0, "end")
            entry.configure(fg=TEXT)

    def focus_out(_e):
        if not entry.get():
            entry.insert(0, entry._ph)
            entry.configure(fg=MUTED)

    entry.bind("<FocusIn>", focus_in)
    entry.bind("<FocusOut>", focus_out)


def entry_value(entry):
    t = entry.get()
    return "" if getattr(entry, "_ph", None) == t else t


def label(master, text, **kw):
    kw.setdefault("bg", master["bg"])
    kw.setdefault("fg", TEXT)
    kw.setdefault("font", F_TEXT)
    kw.setdefault("anchor", "w")
    return tk.Label(master, text=text, **kw)
