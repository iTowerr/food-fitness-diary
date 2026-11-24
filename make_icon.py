# -*- coding: utf-8 -*-
"""
make_icon.py — генерация иконки приложения (тарелка с листом + гантель).
Запуск: python make_icon.py
"""
from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

GREEN  = (55, 201, 120, 255)
ORANGE = (255, 159, 67, 255)
DARK   = (16, 24, 29, 255)
PANEL  = (26, 39, 48, 255)

# фон — тёмный скруглённый квадрат с зелёной окантовкой
d.rounded_rectangle([6, 6, S - 6, S - 6], radius=58, fill=DARK, outline=GREEN, width=7)

# тарелка (питание)
cx, cy = 118, 108
d.ellipse([cx - 78, cy - 78, cx + 78, cy + 78], fill=PANEL, outline=GREEN, width=9)
d.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], outline=GREEN, width=5)
# листик на тарелке — здоровое питание
d.ellipse([cx - 26, cy - 30, cx + 20, cy + 18], fill=GREEN)
d.line([cx - 20, cy + 22, cx + 26, cy - 24], fill=DARK, width=6)

# гантель (тренировки) — снизу
d.rounded_rectangle([96, 196, 208, 212], radius=8, fill=ORANGE)
d.rounded_rectangle([76, 172, 104, 236], radius=9, fill=ORANGE)
d.rounded_rectangle([200, 172, 228, 236], radius=9, fill=ORANGE)

img.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save("icon.png")
print("Иконка сохранена: icon.ico, icon.png")
