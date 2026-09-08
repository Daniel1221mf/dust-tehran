# -*- coding: utf-8 -*-
"""
Tehran: Shadows of the Realm - Android edition
Rewritten from the original pygame version using Kivy so it can be
packaged into an .apk with buildozer.

Controls (touch):
  - Drag on the bottom-left circle  -> move
  - Tap/hold anywhere else on the map -> aim & shoot toward that point
  - Buttons on the right            -> Horse / Deliver / Talk / Crack / Pay / Map
  - During the safe-cracking minigame -> tap the dial when the needle lines up
  - Android Back button             -> closes map/minigame, otherwise exits
"""

import math
import random

from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Ellipse, Line, Triangle

random.seed(42)


def C(r, g, b, a=1.0):
    """Convert 0-255 RGB(+alpha 0-1) into Kivy's 0-1 color tuple."""
    return (r / 255.0, g / 255.0, b / 255.0, a)


# ----------------------------------------------------------------------
# Small self-contained replacements for pygame.Vector2 / pygame.Rect
# ----------------------------------------------------------------------
class Vec2:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, o):
        return Vec2(self.x + o.x, self.y + o.y)

    def __sub__(self, o):
        return Vec2(self.x - o.x, self.y - o.y)

    def __mul__(self, s):
        return Vec2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def length(self):
        return math.hypot(self.x, self.y)

    def length_squared(self):
        return self.x * self.x + self.y * self.y

    def normalize(self):
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l else Vec2(0, 0)

    def distance_to(self, o):
        return math.hypot(self.x - o.x, self.y - o.y)


V = Vec2


class Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    def inflate(self, dx, dy):
        return Rect(self.x - dx / 2, self.y - dy / 2, self.w + dx, self.h + dy)

    def collidepoint(self, x, y):
        return self.x <= x <= self.right and self.y <= y <= self.bottom

    def colliderect(self, o):
        return not (
            self.right < o.x or o.right < self.x or self.bottom < o.y or o.bottom < self.y
        )


# ----------------------------------------------------------------------
# World data (same layout as the original pygame version)
# ----------------------------------------------------------------------
WORLD_W, WORLD_H = 3800, 2800

places = [
    ("Grand Bazaar", V(500, 2100)),
    ("Toopkhaneh Square", V(1350, 1400)),
    ("Golestan Citadel", V(1900, 2050)),
    ("Caravanserai Shah Abbasi", V(2950, 1850)),
    ("Shemiran Foothills", V(3100, 520)),
    ("Darvazeh Doulab", V(750, 750)),
]

post_offices = [
    ("Central Telegraph (Toopkhaneh)", V(1450, 1320)),
    ("Bazaar Post Office", V(620, 2020)),
    ("Northern Outpost Telegraph", V(2800, 650)),
]

roads = [
    Rect(0, 700, WORLD_W, 130),
    Rect(0, 1400, WORLD_W, 150),
    Rect(0, 2100, WORLD_W, 140),
    Rect(650, 0, 140, WORLD_H),
    Rect(1850, 0, 150, WORLD_H),
    Rect(2950, 0, 130, WORLD_H),
]

building_types = [
    {"wall": (185, 145, 105), "roof": (155, 115, 80), "deco": "dome"},
    {"wall": (175, 160, 135), "roof": (68, 140, 150), "deco": "blue_dome"},
    {"wall": (195, 135, 95), "roof": (140, 95, 65), "deco": "windcatcher"},
    {"wall": (210, 180, 140), "roof": (170, 130, 90), "deco": "plain"},
]

buildings = []
for _ in range(320):
    bw, bh = random.randrange(70, 160), random.randrange(60, 130)
    bx = random.randrange(80, WORLD_W - 200)
    by = random.randrange(120, WORLD_H - 180)
    rect = Rect(bx, by, bw, bh)
    near_poi = any(
        rect.inflate(170, 170).collidepoint(p[1].x, p[1].y) for p in places + post_offices
    )
    near_road = any(rect.inflate(40, 40).colliderect(r) for r in roads)
    if not near_poi and not near_road:
        b_type = random.choice(building_types)
        buildings.append({"rect": rect, "type": b_type})

safes = [
    {"pos": V(520, 2040), "looted": False, "code": random.randint(30, 330)},
    {"pos": V(1950, 2000), "looted": False, "code": random.randint(30, 330)},
    {"pos": V(3000, 1800), "looted": False, "code": random.randint(30, 330)},
    {"pos": V(3120, 600), "looted": False, "code": random.randint(30, 330)},
]

dialogue_pool = [
    "Beware of the desert raiders past the north gate!",
    "The Shah's telegraph line reaches Tabriz now.",
    "Did you hear the gunshots near the bazaar last night?",
    "Water is scarce; the qanat needs cleaning.",
    "The gendarmes will shoot on sight if your bounty stays high!",
    "Fine silks arrived today from Isfahan!",
    "Pay your dues at the telegraph post if the law hunts you.",
]

