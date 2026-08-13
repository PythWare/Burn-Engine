# DW2_Tools/gui.py

import math, os, random
import tkinter as tk

from .DW2_VGuider import DW2CoordinateGuider
from .Name_Editor import NameEditor
from .Unit_Editor import UnitEditor
from .Item_Editor import ItemEditor
from .DW2_Bodyguard_Progression import GuardTool
from .Atk_Editor import AtkEditor
from .Mov_Editor import MovEditor
from .Mod_Manager import DW2ModManager
from .Utility import HOSTFS_ELF, ICON_DIR, ROOT_DIR


BURN = {
    "void": "#080504",
    "coal": "#120b08",
    "panel": "#1d120c",
    "panel_hot": "#2b160c",
    "leather": "#4b2c1c",
    "leather_dark": "#2b170f",
    "tan": "#c6904f",
    "cream": "#ffe8b4",
    "gold": "#ffd23c",
    "hair": "#ffdd58",
    "ember": "#ff8a1e",
    "orange": "#ff6a00",
    "red": "#ff2f36",
    "purple": "#a76dff",
    "line": "#8a5a2f",
    "muted": "#d7a86c",
    "soft": "#f6c86f",
    "shadow": "#0b0604",
}


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def mix(a, b, t):
    ar, ag, ab = hex_to_rgb(a)
    br, bg, bb = hex_to_rgb(b)
    return rgb_to_hex((
        int(ar + (br - ar) * t),
        int(ag + (bg - ag) * t),
        int(ab + (bb - ab) * t),
    ))


def cut_points(x1, y1, x2, y2, cut):
    return (
        x1 + cut, y1, x2 - cut, y1, x2, y1 + cut, x2, y2 - cut,
        x2 - cut, y2, x1 + cut, y2, x1, y2 - cut, x1, y1 + cut,
    )


def draw_card_icon(canvas, icon, x, y, accent, disabled):
    fill = accent if not disabled else "#5a4a38"
    dark = "#0c0704"
    items = []
    if icon == "stage":
        items.append((canvas.create_polygon(x, y - 17, x + 35, y - 9, x + 30, y + 22, x - 5, y + 15, fill=fill, outline=""), fill))
        items.append((canvas.create_line(x + 4, y - 6, x + 28, y - 1, x + 24, y + 13, x, y + 8, fill=dark, width=2), dark))
        items.append((canvas.create_oval(x + 12, y - 3, x + 19, y + 4, fill=dark, outline=""), dark))
    elif icon == "unit":
        items.append((canvas.create_arc(x - 3, y - 23, x + 37, y + 17, start=0, extent=180, fill=fill, outline=fill), fill))
        items.append((canvas.create_rectangle(x + 2, y - 4, x + 32, y + 11, fill=fill, outline=""), fill))
        items.append((canvas.create_rectangle(x + 8, y + 11, x + 26, y + 18, fill=fill, outline=""), fill))
    elif icon == "item":
        items.append((canvas.create_polygon(x + 16, y - 22, x + 35, y - 2, x + 16, y + 22, x - 3, y - 2, fill=fill, outline=""), fill))
        items.append((canvas.create_polygon(x + 16, y - 14, x + 25, y - 2, x + 16, y + 12, x + 7, y - 2, fill=dark, outline=""), dark))
    elif icon == "name":
        items.append((canvas.create_rectangle(x - 4, y - 18, x + 38, y + 18, fill=fill, outline=""), fill))
        items.append((canvas.create_polygon(x + 38, y - 18, x + 46, y - 10, x + 46, y + 10, x + 38, y + 18, fill=fill, outline=""), fill))
        items.append((canvas.create_line(x + 6, y - 5, x + 31, y - 5, fill=dark, width=2), dark))
        items.append((canvas.create_line(x + 6, y + 6, x + 25, y + 6, fill=dark, width=2), dark))
    elif icon == "guard":
        items.append((canvas.create_polygon(x + 17, y - 24, x + 38, y - 14, x + 34, y + 12, x + 17, y + 24, x, y + 12, x - 4, y - 14, fill=fill, outline=""), fill))
        items.append((canvas.create_line(x + 17, y - 15, x + 17, y + 15, fill=dark, width=2), dark))
        items.append((canvas.create_line(x + 6, y - 5, x + 28, y - 5, fill=dark, width=2), dark))
    elif icon == "atk":
        # crossed blades
        items.append((canvas.create_line(x - 4, y + 18, x + 34, y - 20, fill=fill, width=5), fill))
        items.append((canvas.create_line(x + 34, y + 18, x - 4, y - 20, fill=fill, width=5), fill))
        items.append((canvas.create_oval(x + 11, y - 4, x + 19, y + 4, fill=dark, outline=""), dark))
    elif icon == "mov":
        # motion arc with nodes
        items.append((canvas.create_arc(x - 6, y - 18, x + 30, y + 26, start=20, extent=140, style="arc", outline=fill, width=4), fill))
        items.append((canvas.create_oval(x - 8, y + 2, x - 1, y + 9, fill=fill, outline=""), fill))
        items.append((canvas.create_oval(x + 12, y - 20, x + 19, y - 13, fill=fill, outline=""), fill))
        items.append((canvas.create_oval(x + 30, y + 2, x + 37, y + 9, fill=fill, outline=""), fill))
    elif icon == "mod":
        for offset in (8, 0, -8):
            items.append((canvas.create_polygon(x, y - 18 + offset, x + 34, y - 18 + offset, x + 42, y - 9 + offset, x + 8, y - 9 + offset, fill=fill, outline=""), fill))
    return items


