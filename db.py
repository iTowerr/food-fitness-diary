# -*- coding: utf-8 -*-
"""
db.py — база данных SQLite приложения «Дневник питания и тренировок».

СХЕМА (6 связанных таблиц, первичные и внешние ключи):

  users (id PK) ──< meals (id PK, user_id FK, product_id FK) >── products (id PK)
        │
        └──────< workouts (id PK, user_id FK, exercise_id FK) >── exercises (id PK)
        │
        └──────< action_log (id PK, user_id FK)

Расчёты:
  калории еды    = ккал/100 г × граммы / 100
  калории тренировки = MET × 3.5 × вес(кг) / 200 × минуты   (формула ACSM)
  нагрузка (баллы)   = MET × минуты / 10
  суточная норма     = вес × 33 ккал (упрощённая формула поддержки веса)
"""
import hashlib
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("food_diary.db")

MEAL_TYPES = ["Завтрак", "Обед", "Ужин", "Перекус"]

_conn: sqlite3.Connection | None = None


def hash_pw(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


# ------------------------------------------------------------------ схема
def init_db() -> None:
    c = get_conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name    TEXT NOT NULL,
        role         TEXT NOT NULL CHECK (role IN ('user','admin')),
        weight_kg    REAL NOT NULL DEFAULT 70,
        created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS products (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL UNIQUE,
        category     TEXT NOT NULL,
        kcal_per_100g REAL NOT NULL,
        protein      REAL NOT NULL DEFAULT 0,
        fat          REAL NOT NULL DEFAULT 0,
        carbs        REAL NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS exercises (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL UNIQUE,
        muscle_group TEXT NOT NULL,
        met          REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS meals (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
        meal_date  TEXT NOT NULL,
        meal_type  TEXT NOT NULL,
        grams      REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS workouts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        exercise_id  INTEGER NOT NULL REFERENCES exercises(id) ON DELETE RESTRICT,
        workout_date TEXT NOT NULL,
        duration_min REAL NOT NULL,
        avg_hr       INTEGER,
        notes        TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS action_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
        action     TEXT NOT NULL,
        details    TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );
    """)
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        _seed(c)
    c.commit()


# ------------------------------------------------------------- тестовые данные
def _seed(c: sqlite3.Connection) -> None:
    today = date.today()
    d = lambda off: (today - timedelta(days=off)).isoformat()

    users = [
        ("admin", "admin123", "Системный Администратор", "admin", 78),
        ("zahar", "user123",  "Дерябин Захар Олегович",  "user",  72),
        ("maria", "user123",  "Мария Петрова",           "user",  58),
        ("ivan",  "user123",  "Иван Смирнов",            "user",  84),
    ]
    uid = {}
    for u, p, f, r, w in users:
        cur = c.execute(
            "INSERT INTO users(username,password_hash,full_name,role,weight_kg)"
            " VALUES(?,?,?,?,?)", (u, hash_pw(p), f, r, w))
        uid[u] = cur.lastrowid

    products = [
        ("Овсяная каша на молоке", "Каши", 102, 3.2, 3.0, 15.5),
        ("Куриная грудка отварная", "Мясо и рыба", 165, 31.0, 3.6, 0),
        ("Гречка отварная", "Каши", 110, 4.2, 1.1, 21.3),
        ("Яблоко", "Фрукты", 52, 0.3, 0.2, 14.0),
        ("Банан", "Фрукты", 89, 1.1, 0.3, 23.0),
        ("Творог 5%", "Молочные продукты", 121, 17.0, 5.0, 1.8),
        ("Лосось запечённый", "Мясо и рыба", 208, 20.0, 13.0, 0),
        ("Омлет из 2 яиц", "Яйца", 154, 11.0, 11.0, 1.6),
        ("Рис белый отварной", "Каши", 130, 2.7, 0.3, 28.0),
        ("Греческий йогурт", "Молочные продукты", 59, 10.0, 0.4, 3.6),
        ("Овощной салат", "Овощи", 35, 1.2, 0.3, 6.6),
        ("Протеиновый батончик", "Снеки", 350, 30.0, 10.0, 33.0),
    ]
    pid = {}
    for name, cat, kcal, p, f, cb in products:
        cur = c.execute(
            "INSERT INTO products(name,category,kcal_per_100g,protein,fat,carbs)"
            " VALUES(?,?,?,?,?,?)", (name, cat, kcal, p, f, cb))
        pid[name] = cur.lastrowid

    exercises = [
        ("Бег 10 км/ч", "Кардио", 9.8),
        ("Быстрая ходьба", "Кардио", 4.3),
        ("Силовая тренировка (общая)", "Силовые", 5.0),
        ("Приседания со штангой", "Ноги", 6.0),
        ("Жим штанги лёжа", "Грудь", 6.0),
        ("Становая тяга", "Спина", 6.5),
        ("Плавание", "Кардио", 8.3),
        ("Велотренажёр", "Кардио", 7.0),
        ("Скакалка", "Кардио", 11.0),
        ("Йога", "Растяжка", 3.0),
        ("Отжимания", "Грудь", 8.0),
        ("Эллипсоид", "Кардио", 5.0),
    ]
    eid = {}
    for name, grp, met in exercises:
        cur = c.execute(
            "INSERT INTO exercises(name,muscle_group,met) VALUES(?,?,?)",
            (name, grp, met))
        eid[name] = cur.lastrowid

    meals = [  # (пользователь, продукт, сдвиг дня, тип, граммы)
        ("zahar", "Овсяная каша на молоке", 0, "Завтрак", 250),
        ("zahar", "Банан", 0, "Перекус", 120),
        ("zahar", "Куриная грудка отварная", 0, "Обед", 180),
        ("zahar", "Овощной салат", 0, "Обед", 150),
        ("zahar", "Творог 5%", 0, "Ужин", 200),
        ("zahar", "Омлет из 2 яиц", 1, "Завтрак", 160),
        ("zahar", "Гречка отварная", 1, "Обед", 200),
        ("zahar", "Лосось запечённый", 1, "Ужин", 150),
        ("zahar", "Греческий йогурт", 2, "Перекус", 130),
        ("zahar", "Рис белый отварной", 3, "Обед", 220),
        ("maria", "Греческий йогурт", 0, "Завтрак", 150),
        ("maria", "Яблоко", 0, "Перекус", 180),
        ("maria", "Овощной салат", 0, "Обед", 200),
        ("maria", "Творог 5%", 0, "Ужин", 150),
        ("maria", "Овсяная каша на молоке", 1, "Завтрак", 220),
        ("maria", "Банан", 1, "Перекус", 100),
        ("ivan", "Омлет из 2 яиц", 0, "Завтрак", 200),
        ("ivan", "Рис белый отварной", 0, "Обед", 250),
        ("ivan", "Куриная грудка отварная", 0, "Обед", 200),
        ("ivan", "Протеиновый батончик", 0, "Перекус", 60),
        ("ivan", "Гречка отварная", 2, "Обед", 250),
        ("ivan", "Лосось запечённый", 2, "Ужин", 180),
        ("admin", "Куриная грудка отварная", 0, "Обед", 150),
        ("admin", "Яблоко", 0, "Перекус", 150),
    ]
    for u, prod, off, mt, g in meals:
        c.execute(
            "INSERT INTO meals(user_id,product_id,meal_date,meal_type,grams)"
            " VALUES(?,?,?,?,?)", (uid[u], pid[prod], d(off), mt, g))

    workouts = [  # (пользователь, упражнение, сдвиг дня, минуты, пульс)
        ("zahar", "Бег 10 км/ч", 0, 40, 152),
        ("zahar", "Отжимания", 1, 15, 128),
        ("zahar", "Велотренажёр", 2, 45, 138),
        ("zahar", "Приседания со штангой", 4, 30, 140),
        ("zahar", "Скакалка", 6, 15, 160),
        ("maria", "Йога", 0, 60, 95),
        ("maria", "Быстрая ходьба", 1, 50, 110),
        ("maria", "Плавание", 3, 40, 125),
        ("maria", "Эллипсоид", 5, 35, 128),
        ("ivan", "Жим штанги лёжа", 0, 45, 130),
        ("ivan", "Становая тяга", 2, 40, 135),
        ("ivan", "Бег 10 км/ч", 3, 30, 150),
        ("ivan", "Силовая тренировка (общая)", 5, 60, 128),
        ("admin", "Быстрая ходьба", 1, 30, 105),
        ("admin", "Велотренажёр", 4, 40, 120),
    ]
    for u, ex, off, mins, hr in workouts:
        c.execute(
            "INSERT INTO workouts(user_id,exercise_id,workout_date,duration_min,avg_hr)"
            " VALUES(?,?,?,?,?)", (uid[u], eid[ex], d(off), mins, hr))

    logs = [
        ("admin", "Инициализация базы данных", "Созданы тестовые данные"),
        ("admin", "Добавлен пользователь", "maria"),
        ("admin", "Добавлен пользователь", "ivan"),
        ("zahar", "Добавлена запись питания", "Овсяная каша на молоке, 250 г"),
        ("zahar", "Добавлена тренировка", "Бег 10 км/ч, 40 мин"),
        ("maria", "Добавлена тренировка", "Йога, 60 мин"),
        ("ivan",  "Добавлена запись питания", "Куриная грудка отварная, 200 г"),
    ]
    for u, act, det in logs:
        c.execute("INSERT INTO action_log(user_id,action,details) VALUES(?,?,?)",
                  (uid[u], act, det))


# ------------------------------------------------------------------ журнал
def log(user_id, action: str, details: str = "") -> None:
    c = get_conn()
    c.execute("INSERT INTO action_log(user_id,action,details) VALUES(?,?,?)",
              (user_id, action, details))
    c.commit()


# ------------------------------------------------------------------ пользователи
def authenticate(username: str, password: str):
    row = get_conn().execute(
        "SELECT * FROM users WHERE lower(username)=lower(?) AND password_hash=?",
        (username.strip(), hash_pw(password))).fetchone()
    return dict(row) if row else None


def get_user(uid: int) -> dict:
    return dict(get_conn().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())


def all_users() -> list:
    return [dict(r) for r in get_conn().execute(
        "SELECT * FROM users ORDER BY id")]


def username_exists(username: str, except_id: int = None) -> bool:
    q = "SELECT COUNT(*) FROM users WHERE lower(username)=lower(?)"
    args = [username.strip()]
    if except_id:
        q += " AND id<>?"
        args.append(except_id)
    return get_conn().execute(q, args).fetchone()[0] > 0


def add_user(username, password, full_name, role, weight):
    c = get_conn()
    cur = c.execute(
        "INSERT INTO users(username,password_hash,full_name,role,weight_kg)"
        " VALUES(?,?,?,?,?)", (username.strip(), hash_pw(password),
                               full_name.strip(), role, weight))
    c.commit()
    return cur.lastrowid


def update_user(uid, username, full_name, role, weight, password=None):
    c = get_conn()
    if password:
        c.execute("UPDATE users SET username=?,full_name=?,role=?,weight_kg=?,"
                  "password_hash=? WHERE id=?",
                  (username.strip(), full_name.strip(), role, weight,
                   hash_pw(password), uid))
    else:
        c.execute("UPDATE users SET username=?,full_name=?,role=?,weight_kg=?"
                  " WHERE id=?", (username.strip(), full_name.strip(), role,
                                  weight, uid))
    c.commit()


def update_weight(uid, weight):
    c = get_conn()
    c.execute("UPDATE users SET weight_kg=? WHERE id=?", (weight, uid))
    c.commit()


def delete_user(uid):
    c = get_conn()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    c.commit()


# ------------------------------------------------------------------ справочники
def products_all() -> list:
    return [dict(r) for r in get_conn().execute(
        "SELECT * FROM products ORDER BY category, name")]


def product_add(name, category, kcal, p, f, cb) -> int:
    c = get_conn()
    cur = c.execute("INSERT INTO products(name,category,kcal_per_100g,protein,fat,carbs)"
                    " VALUES(?,?,?,?,?,?)", (name.strip(), category.strip(), kcal, p, f, cb))
    c.commit()
    return cur.lastrowid


def product_update(pid, name, category, kcal, p, f, cb):
    c = get_conn()
    c.execute("UPDATE products SET name=?,category=?,kcal_per_100g=?,protein=?,fat=?,carbs=?"
              " WHERE id=?", (name.strip(), category.strip(), kcal, p, f, cb, pid))
    c.commit()


def product_delete(pid):
    c = get_conn()
    c.execute("DELETE FROM products WHERE id=?", (pid,))
    c.commit()


def exercises_all() -> list:
    return [dict(r) for r in get_conn().execute(
        "SELECT * FROM exercises ORDER BY muscle_group, name")]


def exercise_add(name, group, met) -> int:
    c = get_conn()
    cur = c.execute("INSERT INTO exercises(name,muscle_group,met) VALUES(?,?,?)",
                    (name.strip(), group.strip(), met))
    c.commit()
    return cur.lastrowid


def exercise_update(eid, name, group, met):
    c = get_conn()
    c.execute("UPDATE exercises SET name=?,muscle_group=?,met=? WHERE id=?",
              (name.strip(), group.strip(), met, eid))
    c.commit()


def exercise_delete(eid):
    c = get_conn()
    c.execute("DELETE FROM exercises WHERE id=?", (eid,))
    c.commit()


# ------------------------------------------------------------------ записи
def meals_all(user_id=None) -> list:
    q = ("SELECT m.id, m.user_id, m.product_id, m.meal_date, m.meal_type, m.grams,"
         " p.name AS product, p.kcal_per_100g, p.protein, p.fat, p.carbs,"
         " u.full_name AS user "
         "FROM meals m JOIN products p ON p.id=m.product_id"
         " JOIN users u ON u.id=m.user_id")
    args = ()
    if user_id:
        q += " WHERE m.user_id=?"
        args = (user_id,)
    q += " ORDER BY m.meal_date DESC, m.id DESC"
    rows = []
    for r in get_conn().execute(q, args):
        d = dict(r)
        k = d["kcal_per_100g"] * d["grams"] / 100.0
        d["kcal"] = round(k, 1)
        d["prot"] = round(d["protein"] * d["grams"] / 100.0, 1)
        d["fat_g"] = round(d["fat"] * d["grams"] / 100.0, 1)
        d["carb"] = round(d["carbs"] * d["grams"] / 100.0, 1)
        rows.append(d)
    return rows


def meal_add(user_id, product_id, meal_date, meal_type, grams) -> int:
    c = get_conn()
    cur = c.execute("INSERT INTO meals(user_id,product_id,meal_date,meal_type,grams)"
                    " VALUES(?,?,?,?,?)", (user_id, product_id, meal_date, meal_type, grams))
    c.commit()
    return cur.lastrowid


def meal_update(mid, product_id, meal_date, meal_type, grams):
    c = get_conn()
    c.execute("UPDATE meals SET product_id=?,meal_date=?,meal_type=?,grams=? WHERE id=?",
              (product_id, meal_date, meal_type, grams, mid))
    c.commit()


def meal_delete(mid):
    c = get_conn()
    c.execute("DELETE FROM meals WHERE id=?", (mid,))
    c.commit()


def workouts_all(user_id=None) -> list:
    q = ("SELECT w.id, w.user_id, w.exercise_id, w.workout_date, w.duration_min,"
         " w.avg_hr, w.notes, e.name AS exercise, e.muscle_group, e.met,"
         " u.full_name AS user, u.weight_kg "
         "FROM workouts w JOIN exercises e ON e.id=w.exercise_id"
         " JOIN users u ON u.id=w.user_id")
    args = ()
    if user_id:
        q += " WHERE w.user_id=?"
        args = (user_id,)
    q += " ORDER BY w.workout_date DESC, w.id DESC"
    rows = []
    for r in get_conn().execute(q, args):
        d = dict(r)
        d["kcal"] = round(d["met"] * 3.5 * d["weight_kg"] / 200.0 * d["duration_min"], 1)
        d["load"] = round(d["met"] * d["duration_min"] / 10.0, 1)
        rows.append(d)
    return rows


def workout_add(user_id, exercise_id, workout_date, minutes, hr, notes="") -> int:
    c = get_conn()
    cur = c.execute("INSERT INTO workouts(user_id,exercise_id,workout_date,duration_min,avg_hr,notes)"
                    " VALUES(?,?,?,?,?,?)",
                    (user_id, exercise_id, workout_date, minutes, hr, notes))
    c.commit()
    return cur.lastrowid


def workout_update(wid, exercise_id, workout_date, minutes, hr, notes=""):
    c = get_conn()
    c.execute("UPDATE workouts SET exercise_id=?,workout_date=?,duration_min=?,avg_hr=?,notes=?"
              " WHERE id=?", (exercise_id, workout_date, minutes, hr, notes, wid))
    c.commit()


def workout_delete(wid):
    c = get_conn()
    c.execute("DELETE FROM workouts WHERE id=?", (wid,))
    c.commit()


# ------------------------------------------------------------------ журнал действий
def log_all() -> list:
    return [dict(r) for r in get_conn().execute(
        "SELECT l.id, l.created_at, l.action, l.details,"
        " COALESCE(u.username,'—') AS user"
        " FROM action_log l LEFT JOIN users u ON u.id=l.user_id"
        " ORDER BY l.created_at DESC, l.id DESC")]


# ------------------------------------------------------------------ статистика
def counts() -> dict:
    c = get_conn()
    out = {}
    for t in ("users", "products", "exercises", "meals", "workouts", "action_log"):
        out[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return out


def fk_check() -> list:
    return [dict(r) for r in get_conn().execute("PRAGMA foreign_key_check")]


if __name__ == "__main__":
    init_db()
    print("БД готова:", DB_PATH)
    print("Записей в таблицах:", counts())
    print("Проверка внешних ключей (пусто = всё связно):", fk_check())