npcs = []
for _ in range(45):
    pos = V(random.randint(200, WORLD_W - 200), random.randint(200, WORLD_H - 200))
    npcs.append(
        {
            "pos": pos,
            "vel": V(random.choice([-1, 0, 1]), random.choice([-1, 0, 1])) * 35,
            "dialogue": random.choice(dialogue_pool),
            "timer": random.uniform(2, 6),
            "turban": random.choice([(230, 230, 230), (50, 100, 70), (140, 70, 40)]),
        }
    )

BUTTON_DEFS = [
    ("horse", "Horse"),
    ("deliver", "Deliver"),
    ("talk", "Talk"),
    ("crack", "Crack"),
    ("pay", "Pay"),
    ("map", "Map"),
]


class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.player = V(520, 2080)
        self.camera = V(0, 0)
        self.horse = False
        self.gallop_cycle = 0.0
        self.health = 100.0
        self.money = 120
        self.wanted = 0.0
        self.cooldown = 0.0
        self.spawn_timer = 0.0
        self.target = 0
        self.missions_completed = 0
        self.guards = []
        self.bullets = []
        self.active_dialogue = ""
        self.active_dialogue_time = 0.0
        self.message = "Welcome to Tehran. Deliver cargo, avoid the gendarmerie, or clear your bounty."
        self.message_time = 7.0
        self.show_full_map = False
        self.minigame_active = False
        self.active_safe = None
        self.lock_angle = 0.0
        self.lock_sweet_spot = 0.0
        self.lock_progress = 0.0
        self.aim = V(1, 0)

        # touch/joystick state
        self.joy_touch = None
        self.joy_center = V(130, 150)
        self.joy_radius = 80
        self.joy_vec = V(0, 0)
        self.fire_touch = None
        self.fire_pos = None
        self.firing = False

        # persistent label widgets (repositioned every frame)
        self.lbl_title = self._mk_label()
        self.lbl_stats = self._mk_label()
        self.lbl_target = self._mk_label()
        self.lbl_hint = self._mk_label()
        self.lbl_message = self._mk_label()
        self.lbl_dialogue = self._mk_label()
        self.lbl_prompt1 = self._mk_label()
        self.lbl_prompt2 = self._mk_label()
        self.lbl_map_title = self._mk_label()
        self.lbl_map_close = self._mk_label()
        self.lbl_you = self._mk_label()
        self.lbl_minigame_title = self._mk_label()
        self.lbl_minigame_hint = self._mk_label()

        self.poi_labels = [self._mk_label() for _ in places]
        self.post_labels = [self._mk_label() for _ in post_offices]
        self.map_place_labels = [self._mk_label() for _ in places]
        self.map_post_labels = [self._mk_label() for _ in post_offices]
        self.button_labels = {key: self._mk_label() for key, _ in BUTTON_DEFS}

        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_interval(self.update, 1.0 / 60.0)

    def _mk_label(self):
        lbl = Label(size_hint=(None, None), halign="left", valign="middle")
        self.add_widget(lbl)
        return lbl

    def set_label(self, lbl, text, x, y_down, color=(1, 1, 1, 1), font_size="13sp",
                  bold=False, height=20, width=None):
        lbl.text = text
        lbl.color = color
        lbl.font_size = font_size
        lbl.bold = bold
        w = width if width is not None else max(len(text) * 8, 10)
        lbl.text_size = (w, height)
        lbl.size = (w, height)
        lbl.pos = (x, self.height - y_down - height)
        lbl.opacity = 1 if text else 0

    def hide_label(self, lbl):
        lbl.opacity = 0

    # ------------------------------------------------------------------
    # physics helpers
    # ------------------------------------------------------------------
    def is_blocked(self, pos, radius=14):
        if not (radius < pos.x < WORLD_W - radius and radius < pos.y < WORLD_H - radius):
            return True
        return any(
            b["rect"].inflate(radius * 2, radius * 2).collidepoint(pos.x, pos.y)
            for b in buildings
        )

    def move_entity(self, pos, motion, radius=14):
        nx = V(pos.x + motion.x, pos.y)
        if not self.is_blocked(nx, radius):
            pos.x = nx.x
        ny = V(pos.x, pos.y + motion.y)
        if not self.is_blocked(ny, radius):
            pos.y = ny.y

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def get_buttons(self):
        bw, bh = 92, 56
        margin = 10
        x = self.width - bw - margin
        result = []
        for i, (key, label) in enumerate(BUTTON_DEFS):
            y = self.height - margin - (bh + margin) * (i + 1)
            result.append((key, label, x, y, bw, bh))
        return result

    def button_active(self, key):
        if key in ("horse", "map"):
            return True
        if key == "deliver":
            return self.player.distance_to(places[self.target][1]) < 90
        if key == "talk":
            closest = min(npcs, key=lambda n: self.player.distance_to(n["pos"]))
            return self.player.distance_to(closest["pos"]) < 90
        if key == "crack":
            return any(
                not s["looted"] and self.player.distance_to(s["pos"]) < 60 for s in safes
            )
        if key == "pay":
            return any(self.player.distance_to(p[1]) < 90 for p in post_offices)
        return False

    def handle_action(self, key):
        if key == "horse":
            self.horse = not self.horse

        elif key == "deliver":
            p_dest = places[self.target][1]
            if self.player.distance_to(p_dest) < 90:
                reward = 55 + self.missions_completed * 5
                self.money += reward
                self.missions_completed += 1
                self.target = (self.target + 1) % len(places)
                self.message = f"Mission done! +${reward}. Deliver dispatch to {places[self.target][0]}."
                self.message_time = 6.0
            else:
                self.message = "You must be at the destination to deliver."
                self.message_time = 2.5

        elif key == "talk":
            closest = min(npcs, key=lambda n: self.player.distance_to(n["pos"]))
            if self.player.distance_to(closest["pos"]) < 90:
                self.active_dialogue = closest["dialogue"]
                self.active_dialogue_time = 5.5
            else:
                self.message = "No one is close enough to talk to."
                self.message_time = 2.5

        elif key == "crack":
            found = False
            for safe in safes:
                if not safe["looted"] and self.player.distance_to(safe["pos"]) < 60:
                    self.minigame_active = True
                    self.active_safe = safe
                    self.lock_sweet_spot = safe["code"]
                    self.lock_angle = 0
                    self.lock_progress = 0
                    found = True
                    break
            if not found:
                self.message = "No safe nearby."
                self.message_time = 2.5

        elif key == "pay":
            near_post = any(self.player.distance_to(p[1]) < 90 for p in post_offices)
            if near_post:
                bounty_cost = int(self.wanted * 40)
                if bounty_cost <= 0:
                    self.message = "Your name is clear with the authorities."
                    self.message_time = 4.0
                elif self.money >= bounty_cost:
                    self.money -= bounty_cost
                    self.wanted = 0.0
                    self.guards.clear()
                    self.message = f"Bounty paid (${bounty_cost})! You are a free citizen."
                    self.message_time = 5.0
                else:
                    self.message = f"Not enough cash! Need ${bounty_cost}."
                    self.message_time = 5.0
            else:
                self.message = "No telegraph post nearby."
                self.message_time = 2.5

        elif key == "map":
            self.show_full_map = not self.show_full_map

    def tap_lock(self):
        diff = abs((self.lock_angle % 360) - self.lock_sweet_spot)
        if diff < 18 or diff > 342:
            self.lock_progress += 38
            if self.lock_progress >= 100:
                payout = random.randint(65, 140)
                self.money += payout
                self.active_safe["looted"] = True
                self.minigame_active = False
                self.message = f"Safe cracked! Plundered ${payout}."
                self.message_time = 5.0
        else:
            self.lock_progress = max(0, self.lock_progress - 20)
            self.wanted = min(5.0, self.wanted + 0.8)
            self.message = "Lockpick slipped! Guards alerted!"
            self.message_time = 4.0

    def on_key(self, window, key, *args):
        if key == 27:  # Android back button / Esc
            if self.minigame_active:
                self.minigame_active = False
                return True
            if self.show_full_map:
                self.show_full_map = False
                return True
            return False
        return False

    def _update_joy(self, tx, ty):
        dx = tx - self.joy_center.x
        dy = ty - self.joy_center.y
        dist = math.hypot(dx, dy)
        if dist > self.joy_radius:
            dx *= self.joy_radius / dist
            dy *= self.joy_radius / dist
        self.joy_vec = V(dx / self.joy_radius, -dy / self.joy_radius)

    def on_touch_down(self, touch):
        tx, ty = touch.x, touch.y

        if self.minigame_active:
            if self.width - 80 <= tx <= self.width - 20 and self.height - 80 <= ty <= self.height - 20:
                self.minigame_active = False
                return True
            cx, cy = self.width / 2.0, self.height / 2.0
            if math.hypot(tx - cx, ty - cy) <= 140:
                self.tap_lock()
            return True

        if self.show_full_map:
            if self.width - 100 <= tx <= self.width - 20 and self.height - 70 <= ty <= self.height - 20:
                self.show_full_map = False
            return True

        for key, label, bx, by, bw, bh in self.get_buttons():
            if bx <= tx <= bx + bw and by <= ty <= by + bh:
                self.handle_action(key)
                return True

        if tx < self.width * 0.45 and ty < self.height * 0.6:
            self.joy_touch = touch.uid
            self._update_joy(tx, ty)
            return True

        self.fire_touch = touch.uid
        self.fire_pos = (tx, ty)
        self.firing = True
        return True

    def on_touch_move(self, touch):
        if touch.uid == self.joy_touch:
            self._update_joy(touch.x, touch.y)
        elif touch.uid == self.fire_touch:
            self.fire_pos = (touch.x, touch.y)

    def on_touch_up(self, touch):
        if touch.uid == self.joy_touch:
            self.joy_touch = None
            self.joy_vec = V(0, 0)
        elif touch.uid == self.fire_touch:
            self.fire_touch = None
            self.firing = False
            self.fire_pos = None

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def update(self, dt):
        dt = min(dt, 0.04)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.message_time = max(0.0, self.message_time - dt)
        self.active_dialogue_time = max(0.0, self.active_dialogue_time - dt)
        self.wanted = max(0.0, self.wanted - dt * 0.02)

        if self.minigame_active:
            self.lock_angle = (self.lock_angle + 120 * dt) % 360
        else:
            move_dir = V(self.joy_vec.x, self.joy_vec.y)
            speed = 290 if self.horse else 145
            if move_dir.length_squared() > 0.0001:
                if move_dir.length() > 1:
                    move_dir = move_dir.normalize()
                self.move_entity(self.player, move_dir * speed * dt)
                if self.horse:
                    self.gallop_cycle += dt * 14

            self.camera.x = max(0, min(WORLD_W - self.width, self.player.x - self.width / 2))
            self.camera.y = max(0, min(WORLD_H - self.height, self.player.y - self.height / 2))

            if self.firing and self.fire_pos:
                player_screen = V(self.player.x - self.camera.x, self.player.y - self.camera.y)
                touch_screen = V(self.fire_pos[0], self.height - self.fire_pos[1])
                diff = touch_screen - player_screen
                if diff.length_squared() > 4:
                    self.aim = diff.normalize()

            if self.firing and self.cooldown <= 0:
                self.bullets.append([V(self.player.x, self.player.y) + self.aim * 24, self.aim * 720, 1.3])
                self.cooldown = 0.24
                self.wanted = min(5.0, self.wanted + 0.5)

            self.spawn_timer -= dt
            if self.wanted >= 0.8 and self.spawn_timer <= 0 and len(self.guards) < 10:
                for _ in range(25):
                    angle = random.uniform(0, math.tau)
                    spot = V(self.player.x + math.cos(angle) * 520, self.player.y + math.sin(angle) * 520)
                    if not self.is_blocked(spot):
                        self.guards.append({"pos": spot, "hp": 40})
                        break
                self.spawn_timer = max(0.9, 3.2 - self.wanted * 0.4)

            if self.wanted <= 0:
                self.guards.clear()

            for g in self.guards[:]:
                to_p = self.player - g["pos"]
                dist = to_p.length()
                if dist > 0:
                    self.move_entity(g["pos"], to_p.normalize() * (110 + self.wanted * 12) * dt)
                if dist < 28:
                    self.health -= 22 * dt

            for b in self.bullets[:]:
                b[0] = b[0] + b[1] * dt
                b[2] -= dt
                if self.is_blocked(b[0], 3) or b[2] <= 0:
                    self.bullets.remove(b)
                    continue
                for g in self.guards[:]:
                    if g["pos"].distance_to(b[0]) < 18:
                        g["hp"] -= 25
                        if g["hp"] <= 0:
                            self.guards.remove(g)
                            self.money += 15
                            self.wanted = min(5.0, self.wanted + 0.3)
                        if b in self.bullets:
                            self.bullets.remove(b)
                        break

            for n in npcs:
                n["timer"] -= dt
                if n["timer"] <= 0:
                    n["timer"] = random.uniform(2, 5)
                    n["vel"] = V(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * random.uniform(20, 45)
                self.move_entity(n["pos"], n["vel"] * dt, 10)

            if self.wanted == 0:
                self.health = min(100.0, self.health + 5 * dt)

            if self.health <= 0:
                self.player = V(520, 2080)
                self.health = 100.0
                self.money = max(0, self.money - 40)
                self.wanted = 0.0
                self.guards.clear()
                self.bullets.clear()
                self.horse = False
                self.message = "Hospitalized! The gendarmes confiscated $40 in penalties."
                self.message_time = 6.0

        self.redraw()

    # ------------------------------------------------------------------
    # drawing helpers (world-space, y-down like the original pygame code)
    # ------------------------------------------------------------------
    def w2s(self, pos):
        return pos.x - self.camera.x, pos.y - self.camera.y

    def rect_screen(self, sx, sy, w, h, rgba, line=False, width=2):
        Color(*rgba)
        if line:
            Line(rectangle=(sx, self.height - sy - h, w, h), width=width)
        else:
            Rectangle(pos=(sx, self.height - sy - h), size=(w, h))

    def circle_screen(self, sx, sy, r, rgba):
        Color(*rgba)
        Ellipse(pos=(sx - r, self.height - sy - r), size=(r * 2, r * 2))

    def circle_outline_screen(self, sx, sy, r, rgba, width=2):
        Color(*rgba)
        Line(circle=(sx, self.height - sy, r), width=width)

    def ellipse_screen(self, sx, sy, w, h, rgba):
        Color(*rgba)
        Ellipse(pos=(sx, self.height - sy - h), size=(w, h))

    def line_screen(self, x1, y1, x2, y2, rgba, width=2):
        Color(*rgba)
        Line(points=[x1, self.height - y1, x2, self.height - y2], width=width)

    # plain UI-space helpers (already in Kivy's own coordinate system)
    def ui_circle(self, cx, cy, r, rgba, outline=False, width=2):
        Color(*rgba)
        if outline:
            Line(circle=(cx, cy, r), width=width)
        else:
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

    def ui_rect(self, x, y, w, h, rgba, outline=False, width=2):
        Color(*rgba)
        if outline:
            Line(rectangle=(x, y, w, h), width=width)
        else:
            Rectangle(pos=(x, y), size=(w, h))

    def ui_line(self, x1, y1, x2, y2, rgba, width=2):
        Color(*rgba)
        Line(points=[x1, y1, x2, y2], width=width)

    # ------------------------------------------------------------------
    # render
    # ------------------------------------------------------------------
    def redraw(self):
        W, H = self.width, self.height
        if W <= 0 or H <= 0:
            return
        self.canvas.clear()

        overlay_active = self.minigame_active or self.show_full_map

        with self.canvas:
            Color(*C(210, 186, 138))
            Rectangle(pos=(0, 0), size=(W, H))

            for r in roads:
                sx, sy = r.x - self.camera.x, r.y - self.camera.y
                self.rect_screen(sx, sy, r.w, r.h, C(168, 147, 116))
                self.rect_screen(sx, sy, r.w, r.h, C(140, 120, 92), line=True, width=2)

            for x in range(-50, WORLD_W + 300, 170):
                wx = x - self.camera.x
                p1 = (wx, 150 - self.camera.y)
                p2 = (wx + 95, -50 - self.camera.y)
                p3 = (wx + 190, 150 - self.camera.y)
                k1 = (p1[0], H - p1[1])
                k2 = (p2[0], H - p2[1])
                k3 = (p3[0], H - p3[1])
                Color(*C(115, 122, 122))
                Triangle(points=[k1[0], k1[1], k2[0], k2[1], k3[0], k3[1]])
                Color(*C(220, 225, 230))
                Triangle(points=[k2[0], k2[1], k2[0] - 25, k2[1] - 45, k2[0] + 25, k2[1] - 45])

            vbox = Rect(self.camera.x, self.camera.y, W, H)
            for b in buildings:
                r = b["rect"]
                if not vbox.colliderect(r.inflate(30, 30)):
                    continue
                sx, sy = r.x - self.camera.x, r.y - self.camera.y
                self.rect_screen(sx + 9, sy + 10, r.w, r.h, C(135, 115, 88))
                self.rect_screen(sx, sy, r.w, r.h, C(*b["type"]["wall"]))
                self.rect_screen(sx, sy, r.w, r.h, C(100, 80, 58), line=True, width=2)
                deco = b["type"]["deco"]
                cx, cy = sx + r.w / 2, sy + r.h / 2
                if deco == "blue_dome":
                    self.circle_screen(cx, cy, min(r.w, r.h) // 3, C(46, 148, 160))
                    self.circle_screen(cx, cy, 4, C(230, 210, 120))
                elif deco == "dome":
                    self.circle_screen(cx, cy, min(r.w, r.h) // 3, C(*b["type"]["roof"]))
                    self.circle_outline_screen(cx, cy, min(r.w, r.h) // 3, C(110, 80, 50), width=2)
                elif deco == "windcatcher":
                    wcx, wcy = sx + 8, sy + 8
                    self.rect_screen(wcx, wcy, 22, 16, C(120, 90, 60))
                    self.line_screen(wcx + 7, wcy, wcx + 7, wcy + 16, C(40, 30, 20), width=2)
                    self.line_screen(wcx + 14, wcy, wcx + 14, wcy + 16, C(40, 30, 20), width=2)

            for safe in safes:
                sx, sy = self.w2s(safe["pos"])
                col = C(130, 130, 130) if not safe["looted"] else C(75, 75, 75)
                self.rect_screen(sx - 10, sy - 10, 20, 20, col)
                self.circle_screen(sx, sy, 4, C(220, 180, 50))

            for name, pos in post_offices:
                sx, sy = self.w2s(pos)
                self.rect_screen(sx - 22, sy - 22, 44, 44, C(40, 75, 120))
                self.rect_screen(sx - 22, sy - 22, 44, 44, C(240, 200, 60), line=True, width=3)

            for idx, (name, pos) in enumerate(places):
                sx, sy = self.w2s(pos)
                is_dest = idx == self.target
                col = C(255, 200, 40) if is_dest else C(90, 170, 150)
                self.circle_outline_screen(sx, sy, 32, col, width=3)
                self.circle_screen(sx, sy, 6, col)

            for n in npcs:
                sx, sy = self.w2s(n["pos"])
                self.circle_screen(sx + 2, sy + 3, 9, C(90, 80, 70))
                self.circle_screen(sx, sy, 8, C(60, 95, 110))
                self.circle_screen(sx, sy - 2, 6, C(*n["turban"]))

            for g in self.guards:
                sx, sy = self.w2s(g["pos"])
                to_pl = self.player - g["pos"]
                to_pl = to_pl.normalize() if to_pl.length_squared() else V(1, 0)
                self.ellipse_screen(sx - 11, sy - 6, 22, 14, C(50, 40, 30))
                self.circle_screen(sx, sy, 12, C(32, 54, 85))
                self.circle_screen(sx, sy - 4, 7, C(220, 180, 130))
                self.circle_screen(sx, sy - 8, 3, C(190, 40, 40))
                gx, gy = sx + to_pl.x * 14, sy + to_pl.y * 14
                self.line_screen(sx, sy, gx, gy, C(25, 25, 25), width=3)

            for b in self.bullets:
                sx, sy = self.w2s(b[0])
                self.circle_screen(sx, sy, 3, C(255, 240, 130))

            psx, psy = self.w2s(self.player)
            if self.horse:
                bounce = math.sin(self.gallop_cycle) * 3
                h_dir = self.aim
                side = V(-h_dir.y, h_dir.x)
                tail = V(psx - h_dir.x * 22, psy - h_dir.y * 22)
                head = V(psx + h_dir.x * 24, psy + h_dir.y * 24 + bounce)
                self.ellipse_screen(psx - 14, psy - 16, 28, 34, C(85, 45, 22))
                self.circle_screen(head.x, head.y, 10, C(100, 55, 28))
                self.circle_screen(head.x + side.x * 5, head.y + side.y * 5, 3, C(60, 30, 15))
                self.circle_screen(head.x - side.x * 5, head.y - side.y * 5, 3, C(60, 30, 15))
                self.line_screen(psx, psy, tail.x, tail.y, C(40, 20, 10), width=5)
                self.rect_screen(psx - 9, psy - 8, 18, 16, C(145, 95, 55))

            self.circle_screen(psx, psy, 12, C(40, 70, 75))
            self.circle_screen(psx, psy - 2, 7, C(230, 195, 150))
            self.circle_screen(psx, psy - 4, 6, C(30, 30, 30))
            gun_hand = V(psx + self.aim.x * 18, psy + self.aim.y * 18)
            self.line_screen(psx, psy, gun_hand.x, gun_hand.y, C(35, 30, 25), width=4)
            self.circle_screen(gun_hand.x, gun_hand.y, 3, C(180, 140, 60))

            # HUD
            self.rect_screen(0, 0, W, 85, C(26, 28, 30))
            self.line_screen(0, 85, W, 85, C(215, 175, 90), width=2)
            if self.message_time > 0:
                self.rect_screen(16, 95, W - 250, 32, C(40, 36, 30))
                self.rect_screen(16, 95, W - 250, 32, C(220, 180, 90), line=True, width=1)
            if self.active_dialogue_time > 0:
                self.rect_screen(16, 135, W - 250, 32, C(25, 38, 48))

            t_dir = places[self.target][1] - self.player
            if t_dir.length_squared():
                arr = t_dir.normalize()
                c_pt = V(W - 60, 42)
                tip = c_pt + arr * 24
                s_vec = V(-arr.y, arr.x)
                p1, p2, p3 = tip, c_pt - arr * 10 + s_vec * 9, c_pt - arr * 10 - s_vec * 9
                Color(*C(255, 205, 50))
                Triangle(points=[p1.x, H - p1.y, p2.x, H - p2.y, p3.x, H - p3.y])

            self.rect_screen(0, H - 32, W, 32, C(22, 24, 25))

            radar_size = 150
            rx = W - radar_size - 18
            ry = H - radar_size - 44
            self.rect_screen(rx, ry, radar_size, radar_size, C(28, 30, 32))
            self.rect_screen(rx, ry, radar_size, radar_size, C(180, 150, 90), line=True, width=2)
            scale_x, scale_y = radar_size / WORLD_W, radar_size / WORLD_H
            self.circle_screen(rx + self.player.x * scale_x, ry + self.player.y * scale_y, 3, C(255, 255, 255))
            self.circle_screen(rx + places[self.target][1].x * scale_x, ry + places[self.target][1].y * scale_y, 3, C(255, 210, 40))
            for _, po in post_offices:
                self.rect_screen(rx + po.x * scale_x - 2, ry + po.y * scale_y - 2, 4, 4, C(80, 160, 255))
            for g in self.guards:
                self.circle_screen(rx + g["pos"].x * scale_x, ry + g["pos"].y * scale_y, 2, C(255, 60, 60))

            if not overlay_active:
                # virtual joystick
                jx, jy = self.joy_center.x, self.joy_center.y
                self.ui_circle(jx, jy, self.joy_radius, (1, 1, 1, 0.18), outline=True, width=2)
                thumb = V(jx + self.joy_vec.x * self.joy_radius, jy - self.joy_vec.y * self.joy_radius)
                self.ui_circle(thumb.x, thumb.y, 25, (1, 1, 1, 0.35))

                # action buttons
                for key, label, bx, by, bw, bh in self.get_buttons():
                    active = self.button_active(key)
                    self.ui_rect(bx, by, bw, bh, C(90, 140, 90, 0.85) if active else C(70, 70, 70, 0.55))
                    self.ui_rect(bx, by, bw, bh, (1, 1, 1, 0.9), outline=True, width=1.5)

            if self.minigame_active:
                Color(*C(15, 18, 20, 0.85))
                Rectangle(pos=(0, 0), size=(W, H))
                cx, cy = W / 2.0, H / 2.0
                self.ui_circle(cx, cy, 130, C(70, 75, 80))
                self.ui_circle(cx, cy, 120, C(40, 42, 45))
                self.ui_circle(cx, cy, 120, C(180, 150, 90), outline=True, width=4)
                rad = math.radians(self.lock_angle)
                nx, ny = cx + math.cos(rad) * 95, cy + math.sin(rad) * 95
                self.ui_line(cx, cy, nx, ny, C(240, 70, 70), width=5)
                self.ui_circle(cx, cy, 12, C(210, 210, 210))
                bar_x, bar_y = cx - 110, cy - 190
                self.ui_rect(bar_x, bar_y, 220, 20, C(50, 50, 50))
                prog_w = int(220 * (self.lock_progress / 100.0))
                self.ui_rect(bar_x, bar_y, prog_w, 20, C(60, 200, 100))
                self.ui_rect(bar_x, bar_y, 220, 20, C(220, 220, 220), outline=True, width=2)
                self.ui_rect(W - 80, H - 80, 60, 60, C(180, 60, 60, 0.85))
                self.ui_rect(W - 80, H - 80, 60, 60, (1, 1, 1, 0.9), outline=True, width=2)

            if self.show_full_map:
                Color(*C(20, 22, 24, 0.92))
                Rectangle(pos=(0, 0), size=(W, H))
                mw, mh = min(760, W - 40), min(520, H - 60)
                mx, my_top = (W - mw) / 2, (H - mh) / 2
                self.ui_rect(mx, H - my_top - mh, mw, mh, C(205, 180, 135))
                self.ui_rect(mx, H - my_top - mh, mw, mh, C(70, 50, 30), outline=True, width=6)
                map_sx, map_sy = mw / WORLD_W, mh / WORLD_H
                for r in roads:
                    rx_ = mx + r.x * map_sx
                    ry_top = my_top + r.y * map_sy
                    rw_, rh_ = max(2, r.w * map_sx), max(2, r.h * map_sy)
                    self.ui_rect(rx_, H - ry_top - rh_, rw_, rh_, C(160, 140, 110))
                for name, pos in places:
                    px, py_top = mx + pos.x * map_sx, my_top + pos.y * map_sy
                    self.ui_circle(px, H - py_top, 6, C(170, 40, 30))
                for name, pos in post_offices:
                    px, py_top = mx + pos.x * map_sx, my_top + pos.y * map_sy
                    self.ui_rect(px - 5, H - py_top - 5, 10, 10, C(30, 80, 180))
                p_map_x, p_map_top = mx + self.player.x * map_sx, my_top + self.player.y * map_sy
                self.ui_circle(p_map_x, H - p_map_top, 7, C(30, 140, 40))
                self.ui_rect(W - 100, H - 70, 80, 50, C(180, 60, 60, 0.85))
                self.ui_rect(W - 100, H - 70, 80, 50, (1, 1, 1, 0.9), outline=True, width=2)

        # ---------------- text labels (child widgets, drawn on top) -----
        if overlay_active:
            for lbl in self.button_labels.values():
                self.hide_label(lbl)
            for lbl in self.poi_labels + self.post_labels:
                self.hide_label(lbl)
            self.hide_label(self.lbl_prompt1)
            self.hide_label(self.lbl_prompt2)
        else:
            self.set_label(self.lbl_prompt1, "", 0, 0)
            for safe in safes:
                if not safe["looted"] and self.player.distance_to(safe["pos"]) < 65:
                    sx, sy = self.w2s(safe["pos"])
                    self.set_label(self.lbl_prompt1, "Tap CRACK to open safe", sx - 60, sy - 28,
                                   color=C(255, 230, 100), bold=True, font_size="12sp")
                    break

            self.set_label(self.lbl_prompt2, "", 0, 0)
            for name, pos in post_offices:
                if self.player.distance_to(pos) < 95:
                    sx, sy = self.w2s(pos)
                    cost = int(self.wanted * 40)
                    self.set_label(self.lbl_prompt2, f"Tap PAY to clear wanted (${cost})", sx - 70, sy + 26,
                                   color=C(255, 240, 140), bold=True, font_size="12sp")
                    break

            for i, (name, pos) in enumerate(places):
                sx, sy = self.w2s(pos)
                self.set_label(self.poi_labels[i], name, sx - 45, sy + 36,
                                color=C(45, 40, 30), bold=True, font_size="12sp")
            for i, (name, pos) in enumerate(post_offices):
                sx, sy = self.w2s(pos)
                self.set_label(self.post_labels[i], "POST", sx - 16, sy - 8,
                                color=C(255, 255, 255), bold=True, font_size="11sp")

            for key, label, bx, by, bw, bh in self.get_buttons():
                lbl = self.button_labels[key]
                lbl.text = label
                lbl.color = (1, 1, 1, 1)
                lbl.font_size = "13sp"
                lbl.bold = True
                lbl.text_size = (bw, bh)
                lbl.halign = "center"
                lbl.valign = "middle"
                lbl.size = (bw, bh)
                lbl.pos = (bx, by)
                lbl.opacity = 1

        # HUD text (always shown, even under overlays it's fine to keep on top)
        self.set_label(self.lbl_title, "TEHRAN: SHADOWS OF THE REALM", 18, 8,
                        color=C(235, 200, 100), bold=True, font_size="18sp", height=28, width=W - 40)
        wanted_str = ("*" * math.ceil(self.wanted)) if self.wanted >= 0.5 else "None"
        self.set_label(
            self.lbl_stats,
            f"Health: {int(self.health)}%   Gold: ${self.money}   Wanted: {wanted_str}   Mode: {'Horse' if self.horse else 'Foot'}",
            18, 40, color=C(235, 235, 235), bold=True, font_size="13sp", width=W - 40,
        )
        self.set_label(
            self.lbl_target,
            f"Target: {places[self.target][0]}  ({int(self.player.distance_to(places[self.target][1]))}m)",
            18, 62, color=C(180, 220, 240), font_size="12sp", width=W - 40,
        )
        self.set_label(self.lbl_hint, "Drag = Move   |   Hold = Shoot   |   Buttons = Actions",
                        16, H - 25, color=C(200, 200, 200), font_size="12sp", width=W - 20)

        if self.message_time > 0 and not overlay_active:
            self.set_label(self.lbl_message, self.message, 26, 101, color=C(255, 230, 150), bold=True,
                            font_size="13sp", width=W - 270)
        else:
            self.hide_label(self.lbl_message)

        if self.active_dialogue_time > 0 and not overlay_active:
            self.set_label(self.lbl_dialogue, f'Citizen: "{self.active_dialogue}"', 26, 141,
                            color=C(160, 230, 255), font_size="12sp", width=W - 270)
        else:
            self.hide_label(self.lbl_dialogue)

        if self.minigame_active:
            cx = W / 2.0
            self.set_label(self.lbl_minigame_title, "SAFE CRACKING", cx - 100, H / 2 - 165,
                            color=C(255, 220, 120), bold=True, font_size="17sp", width=200)
            self.set_label(self.lbl_minigame_hint, "Tap the dial in sync with the needle. Tap X to abort.",
                            cx - 170, H / 2 + 190, color=C(230, 230, 230), font_size="12sp", width=340)
        else:
            self.hide_label(self.lbl_minigame_title)
            self.hide_label(self.lbl_minigame_hint)

        if self.show_full_map:
            mw, mh = min(760, W - 40), min(520, H - 60)
            mx, my_top = (W - mw) / 2, (H - mh) / 2
            map_sx, map_sy = mw / WORLD_W, mh / WORLD_H
            for i, (name, pos) in enumerate(places):
                px, py_top = mx + pos.x * map_sx, my_top + pos.y * map_sy
                self.set_label(self.map_place_labels[i], name, px - 30, py_top + 8,
                                color=C(30, 25, 20), bold=True, font_size="10sp")
            for i, (name, pos) in enumerate(post_offices):
                px, py_top = mx + pos.x * map_sx, my_top + pos.y * map_sy
                self.set_label(self.map_post_labels[i], "Telegraph", px - 24, py_top - 18,
                                color=C(20, 40, 100), bold=True, font_size="9sp")
            self.set_label(self.lbl_map_title, "PROVINCIAL MAP OF TEHRAN", mx + mw / 2 - 130, my_top - 34,
                            color=C(255, 225, 140), bold=True, font_size="15sp", width=280)
            p_map_x, p_map_top = mx + self.player.x * map_sx, my_top + self.player.y * map_sy
            self.set_label(self.lbl_you, "YOU", p_map_x - 12, p_map_top - 20, color=C(10, 90, 20), bold=True, font_size="11sp")
            self.set_label(self.lbl_map_close, "Close", W - 100, H - 70, color=(1, 1, 1, 1), bold=True,
                            font_size="13sp", width=80, height=50)
        else:
            for lbl in self.map_place_labels + self.map_post_labels:
                self.hide_label(lbl)
            self.hide_label(self.lbl_map_title)
            self.hide_label(self.lbl_you)
            self.hide_label(self.lbl_map_close)


class TehranApp(App):
    title = "Tehran: Shadows of the Realm"

    def build(self):
        Window.clearcolor = (0.08, 0.08, 0.08, 1)
        return GameWidget()


if __name__ == "__main__":
    TehranApp().run()