class BurnRackCanvas(tk.Frame):
    """
    Scrollable 2 column tool card rack with a heat bullet scrollbar
    """

    CARD_H = 116
    GAP = 14
    COLS = 2
    BAR_W = 20

    def __init__(self, parent, controller):
        super().__init__(parent, bg=BURN["void"])
        self.controller = controller
        self.cards = []
        self.card_items = {}
        self.hover_key = None
        self.content_h = 1
        self.bullet_phase = 0.0
        self.anim_job = None

        self.cardcanvas = tk.Canvas(self, bg=BURN["void"], bd=0, highlightthickness=0)
        self.cardcanvas.pack(side="left", fill="both", expand=True)
        self.heatbar = tk.Canvas(self, width=self.BAR_W, bg=BURN["coal"], bd=0, highlightthickness=0)
        self.heatbar.pack(side="right", fill="y")

        self.cardcanvas.bind("<Configure>", lambda e: self.render())
        self.cardcanvas.bind("<Motion>", self.on_motion)
        self.cardcanvas.bind("<Leave>", self.on_leave)
        self.cardcanvas.bind("<Button-1>", self.on_click)
        self.cardcanvas.bind("<MouseWheel>", self.on_wheel)
        self.heatbar.bind("<Button-1>", self.bar_to)
        self.heatbar.bind("<B1-Motion>", self.bar_to)
        self.heatbar.bind("<MouseWheel>", self.on_wheel)
        self.bind("<Destroy>", self.on_destroy)

        self.start_anim()

    def set_cards(self, cards):
        self.cards = cards
        self.render()

    def render(self):
        c = self.cardcanvas
        w = max(c.winfo_width(), 1)
        c.delete("all")
        self.card_items.clear()

        gap = self.GAP
        card_w = (w - gap) / self.COLS
        rows = max(1, math.ceil(len(self.cards) / self.COLS))
        self.content_h = rows * (self.CARD_H + gap)
        c.configure(scrollregion=(0, 0, w, self.content_h))

        for index, card in enumerate(self.cards):
            row = index // self.COLS
            col = index % self.COLS
            cx = col * (card_w + gap)
            cy = row * (self.CARD_H + gap)
            self.draw_card(card, cx, cy, card_w, self.CARD_H)

        self.set_hover(self.hover_key)
        self.sync_bar()

    def draw_card(self, card, x, y, w, h):
        c = self.cardcanvas
        key = card["key"]
        accent = card["accent"]
        disabled = card.get("disabled", False)
        fill = "#17100c" if not disabled else "#120d0a"
        outline = "#60401f" if not disabled else "#3a2a20"
        text = BURN["cream"] if not disabled else "#796858"
        muted = BURN["muted"] if not disabled else "#5e5144"
        launch_fill = "#2b170d" if not disabled else "#1b1511"

        panel = c.create_polygon(cut_points(x, y, x + w, y + h, 14), fill=fill, outline=outline, width=1)
        stripe = c.create_rectangle(x + 14, y, x + w - 14, y + 5, fill=accent if not disabled else "#4a3c28", outline="")
        tag = c.create_text(x + w - 18, y + 17, text=card["tag"], anchor="ne",
                            fill=accent if not disabled else "#6f614f", font=("Segoe UI", 9, "bold"))
        icon_items = draw_card_icon(c, card["icon"], x + 26, y + 57, accent, disabled)
        title = c.create_text(x + 80, y + 26, text=card["title"], anchor="nw", fill=text, font=("Segoe UI", 14, "bold"))
        desc = c.create_text(x + 80, y + 54, text=card["description"], anchor="nw", fill=muted,
                             font=("Segoe UI", 9), width=max(150, int(w - 112)))
        launch = c.create_polygon(cut_points(x + w - 120, y + h - 33, x + w - 18, y + h - 12, 6),
                                  fill=launch_fill, outline=accent if not disabled else "#403225", width=1)
        launch_text = c.create_text(x + w - 69, y + h - 22, text="IGNITE" if not disabled else "LATER",
                                    anchor="center", fill=accent if not disabled else "#6b5a47", font=("Segoe UI", 9, "bold"))

        self.card_items[key] = {
            "bbox": (x, y, x + w, y + h),
            "command": card.get("command"),
            "disabled": disabled,
            "accent": accent,
            "panel": panel, "stripe": stripe, "tag": tag, "title": title,
            "desc": desc, "launch": launch, "launch_text": launch_text,
            "icon_items": icon_items,
        }

    def sync_bar(self):
        b = self.heatbar
        b.delete("all")
        h = max(b.winfo_height(), 1)
        w = self.BAR_W
        b.create_line(w / 2, 6, w / 2, h - 6, fill="#4a2814", width=3)
        top, bottom = self.cardcanvas.yview()
        scrollable = (bottom - top) < 0.999
        span = h - 12
        y1 = 6 + top * span
        y2 = 6 + bottom * span
        thumb_col = BURN["ember"] if scrollable else "#5a3418"
        b.create_line(w / 2, y1 + 5, w / 2, y2 - 5, fill=thumb_col, width=5)
        cy = (y1 + y2) / 2
        glow = mix(BURN["orange"], BURN["gold"], 0.5 + 0.5 * math.sin(self.bullet_phase))
        r_out = 9 if scrollable else 6
        b.create_oval(w / 2 - r_out, cy - r_out, w / 2 + r_out, cy + r_out,
                      fill=mix(BURN["shadow"], glow, 0.45), outline="")
        b.create_oval(w / 2 - 5, cy - 5, w / 2 + 5, cy + 5, fill=glow, outline=BURN["gold"], width=2)
        self.thumb_cy = cy

    def bar_to(self, event):
        h = max(self.heatbar.winfo_height(), 1)
        frac = (event.y - 6) / max(h - 12, 1)
        frac = min(max(frac, 0.0), 1.0)
        top, bottom = self.cardcanvas.yview()
        visible = bottom - top
        self.cardcanvas.yview_moveto(max(0.0, frac - visible / 2))
        self.sync_bar()

    def on_wheel(self, event):
        self.cardcanvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        self.sync_bar()

    def on_motion(self, event):
        cy = self.cardcanvas.canvasy(event.y)
        cx = self.cardcanvas.canvasx(event.x)
        hovered = None
        for key, data in self.card_items.items():
            x1, y1, x2, y2 = data["bbox"]
            if x1 <= cx <= x2 and y1 <= cy <= y2 and not data["disabled"]:
                hovered = key
                break
        if hovered != self.hover_key:
            self.set_hover(hovered)

    def on_leave(self, event=None):
        self.set_hover(None)

    def on_click(self, event):
        cy = self.cardcanvas.canvasy(event.y)
        cx = self.cardcanvas.canvasx(event.x)
        for data in self.card_items.values():
            x1, y1, x2, y2 = data["bbox"]
            if x1 <= cx <= x2 and y1 <= cy <= y2 and not data["disabled"]:
                command = data.get("command")
                if command is not None:
                    command()
                return

    def set_hover(self, key):
        self.hover_key = key
        c = self.cardcanvas
        for card_key, data in self.card_items.items():
            active = card_key == key
            accent = data["accent"]
            c.itemconfigure(data["panel"], fill=BURN["panel_hot"] if active else "#17100c",
                            outline=accent if active else "#60401f", width=2 if active else 1)
            c.itemconfigure(data["launch"], fill=accent if active else "#2b170d")
            c.itemconfigure(data["launch_text"], fill=BURN["void"] if active else accent)
            c.itemconfigure(data["title"], fill=BURN["hair"] if active else BURN["cream"])
            for item, base_fill in data["icon_items"]:
                target_fill = accent if active and base_fill != "#0c0704" else base_fill
                c.itemconfigure(item, fill=target_fill)
        self.cardcanvas.configure(cursor="hand2" if key else "")

    def start_anim(self):
        if not self.winfo_exists():
            return
        self.bullet_phase += 0.22
        if hasattr(self, "_thumb_cy"):
            self.sync_bar()
        self.anim_job = self.after(90, self.start_anim)

    def on_destroy(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self.anim_job is not None:
            try:
                self.after_cancel(self.anim_job)
            except tk.TclError:
                pass
            self.anim_job = None


class BurnHubCanvas(tk.Canvas):
    """Canvas only launch hub, cards live in a scrollable child rack"""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=BURN["void"], bd=0, highlightthickness=0, relief="flat")
        self.controller = controller
        self.cards = []
        self.embers = []
        self.status_item = None
        self.status_dot = None
        self.heat_lines = []
        self.animation_job = None
        self.render_job = None
        self.tick = 0
        self.random = random.Random(42)

        self.rack = BurnRackCanvas(self, controller)

        self.bind("<Configure>", self.schedule_render)
        self.bind("<Destroy>", self.on_destroy)

    def set_tools(self, cards):
        self.cards = cards
        self.rack.set_cards(cards)
        self.render()
        if self.animation_job is None:
            self.animation_job = self.after(80, self.animate)

    def set_status(self, text, tone=None):
        if self.status_item is not None:
            self.itemconfigure(self.status_item, text=text, fill=tone or BURN["cream"])
        if self.status_dot is not None:
            self.itemconfigure(self.status_dot, fill=tone or BURN["gold"])

    def schedule_render(self, event=None):
        if self.render_job is not None:
            self.after_cancel(self.render_job)
        self.render_job = self.after(35, self.render)

    def on_destroy(self, event=None):
        if self.animation_job is not None:
            try:
                self.after_cancel(self.animation_job)
            except tk.TclError:
                pass
            self.animation_job = None

    def render(self):
        self.render_job = None
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        self.delete("all")
        self.embers.clear()
        self.heat_lines.clear()
        self.status_item = None
        self.status_dot = None

        self.draw_background(w, h)
        self.draw_header(w)
        self.draw_work_area(w, h)
        self.draw_embers(w, h)
        self.set_status(self.controller.status_text)

    def draw_background(self, w, h):
        for y in range(0, h, 10):
            t = y / max(h, 1)
            fill = mix(BURN["void"], BURN["leather_dark"], t * 0.75)
            self.create_rectangle(0, y, w, y + 10, fill=fill, outline="")

        for x in range(-120, w + 180, 120):
            self.create_line(x, 0, x + 360, h, fill="#23110a", width=1)

        for i in range(10):
            x1 = -180 + i * 160
            y1 = 72 + (i % 3) * 46
            self.create_line(x1, y1, x1 + 340, y1 - 120, x1 + 660, y1 + 16, fill="#2a160d", width=18, smooth=True)
            self.create_line(x1 + 26, y1 + 2, x1 + 350, y1 - 92, x1 + 626, y1 + 22, fill="#3b1d0c", width=4, smooth=True)

        right = w - 40
        for row in range(0, 170, 10):
            for col in range(0, 230, 10):
                if (row + col) % 30 == 0:
                    self.create_oval(right - col, 28 + row, right - col + 2, 30 + row, fill="#5b2e14", outline="")

        self.create_polygon(0, h - 120, w * 0.42, h - 40, w, h - 138, w, h, 0, h, fill="#100805", outline="")

    def draw_header(self, w):
        margin = 26
        x1, y1 = margin, 24
        x2, y2 = w - margin, 188
        eyebrow_rule_x1 = x1 + 44
        eyebrow_rule_y = y1 + 58
        eyebrow_rule_x2 = x1 + 260
        hero_title_x = x1 + 40
        hero_title_y = 19
        hero_subtitle_x = x1 + 43
        hero_subtitle_y = y1 + 90
        loadout_title_x = x2 - 36
        loadout_title_y = y1 + 42
        loadout_note_x = x2 - 36
        loadout_note_y = y1 + 70
        loadout_note_width = 180
        status_text_x = x2 - 36
        status_text_y = y1 + 90
        status_text_width = 180
        status_dot_x = status_text_x - status_text_width - 14
        status_dot_y = status_text_y + 3
        status_dot_size = 12
        gauntlet_x = x2 - 420
        gauntlet_y = y1 + 45

        self.cut_panel(x1, y1, x2, y2, cut=24, fill="#180d08", outline=BURN["line"], width=2)
        self.cut_panel(x1 + 10, y1 + 10, x2 - 10, y2 - 10, cut=18, fill="#201108", outline="#5d3318", width=1)
        self.create_rectangle(x1 + 36, y2 - 26, x2 - 36, y2 - 19, fill=BURN["orange"], outline="")
        self.create_rectangle(x1 + 36, y2 - 19, x2 - 36, y2 - 16, fill=BURN["gold"], outline="")
        self.create_line(eyebrow_rule_x1, eyebrow_rule_y, eyebrow_rule_x2, eyebrow_rule_y, fill=BURN["gold"], width=2)
        self.create_text(hero_title_x, hero_title_y, text="Burn Engine", anchor="nw", fill=BURN["cream"], font=("Segoe UI", 36, "bold"))
        self.create_text(hero_subtitle_x, hero_subtitle_y, text="Hub for Dynasty Warriors 2 modding", anchor="nw", fill=BURN["muted"], font=("Segoe UI", 12))
        self.draw_gauntlet_plate(gauntlet_x, gauntlet_y)
        self.create_text(loadout_title_x, loadout_title_y, text="Loadout", anchor="ne", fill=BURN["hair"], font=("Segoe UI", 11, "bold"))
        self.create_text(loadout_note_x, loadout_note_y, text="Ember Core", anchor="ne", fill=BURN["muted"], font=("Segoe UI", 10), justify="right", width=loadout_note_width)
        self.status_dot = self.create_oval(status_dot_x, status_dot_y, status_dot_x + status_dot_size, status_dot_y + status_dot_size, fill=BURN["gold"], outline="")
        self.status_item = self.create_text(status_text_x, status_text_y, text="", anchor="ne", fill=BURN["cream"], font=("Segoe UI", 10, "bold"), justify="right", width=status_text_width)

    def draw_work_area(self, w, h):
        margin = 26
        gap = 18
        top = 212
        bottom = h - 28
        side_w = min(420, max(350, int(w * 0.33)))
        left_w = w - margin * 2 - gap - side_w
        side_x = margin + left_w + gap

        self.draw_section_label(margin, top, left_w, "Tool Rack", "Live modules,")
        rack_y = top + 50
        rack_h = bottom - rack_y
        self.rack.place(x=margin, y=rack_y, width=left_w, height=rack_h)
        self.draw_side_panel(side_x, top, side_w, bottom - top)

    def draw_section_label(self, x, y, width, title, subtitle):
        self.create_text(x, y, text=title, anchor="nw", fill=BURN["cream"], font=("Segoe UI", 16, "bold"))
        self.create_text(x, y + 26, text=subtitle, anchor="nw", fill=BURN["muted"], font=("Segoe UI", 10))
        self.create_line(x, y + 42, x + width, y + 42, fill="#5e351b", width=1)
        self.create_line(x, y + 43, x + min(width, 220), y + 43, fill=BURN["gold"], width=2)

    def draw_side_panel(self, x, y, w, h):
        self.cut_panel(x, y, x + w, y + h, cut=16, fill="#160e0a", outline="#5b351b", width=1)
        self.create_rectangle(x + 1, y + 1, x + w - 1, y + 56, fill="#24140b", outline="")
        self.create_rectangle(x + 1, y + 1, x + 7, y + 56, fill=BURN["purple"], outline="")
        self.create_text(x + 22, y + 17, text="System Heat", anchor="nw", fill=BURN["cream"], font=("Segoe UI", 15, "bold"))

        elf_detected = os.path.exists(HOSTFS_ELF)
        root_label = self.short_path(ROOT_DIR)
        elf_label = self.short_path(HOSTFS_ELF)
        status_color = "#58f28a" if elf_detected else BURN["red"]
        status_text = "Hostfs ELF detected" if elf_detected else "Hostfs ELF missing"

        rows = [
            ("Toolkit Root", root_label, BURN["gold"]),
            ("Target Hostfs ELF", elf_label, BURN["orange"]),
            ("ELF Status", status_text, status_color),
            ("Live Tools", f"{len(self.cards)} ignition ready modules", BURN["purple"]),
        ]

        ry = y + 84
        for label, value, color in rows:
            self.draw_status_row(x + 20, ry, w - 40, label, value, color)
            ry += 64

        notes_y = min(y + h - 184, ry + 10)
        self.create_text(x + 22, notes_y, text="Forge Notes", anchor="nw", fill=BURN["cream"], font=("Segoe UI", 13, "bold"))
        notes = "Burn Engine mods Dynasty Warriors 2. More tools will be made."
        self.create_text(x + 22, notes_y + 30, text=notes, anchor="nw", fill=BURN["muted"], font=("Segoe UI", 10), width=w - 44)

        footer_y = y + h - 48
        self.create_line(x + 20, footer_y - 14, x + w - 20, footer_y - 14, fill="#4b2b16", width=1)
        self.create_text(x + 22, footer_y, text="Heat loop", anchor="nw", fill=BURN["gold"], font=("Segoe UI", 9, "bold"))

    def draw_status_row(self, x, y, w, label, value, color):
        self.cut_panel(x, y, x + w, y + 54, cut=8, fill="#20130c", outline="#503018", width=1)
        self.create_rectangle(x, y, x + 6, y + 54, fill=color, outline="")
        self.create_text(x + 20, y + 11, text=label, anchor="nw", fill=BURN["muted"], font=("Segoe UI", 9))
        self.create_text(x + 20, y + 29, text=value, anchor="nw", fill=BURN["cream"], font=("Segoe UI", 9, "bold"), width=w - 30)

    def draw_embers(self, w, h):
        for i in range(30):
            size = self.random.choice((2, 2, 3, 4))
            x = self.random.randint(0, max(w, 1))
            y = self.random.randint(180, max(h - 20, 181))
            color = self.random.choice((BURN["gold"], BURN["orange"], "#ffb02e", "#ff4b1f"))
            item = self.create_oval(x, y, x + size, y + size, fill=color, outline="")
            self.embers.append({
                "id": item, "x": float(x), "y": float(y), "size": size,
                "speed": self.random.uniform(0.35, 1.15), "drift": self.random.uniform(0.015, 0.05),
                "phase": self.random.uniform(0, math.tau), "color": color,
            })

    def animate(self):
        try:
            w = self.winfo_width()
            h = self.winfo_height()
        except tk.TclError:
            self.animation_job = None
            return

        self.tick += 1
        for idx, item in enumerate(self.heat_lines):
            color = BURN["red"] if (self.tick + idx) % 18 < 6 else BURN["orange"]
            self.itemconfigure(item, fill=color)

        for ember in self.embers:
            ember["y"] -= ember["speed"]
            ember["x"] += math.sin(self.tick * ember["drift"] + ember["phase"]) * 0.45
            if ember["y"] < 150:
                ember["y"] = h - self.random.randint(20, 80)
                ember["x"] = self.random.randint(0, max(w, 1))
            size = ember["size"]
            self.coords(ember["id"], ember["x"], ember["y"], ember["x"] + size, ember["y"] + size)

        self.animation_job = self.after(70, self.animate)

    def cut_panel(self, x1, y1, x2, y2, cut, fill, outline, width=1):
        return self.create_polygon(cut_points(x1, y1, x2, y2, cut), fill=fill, outline=outline, width=width)

    def draw_gauntlet_plate(self, x, y):
        self.cut_panel(x, y, x + 128, y + 76, cut=14, fill="#2b160b", outline=BURN["gold"], width=2)
        self.create_rectangle(x + 14, y + 20, x + 114, y + 36, fill=BURN["gold"], outline="")
        self.create_rectangle(x + 18, y + 40, x + 43, y + 58, fill=BURN["red"], outline="")
        self.create_rectangle(x + 51, y + 40, x + 76, y + 58, fill=BURN["orange"], outline="")
        self.create_rectangle(x + 84, y + 40, x + 109, y + 58, fill=BURN["gold"], outline="")
        for lx in (x + 18, x + 48, x + 78, x + 108):
            line = self.create_rectangle(lx, y + 13, lx + 7, y + 64, fill=BURN["orange"], outline="")
            self.heat_lines.append(line)
        self.create_text(x + 64, y + 8, text="EMBER", anchor="n", fill=BURN["void"], font=("Segoe UI", 9, "bold"))

    def short_path(self, path):
        normalized = os.path.normpath(path)
        if len(normalized) <= 46:
            return normalized
        head, tail = os.path.split(normalized)
        parent = os.path.basename(head)
        return os.path.join("...", parent, tail)


