# DW2_Tools/DW2_Bodyguard_Progression.py

import os
import tkinter as tk

from .Utility import HOSTFS_ELF, ICON_DIR, MODS_DIR


GUARD_TIER_COUNT = 5
FIELDS_PER_TIER = 3
GUARD_BYTE_COUNT = GUARD_TIER_COUNT * FIELDS_PER_TIER
DW2_GUARD_MOD_EXT = ".DW2GuardMod"

BURN_GUARD = {
    "void": "#080504",
    "coal": "#120805",
    "panel": "#1d0d08",
    "panel_2": "#2a1209",
    "panel_3": "#3b100f",
    "line": "#8d3f19",
    "line_dim": "#5a2b17",
    "cream": "#ffe8b4",
    "gold": "#ffd23c",
    "orange": "#ff8a1e",
    "red": "#ff3b3b",
    "red_dark": "#6f111c",
    "lilac": "#BF98D9",
    "lilac_dark": "#6e4c83",
    "green": "#78bf8d",
    "muted": "#d7a86c",
    "entry": "#130906",
    "entry_lit": "#2d140c",
    "shadow": "#060302",
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


class GuardTool:
    """
    Dynasty Warriors 2 Bodyguard Progression Editor
    """

    AI_GUARD_FOLLOW = 0x38E90
    FOLLOW_VALUE = b"\x11"
    GUARD_PROG_OFFSET = 0x169D40

    def __init__(self, root):
        self.root = root
        self.root.title("Golden Lineage")

        self.root.configure(bg=BURN_GUARD["void"])
        self.root.minsize(1040, 650)
        self.root.geometry("1100x700")
        self.root.resizable(True, True)

        self.elf_path = HOSTFS_ELF
        self.guard_prog_offset = self.GUARD_PROG_OFFSET
        self.guard_bytes = bytearray(GUARD_BYTE_COUNT)
        self.follow_byte = None
        self.hex_values = [f"{i:02X}" for i in range(256)]
        self.spin_widgets: list[tk.Spinbox] = []
        self.spin_vars: list[tk.StringVar] = []
        self.header_embers = []
        self.animation_job = None
        self.modname = tk.StringVar()

        self.labels = [
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
            "Rank (name ID value)",
            "Guard Model",
            "Guard Motion/Moveset",
        ]
        self.tier_headers = [
            "Tier 1 Bodyguards",
            "Tier 2 Bodyguards",
            "Tier 3 Bodyguards",
            "Tier 4 Bodyguards",
            "Tier 5 Bodyguards",
        ]

        self.build_gui()

        if os.path.exists(self.elf_path):
            self.read_data()
        else:
            self.set_status(f"Hostfs ELF not found at: {self.elf_path}", ok=False)

        self.root.bind("<Destroy>", self.on_destroy, add="+")
        self.start_header_animation()

    def build_gui(self):
        self.shell = tk.Frame(self.root, bg=BURN_GUARD["void"])
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(
            self.shell,
            height=118,
            bg=BURN_GUARD["void"],
            bd=0,
            highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self.draw_header)

        content = tk.Frame(self.shell, bg=BURN_GUARD["void"], padx=18, pady=12)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, minsize=320)
        content.rowconfigure(0, weight=1)

        tiers_panel, tiers_body = self.make_panel(content, "Progression Tiers", BURN_GUARD["orange"])
        tiers_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tiers_body.columnconfigure(0, weight=1)
        tiers_body.columnconfigure(1, weight=1)
        self.build_tier_grid(tiers_body)

        preview_panel, preview_body = self.make_panel(content, "Guard Patch Deck", BURN_GUARD["red"])
        preview_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self.build_preview_panel(preview_body)

        action_panel, action_body = self.make_panel(self.shell, "Bodyguard Control", BURN_GUARD["lilac"])
        action_panel.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        self.build_action_panel(action_body)

    def make_panel(self, parent, title, accent=None):
        accent = accent or BURN_GUARD["orange"]
        outer = tk.Frame(
            parent,
            bg=BURN_GUARD["panel"],
            highlightbackground=BURN_GUARD["line"],
            highlightcolor=BURN_GUARD["line"],
            highlightthickness=1,
        )
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=BURN_GUARD["red_dark"], height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            header,
            text=title,
            bg=BURN_GUARD["red_dark"],
            fg=BURN_GUARD["cream"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(outer, bg=BURN_GUARD["panel"], padx=12, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        return outer, body

    def burn_label(self, parent, text, **kwargs):
        bg = kwargs.pop("bg", BURN_GUARD["panel"])
        fg = kwargs.pop("fg", BURN_GUARD["cream"])
        font = kwargs.pop("font", ("Segoe UI", 9))
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)

    def burn_entry(self, parent, textvariable, width=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=BURN_GUARD["entry"],
            fg=BURN_GUARD["cream"],
            insertbackground=BURN_GUARD["gold"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BURN_GUARD["line_dim"],
            highlightcolor=BURN_GUARD["gold"],
            font=("Consolas", 10),
        )

    def burn_button(self, parent, text, command, accent=None, fg=None):
        accent = accent or BURN_GUARD["red_dark"]
        fg = fg or BURN_GUARD["cream"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg=fg,
            activebackground=BURN_GUARD["gold"],
            activeforeground=BURN_GUARD["shadow"],
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_GUARD["line"],
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
        )

    def build_tier_grid(self, parent):
        vcmd_hex = (self.root.register(self.validate_hex_byte), "%P")

        for tier in range(GUARD_TIER_COUNT):
            card = tk.Frame(
                parent,
                bg=BURN_GUARD["panel_2"],
                highlightbackground=BURN_GUARD["line_dim"],
                highlightthickness=1,
                padx=12,
                pady=10,
            )
            card.grid(
                row=tier // 2,
                column=tier % 2,
                sticky="nsew",
                padx=(0, 8) if tier % 2 == 0 else (8, 0),
                pady=7,
            )
            parent.rowconfigure(tier // 2, weight=1)
            card.columnconfigure(1, weight=1)

            accent = BURN_GUARD["lilac"] if tier < 4 else BURN_GUARD["red"]
            self.burn_label(
                card,
                self.tier_headers[tier],
                bg=BURN_GUARD["panel_2"],
                fg=accent,
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

            for field in range(FIELDS_PER_TIER):
                idx = tier * FIELDS_PER_TIER + field
                self.field_row(card, idx, self.labels[idx], field + 1, vcmd_hex)

    def field_row(self, parent, index, label_text, row, vcmd_hex):
        self.burn_label(
            parent,
            label_text,
            bg=BURN_GUARD["panel_2"],
            fg=BURN_GUARD["cream"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)

        var = tk.StringVar(value="00")
        var.trace_add("write", lambda *args: self.update_preview())
        sb = tk.Spinbox(
            parent,
            values=self.hex_values,
            textvariable=var,
            width=5,
            wrap=True,
            validate="key",
            validatecommand=vcmd_hex,
            command=self.update_preview,
            bg=BURN_GUARD["entry"],
            fg=BURN_GUARD["cream"],
            insertbackground=BURN_GUARD["gold"],
            buttonbackground=BURN_GUARD["red_dark"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BURN_GUARD["line_dim"],
            highlightcolor=BURN_GUARD["gold"],
            font=("Consolas", 10, "bold"),
            justify="center",
        )
        sb.bind("<FocusOut>", self.force_upper_hex)
        sb.bind("<Return>", self.force_upper_hex)
        sb.bind("<KeyRelease>", lambda event: self.update_preview())
        sb.grid(row=row, column=1, sticky="e", pady=5)

        decimal_label = self.burn_label(
            parent,
            "0",
            bg=BURN_GUARD["panel_2"],
            fg=BURN_GUARD["muted"],
            font=("Segoe UI", 8, "bold"),
            anchor="e",
            width=4,
        )
        decimal_label.grid(row=row, column=2, sticky="e", padx=(8, 0), pady=5)
        setattr(self, f"decimal_label_{index}", decimal_label)

        self.spin_widgets.append(sb)
        self.spin_vars.append(var)

    def build_preview_panel(self, parent):
        parent.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            parent,
            height=190,
            bg=BURN_GUARD["panel"],
            bd=0,
            highlightthickness=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="ew")
        self.preview_canvas.bind("<Configure>", lambda event: self.update_preview())

        details = tk.Frame(parent, bg=BURN_GUARD["panel_2"], padx=12, pady=10)
        details.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        details.columnconfigure(1, weight=1)
        rows = [
            ("offset_detail_label", "Progression offset"),
            ("follow_detail_label", "Follow patch"),
            ("count_detail_label", "Progression bytes"),
        ]
        for row, (attr, label_text) in enumerate(rows):
            self.burn_label(
                details,
                label_text,
                bg=BURN_GUARD["panel_2"],
                fg=BURN_GUARD["muted"],
                font=("Segoe UI", 8, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=3)
            value = self.burn_label(
                details,
                "",
                bg=BURN_GUARD["panel_2"],
                fg=BURN_GUARD["cream"],
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                wraplength=145,
                justify="right",
            )
            value.grid(row=row, column=1, sticky="e", pady=3)
            setattr(self, attr, value)

        self.byte_preview_label = self.burn_label(
            parent,
            "",
            fg=BURN_GUARD["gold"],
            font=("Consolas", 10, "bold"),
            wraplength=290,
            justify="left",
        )
        self.byte_preview_label.grid(row=2, column=0, sticky="ew", pady=(14, 0))

        self.patch_note = self.burn_label(
            parent,
            "Tier 5 is still the unused base game bodyguard slot, values here are written exactly like the other tiers.",
            fg=BURN_GUARD["lilac"],
            font=("Segoe UI", 8, "bold"),
            wraplength=280,
            justify="left",
        )
        self.patch_note.grid(row=3, column=0, sticky="ew", pady=(16, 0))

    def build_action_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.columnconfigure(3, weight=3)

        write_button = self.burn_button(
            parent,
            "Apply Values",
            self.write_data,
            BURN_GUARD["orange"],
            fg=BURN_GUARD["shadow"],
        )
        write_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        reload_button = self.burn_button(
            parent,
            "Reload From ELF",
            self.read_data,
            BURN_GUARD["lilac_dark"],
            fg=BURN_GUARD["cream"],
        )
        reload_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        follow_button = self.burn_button(
            parent,
            "Enable Follow Formation",
            self.update_follow,
            BURN_GUARD["red_dark"],
            fg=BURN_GUARD["cream"],
        )
        follow_button.grid(row=0, column=2, sticky="ew", padx=(0, 12))

        self.status_label = self.burn_label(
            parent,
            "",
            fg=BURN_GUARD["green"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            wraplength=520,
            justify="left",
        )
        self.status_label.grid(row=0, column=3, sticky="ew")

        mod_row = tk.Frame(parent, bg=BURN_GUARD["panel"])
        mod_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        mod_row.columnconfigure(0, weight=1)

        mod_entry = self.burn_entry(mod_row, self.modname)
        mod_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        create_button = self.burn_button(
            mod_row,
            "Create Guard Mod",
            self.create_guard_mod,
            BURN_GUARD["gold"],
            fg=BURN_GUARD["shadow"],
        )
        create_button.grid(row=0, column=1, sticky="ew")

    def draw_header(self, event=None):
        c = self.header_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("static")

        for y in range(0, h, 8):
            fill = mix(BURN_GUARD["void"], BURN_GUARD["panel_3"], y / max(h, 1) * 0.7)
            c.create_rectangle(0, y, w, y + 8, fill=fill, outline="", tags="static")

        c.create_polygon(
            0, h - 28, w * 0.34, h - 10, w, h - 36, w, h, 0, h,
            fill=BURN_GUARD["shadow"],
            outline="",
            tags="static",
        )
        c.create_line(24, h - 18, w - 24, h - 18, fill=BURN_GUARD["orange"], width=4, tags="static")
        c.create_line(24, h - 24, w - 24, h - 24, fill=BURN_GUARD["gold"], width=1, tags="static")

        c.create_text(
            34,
            40,
            text="Bodyguard Progression",
            anchor="w",
            fill=BURN_GUARD["cream"],
            font=("Segoe UI", 28, "bold"),
            tags="static",
        )
        c.create_text(
            36,
            70,
            text="Five bodyguard tiers/three bytes per tier/formation patch available",
            anchor="w",
            fill=BURN_GUARD["muted"],
            font=("Segoe UI", 10),
            tags="static",
        )

        self.draw_header_embers()

    def draw_header_embers(self):
        c = self.header_canvas
        c.delete("ember")
        w = max(c.winfo_width(), 1)
        if not self.header_embers:
            self.header_embers = [
                [0.18, 94, 2, BURN_GUARD["gold"]],
                [0.30, 101, 2, BURN_GUARD["orange"]],
                [0.42, 102, 3, BURN_GUARD["orange"]],
                [0.54, 91, 2, BURN_GUARD["gold"]],
                [0.65, 90, 2, BURN_GUARD["red"]],
                [0.74, 99, 2, BURN_GUARD["orange"]],
                [0.82, 100, 3, BURN_GUARD["gold"]],
                [0.90, 92, 2, BURN_GUARD["red"]],
            ]
        for x_factor, y, radius, color in self.header_embers:
            x = int(w * x_factor)
            c.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=color,
                outline="",
                tags="ember",
            )

    def start_header_animation(self):
        if not self.root.winfo_exists():
            return
        if self.header_embers:
            for ember in self.header_embers:
                ember[0] += 0.012
                if ember[0] > 0.92:
                    ember[0] = 0.16
                ember[1] -= 1
                if ember[1] < 82:
                    ember[1] = 104
        self.draw_header_embers()
        self.animation_job = self.root.after(110, self.start_header_animation)

    def on_destroy(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if self.animation_job is not None:
            try:
                self.root.after_cancel(self.animation_job)
            except tk.TclError:
                pass
            self.animation_job = None

    def force_upper_hex(self, event):
        """Normalize spinbox text to 2 digit uppercase hex on focus out/Enter"""
        sb = event.widget
        text = sb.get().strip()
        if not text:
            self.set_sb_hex(sb, 0)
            self.update_preview()
            return

        try:
            val = int(text, 16)
        except ValueError:
            val = 0

        self.set_sb_hex(sb, val)
        self.update_preview()

    def set_sb_hex(self, sb, value: int) -> None:
        """Set spinbox display to a 2 digit hex string like 00-FF"""
        value = max(0, min(255, int(value)))
        sb.delete(0, tk.END)
        sb.insert(0, f"{value:02X}")

    def byte_from_sb_hex(self, sb) -> int:
        """Read a hex string from spinbox and convert to 0-255 integer"""
        s = sb.get().strip()
        if not s:
            return 0
        try:
            v = int(s, 16)
        except ValueError:
            v = 0
        return 0 if v < 0 else 255 if v > 255 else v

    def validate_hex_byte(self, proposed: str) -> bool:
        """Allow empty while typing and up to 2 hex digits"""
        if proposed == "":
            return True
        if len(proposed) > 2:
            return False
        return all(ch in "0123456789abcdefABCDEF" for ch in proposed)

    def read_data(self):
        if not os.path.exists(self.elf_path):
            self.set_status(f"Hostfs ELF not found: {self.elf_path}", ok=False)
            return

        try:
            with open(self.elf_path, "rb") as f:
                f.seek(self.guard_prog_offset)
                values = f.read(GUARD_BYTE_COUNT)
                if len(values) != GUARD_BYTE_COUNT:
                    raise ValueError(f"Couldnt read {GUARD_BYTE_COUNT} bytes of guard data.")

                f.seek(self.AI_GUARD_FOLLOW)
                follow = f.read(1)
                if len(follow) != 1:
                    raise ValueError("Couldn't read the follow-formation byte.")

            self.guard_bytes = bytearray(values)
            self.follow_byte = follow[0]

            for sb, val in zip(self.spin_widgets, self.guard_bytes):
                self.set_sb_hex(sb, val)

            self.update_preview()
            self.set_status(
                f"Guard progression data loaded from hostfs ELF at 0x{self.guard_prog_offset:X}.", ok=True
            )

        except Exception as e:
            self.set_status(f"Error reading: {e}", ok=False)

    def write_data(self):
        """Apply the current spinbox values into the in-memory guard buffer"""
        if self.guard_prog_offset is None:
            self.set_status("Guard progression offset not found; cannot apply.", ok=False)
            return

        try:
            values = self.current_values()
            if len(values) != GUARD_BYTE_COUNT:
                raise ValueError(f"Expected {GUARD_BYTE_COUNT} values, got {len(values)}")

            self.guard_bytes = bytearray(values)

            self.update_preview()
            self.set_status("Guard progression data applied in memory. Use Create Guard Mod to save it.", ok=True)

        except Exception as e:
            self.set_status(f"Error applying: {e}", ok=False)

    def update_follow(self):
        self.follow_byte = self.FOLLOW_VALUE[0]
        self.update_preview()
        self.set_status("Follow formation patch staged in memory. Use Create Guard Mod to save it.", ok=True)

    def create_guard_mod(self):
        """Dump the in-memory guard progression/follow byte to a .DW2GuardMod file"""
        if self.follow_byte is None:
            self.set_status("Guard data not loaded.", ok=False)
            return

        sep = "."
        base_name = self.modname.get().split(sep, 1)[0] or "DW2Guard"
        usermodname = base_name + DW2_GUARD_MOD_EXT

        try:
            os.makedirs(MODS_DIR, exist_ok=True)
            mod_path = os.path.join(MODS_DIR, usermodname)
            with open(mod_path, "wb") as w1:
                w1.write(bytes(self.guard_bytes))
                w1.write(bytes([self.follow_byte]))
                w1.write(self.guard_prog_offset.to_bytes(4, "little"))
                w1.write(self.AI_GUARD_FOLLOW.to_bytes(4, "little"))

            self.set_status(f"Mod file '{usermodname}' created in DW2_Mods.", ok=True)
        except Exception as e:
            self.set_status(f"Error creating mod file '{usermodname}': {e}", ok=False)

    def current_values(self):
        return [self.byte_from_sb_hex(sb) for sb in self.spin_widgets]

    def update_preview(self):
        if not hasattr(self, "preview_canvas") or len(self.spin_widgets) != GUARD_BYTE_COUNT:
            return

        values = self.current_values()
        for index, value in enumerate(values):
            label = getattr(self, f"decimal_label_{index}", None)
            if label is not None:
                label.config(text=str(value))

        self.draw_byte_preview(values)
        if hasattr(self, "offset_detail_label"):
            self.offset_detail_label.config(text=f"0x{self.guard_prog_offset:X}")
            follow_text = (
                f"0x{self.AI_GUARD_FOLLOW:X} -> {self.follow_byte:02X}"
                if self.follow_byte is not None
                else f"0x{self.AI_GUARD_FOLLOW:X} -> not loaded"
            )
            self.follow_detail_label.config(text=follow_text)
            self.count_detail_label.config(text=f"{GUARD_BYTE_COUNT} bytes")
            self.byte_preview_label.config(text=" ".join(f"{value:02X}" for value in values))

    def draw_byte_preview(self, values):
        c = self.preview_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=BURN_GUARD["panel"], outline="")

        gap = 5
        box_count = max(len(values), 1)
        box_w = max(13, min(28, int((w - 24 - gap * (box_count - 1)) / box_count)))
        total_w = box_w * box_count + gap * (box_count - 1)
        x = max(12, (w - total_w) / 2)
        y = 64

        for index, value in enumerate(values):
            tier = index // FIELDS_PER_TIER
            fill = BURN_GUARD["red_dark"] if tier == 4 else BURN_GUARD["lilac_dark"]
            outline = BURN_GUARD["red"] if tier == 4 else BURN_GUARD["lilac"]
            c.create_rectangle(x, y, x + box_w, y + 34, fill=fill, outline=outline)
            c.create_text(
                x + box_w / 2,
                y + 17,
                text=f"{value:02X}",
                fill=BURN_GUARD["cream"],
                font=("Consolas", 8, "bold"),
            )
            x += box_w + gap

        c.create_text(
            w / 2,
            26,
            text="15 Byte Progression Block",
            fill=BURN_GUARD["gold"],
            font=("Segoe UI", 10, "bold"),
        )
        c.create_line(18, h - 26, w - 18, h - 26, fill=BURN_GUARD["orange"], width=3)
        c.create_line(18, h - 32, w - 18, h - 32, fill=BURN_GUARD["gold"], width=1)

    def set_status(self, text, ok=True):
        if not hasattr(self, "status_label"):
            return
        self.status_label.config(
            text=text,
            fg=BURN_GUARD["green"] if ok else BURN_GUARD["red"],
        )
