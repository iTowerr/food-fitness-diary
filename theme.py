# -*- coding: utf-8 -*-
"""
theme.py — единая тема оформления: палитра, шрифты, данные автора.

ПАЛИТРА (аналоговая схема, colorscheme.ru):
  Тёмно-синий угольный фон (#10181D) — снижает нагрузку на глаза,
    приложение используется вечером после тренировок.
  Мятно-зелёный акцент (#37C978) — цвет здоровья, свежести и питания.
  Оранжевый акцент (#FF9F43) — цвет энергии и тренировок, контрастен зелёному.
  Тёплый красный (#E9575B) — только для ошибок и удаления.

ШРИФТОВАЯ ПАРА (подобрана по принципу fontjoy/mixfont):
  Заголовки — "Segoe UI Semibold" (гротеск, чёткая иерархия).
  Текст     — "Segoe UI" (максимальная читаемость на экране).
  Таблицы/цифры — "Consolas" (моноширинный, цифры не «прыгают»).
"""
import datetime

APP_TITLE   = "Дневник питания и тренировок"
APP_VERSION = "1.0"
AUTHOR_NAME  = "Дерябин Захар Олегович"
AUTHOR_GROUP = "22О"

# ----- палитра -----
BG       = "#10181D"   # фон окна
PANEL    = "#1A2730"   # панели/карточки
PANEL_2  = "#22333F"   # панели второго уровня, шапки таблиц
LINE     = "#2E4552"   # границы
ACCENT   = "#37C978"   # зелёный акцент (питание/успех)
ACCENT_D = "#27A55E"   # тёмно-зелёный (нажатие, выделение)
ACCENT2  = "#FF9F43"   # оранжевый акцент (тренировки)
DANGER   = "#E9575B"   # ошибки, удаление
TEXT     = "#EAF4EE"   # основной текст
MUTED    = "#8FA8A0"   # вторичный текст
ENTRY_BG = "#131E25"   # поля ввода

# ----- шрифты -----
F_HEADER = ("Segoe UI Semibold", 17)
F_TITLE  = ("Segoe UI Semibold", 12)
F_TEXT   = ("Segoe UI", 10)
F_SMALL  = ("Segoe UI", 9)
F_BTN    = ("Segoe UI Semibold", 10)
F_LOGO   = ("Segoe UI Black", 15)
F_MONO   = ("Consolas", 10)

RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
             "августа", "сентября", "октября", "ноября", "декабря"]
RU_DAYS   = ["понедельник", "вторник", "среда", "четверг",
             "пятница", "суббота", "воскресенье"]


def fmt_date(iso: str) -> str:
    """'2026-11-05' -> '05.11.2026, чт'"""
    try:
        d = datetime.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return str(iso)
    return d.strftime("%d.%m.%Y") + ", " + RU_DAYS[d.weekday()][:2]


def long_date(iso: str) -> str:
    try:
        d = datetime.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return str(iso)
    return f"{d.day} {RU_MONTHS[d.month - 1]} {d.year}, {RU_DAYS[d.weekday()]}"