class Core_Tools():
    def __init__(self, root):
        self.root = root
        self.root.title("Burn Engine, Dynasty Warriors 2 Modding Toolkit")
        self.root.geometry("1280x860")
        self.root.minsize(1120, 760)
        self.root.configure(bg=BURN["void"])

        self.status_text = "Gauntlet bay online. Select a module to ignite."
        self.tool_buttons = []

        self.stage_editor_window = None
        self.name_editor_window = None
        self.unit_editor_window = None
        self.item_editor_window = None
        self.guard_editor_window = None
        self.atk_editor_window = None
        self.mov_editor_window = None
        self.toc_updater_window = None
        self.mod_manager_window = None

        self.gui_setup()

    def set_status(self, text, tone=None):
        self.status_text = text
        if hasattr(self, "hub"):
            self.hub.set_status(text, tone)

    def focus_existing(self, window_attr, label):
        win = getattr(self, window_attr)
        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_force()
            self.set_status(f"{label} already lit. Bringing it forward.", BURN["gold"])
            return True
        return False

    def launch(self, window_attr, title, editor_cls, lit_status, tone):
        if self.focus_existing(window_attr, title):
            return
        win = tk.Toplevel(self.root)
        win.title(title)
        setattr(self, window_attr, win)
        editor_cls(win)
        self.set_status(lit_status, tone)

        def on_close():
            setattr(self, window_attr, None)
            win.destroy()
            self.set_status(f"{title} closed. Hub heat holding.", BURN["cream"])

        win.protocol("WM_DELETE_WINDOW", on_close)

    def open_stage_editor(self):
        self.launch("stage_editor_window", "Afterburn Stageworks", DW2CoordinateGuider, "Afterburn Stageworks ignited.", BURN["orange"])

    def open_name_editor(self):
        self.launch("name_editor_window", "Ember Registry", NameEditor, "Ember Registry ignited.", BURN["gold"])

    def open_unit_editor(self):
        self.launch("unit_editor_window", "Knuckleforge", UnitEditor, "Knuckleforge ignited.", BURN["purple"])

    def open_item_editor(self):
        self.launch("item_editor_window", "Dragonvault", ItemEditor, "Dragonvault ignited.", BURN["hair"])

    def open_guard_editor(self):
        self.launch("guard_editor_window", "Golden Lineage", GuardTool, "Golden Lineage ignited.", BURN["red"])

    def open_atk_editor(self):
        self.launch("atk_editor_window", "Emberchain", AtkEditor, "Emberchain ignited.", BURN["ember"])

    def open_mov_editor(self):
        self.launch("mov_editor_window", "Emberflow", MovEditor, "Emberflow ignited.", BURN["gold"])

    def run_dialog_tool(self, module_name, label, tone):
        try:
            from importlib import import_module
            module = import_module(f".{module_name}", __package__)
        except Exception as e:
            self.set_status(f"{label} unavailable: {e}", BURN["red"])
            return

        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        try:
            module.launch(parent=self.root,
                          status=lambda msg: self.set_status(msg, tone))
        except Exception as e:
            self.set_status(f"{label} failed: {e}", BURN["red"])
        finally:
            self.root.configure(cursor="")

    def open_linkdata_unpacker(self):
        self.run_dialog_tool("dw2_linkdata_extract", "LINKDATA Unpacker", BURN["gold"])

    def open_hostfs_patcher(self):
        self.run_dialog_tool("dw2_hostfs_patch", "Host-FS Patcher", BURN["ember"])

    def open_toc_updater(self):
        try:
            from .dw2_toc_updater import TocUpdaterApp
        except Exception as e:
            self.set_status(f"HostFS TOC Updater unavailable: {e}", BURN["red"])
            return
        self.launch("toc_updater_window", "HostFS TOC Updater", TocUpdaterApp,
                     "HostFS TOC Updater ignited.", BURN["orange"])

    def open_mod_manager(self):
        self.launch("mod_manager_window", "Burn Engine, Mod Manager", DW2ModManager, "Mod Manager ignited.", BURN["orange"])

    def gui_setup(self):
        """Handles GUI designing"""
        self.hub = BurnHubCanvas(self.root, self)
        self.hub.pack(fill="both", expand=True)

        tool_cards = [
            {"key": "stage", "title": "Afterburn Stageworks", "description": "Battlefield records.",
             "tag": "Field", "icon": "stage", "accent": BURN["orange"], "command": self.open_stage_editor},
            {"key": "unit", "title": "Knuckleforge", "description": "Unit data, model references, move and stat bytes.",
             "tag": "Roster", "icon": "unit", "accent": BURN["purple"], "command": self.open_unit_editor},
            {"key": "item", "title": "Dragonvault", "description": "Pickup values, stat drops, item balance tuning.",
             "tag": "Gear", "icon": "item", "accent": BURN["hair"], "command": self.open_item_editor},
            {"key": "name", "title": "Ember Registry", "description": "String data for characters, titles, etc.",
             "tag": "Names", "icon": "name", "accent": BURN["gold"], "command": self.open_name_editor},
            {"key": "guard", "title": "Golden Lineage", "description": "Guard progression tiers and formation patch values.",
             "tag": "Guard", "icon": "guard", "accent": BURN["red"], "command": self.open_guard_editor},
            {"key": "atk", "title": "Emberchain", "description": "ATK combo graph, attack chains and combat data.",
             "tag": "Combo", "icon": "atk", "accent": BURN["ember"], "command": self.open_atk_editor},
            {"key": "mov", "title": "Emberflow", "description": "MOV motion chains, clip ids, next move and SFX.",
             "tag": "Motion", "icon": "mov", "accent": BURN["gold"], "command": self.open_mov_editor},
            {"key": "unpack", "title": "LINKDATA Unpacker", "description": "Unpack LINKDATA.BNS into loose files.",
             "tag": "Extract", "icon": "mod", "accent": BURN["gold"], "command": self.open_linkdata_unpacker},
            {"key": "hostfs", "title": "Host-FS Patcher", "description": "Patch the ELF to load loose files from host.",
             "tag": "Patch", "icon": "mod", "accent": BURN["ember"], "command": self.open_hostfs_patcher},
            {"key": "toc", "title": "Host-FS TOC Updater", "description": "Rebuild the hostFS ELF after editing files.",
             "tag": "Rebuild", "icon": "mod", "accent": BURN["orange"], "command": self.open_toc_updater},
            {"key": "mods", "title": "Mod Manager", "description": "Apply, disable, and restore DW2 Mods.",
             "tag": "Forge", "icon": "mod", "accent": BURN["orange"], "command": self.open_mod_manager},
        ]
        self.tool_buttons = tool_cards
        self.hub.set_tools(tool_cards)
