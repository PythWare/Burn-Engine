# DW2_Tools/Item_Editor.py
import io, os
import tkinter as tk
from .Utility import HOSTFS_ELF, ICON_DIR, MODS_DIR, TheCheck, itemsoffset

DW2_ITEM_MOD_EXT = ".DW2ItemMod"

FIELD_DEFS = [
    ("hp1",    "Health Item 1",         0, 0),
    ("hp2",    "Health Item 2",         0, 1),
    ("hp3",    "Health Item 3",         0, 2),
    ("hp4",    "Health Item 4",         0, 3),

    ("arrow1", "Arrows 1",              1, 0),
    ("arrow2", "Arrows 2",              1, 1),
    ("arrow3", "Arrows 3",              1, 2),
    ("arrow4", "Arrows 4",              1, 3),

    ("s1",     "Stat increase Item 1",  2, 0),
    ("s2",     "Stat increase Item 2",  2, 1),
    ("s3",     "Stat increase Item 3",  2, 2),
    ("s4",     "Stat increase Item 4",  2, 3),

    ("s5",     "Stat increase Item 5",  3, 0),
    ("s6",     "Stat increase Item 6",  3, 1),
    ("s7",     "Stat increase Item 7",  3, 2),
    ("s8",     "Stat increase Item 8",  3, 3),
]

ITEM_RECORD_SIZE = 12
ITEM_VALUE_SIZE = 4
ITEM_COUNT = len(FIELD_DEFS)

BURN_ITEM = {
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

COLUMN_TITLES = {
    0: ("Health Drops", BURN_ITEM["green"]),
    1: ("Arrow Drops", BURN_ITEM["gold"]),
    2: ("Stat Drops A", BURN_ITEM["lilac"]),
    3: ("Stat Drops B", BURN_ITEM["red"]),
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


class ItemEditor(TheCheck):
    """
    DW2 Item Editor
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Dragonvault")

        self.root.configure(bg=BURN_ITEM["void"])
        self.root.minsize(1020, 640)
        self.root.geometry("1080x690")
        self.root.resizable(True, True)

        self.item_mem: io.BytesIO | None = None
        self.itemlist = []
        self.item_records = []
        self.field_entries = {}
        self.header_embers = []
        self.animation_job = None
        self.modname = tk.StringVar()

        self.field_vars = {}
        for name, label, col, row in FIELD_DEFS:
            var = tk.IntVar()
            setattr(self, name, var)
            self.field_vars[name] = var
            var.trace_add("write", lambda *args: self.update_preview())

        self.build_gui()
        self.item_reader()

        self.root.bind("<Destroy>", self.on_destroy, add="+")
        self.start_header_animation()

    def build_gui(self):
        self.shell = tk.Frame(self.root, bg=BURN_ITEM["void"])
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(
            self.shell,
            height=118,
            bg=BURN_ITEM["void"],
            bd=0,
            highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self.draw_header)

        content = tk.Frame(self.shell, bg=BURN_ITEM["void"], padx=18, pady=12)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, minsize=320)
        content.rowconfigure(0, weight=1)

        values_panel, values_body = self.make_panel(content, "Item Values", BURN_ITEM["orange"])
        values_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        values_body.columnconfigure(0, weight=1)
        values_body.columnconfigure(1, weight=1)
        self.build_value_grid(values_body)

        preview_panel, preview_body = self.make_panel(content, "Write Preview", BURN_ITEM["red"])
        preview_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self.build_preview_panel(preview_body)

        action_panel, action_body = self.make_panel(self.shell, "Item Table Control", BURN_ITEM["lilac"])
        action_panel.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        self.build_action_panel(action_body)

    def make_panel(self, parent, title, accent=None):
        accent = accent or BURN_ITEM["orange"]
        outer = tk.Frame(
            parent,
            bg=BURN_ITEM["panel"],
            highlightbackground=BURN_ITEM["line"],
            highlightcolor=BURN_ITEM["line"],
            highlightthickness=1,
        )
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=BURN_ITEM["red_dark"], height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            header,
            text=title,
            bg=BURN_ITEM["red_dark"],
            fg=BURN_ITEM["cream"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(outer, bg=BURN_ITEM["panel"], padx=12, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        return outer, body

    def burn_label(self, parent, text, **kwargs):
        bg = kwargs.pop("bg", BURN_ITEM["panel"])
        fg = kwargs.pop("fg", BURN_ITEM["cream"])
        font = kwargs.pop("font", ("Segoe UI", 9))
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)

    def burn_entry(self, parent, textvariable, width=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=BURN_ITEM["entry"],
            fg=BURN_ITEM["cream"],
            insertbackground=BURN_ITEM["gold"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BURN_ITEM["line_dim"],
            highlightcolor=BURN_ITEM["gold"],
            font=("Consolas", 10),
        )

    def burn_button(self, parent, text, command, accent=None, fg=None):
        accent = accent or BURN_ITEM["red_dark"]
        fg = fg or BURN_ITEM["cream"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg=fg,
            activebackground=BURN_ITEM["gold"],
            activeforeground=BURN_ITEM["shadow"],
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_ITEM["line"],
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
        )

    def build_value_grid(self, parent):
        groups = {}
        for col in range(4):
            title, accent = COLUMN_TITLES[col]
            group = tk.Frame(
                parent,
                bg=BURN_ITEM["panel_2"],
                highlightbackground=BURN_ITEM["line_dim"],
                highlightthickness=1,
                padx=10,
                pady=10,
            )
            group.grid(row=col // 2, column=col % 2, sticky="nsew", padx=7, pady=7)
            group.columnconfigure(0, weight=1)
            parent.rowconfigure(col // 2, weight=1)
            self.burn_label(
                group,
                title,
                bg=BURN_ITEM["panel_2"],
                fg=accent,
                font=("Segoe UI", 11, "bold"),
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))
            groups[col] = group

        vcmd = (self.root.register(self.validate_numeric_input), "%P")
        for name, label_text, col, row in FIELD_DEFS:
            self.field_row(groups[col], name, label_text, row + 1, vcmd)

    def field_row(self, parent, name, label_text, row, vcmd):
        wrap = tk.Frame(parent, bg=BURN_ITEM["panel_2"])
        wrap.grid(row=row, column=0, sticky="ew", pady=5)
        wrap.columnconfigure(1, weight=1)

        self.burn_label(
            wrap,
            label_text,
            bg=BURN_ITEM["panel_2"],
            fg=BURN_ITEM["cream"],
            font=("Segoe UI", 9, "bold"),
            width=18,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        entry = self.burn_entry(wrap, self.field_vars[name], width=10)
        entry.configure(validate="key", validatecommand=vcmd)
        entry.grid(row=0, column=1, sticky="ew")
        self.field_entries[name] = entry

        stepper = tk.Frame(wrap, bg=BURN_ITEM["panel_2"])
        stepper.grid(row=0, column=2, sticky="e", padx=(8, 0))
        minus = tk.Button(
            stepper,
            text="-",
            command=lambda field=name: self.adjust_field(field, -1),
            bg=BURN_ITEM["entry_lit"],
            fg=BURN_ITEM["cream"],
            activebackground=BURN_ITEM["red"],
            activeforeground=BURN_ITEM["cream"],
            bd=0,
            width=3,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        minus.grid(row=0, column=0, padx=(0, 3))
        plus = tk.Button(
            stepper,
            text="+",
            command=lambda field=name: self.adjust_field(field, 1),
            bg=BURN_ITEM["entry_lit"],
            fg=BURN_ITEM["cream"],
            activebackground=BURN_ITEM["gold"],
            activeforeground=BURN_ITEM["shadow"],
            bd=0,
            width=3,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        plus.grid(row=0, column=1)

        hex_label = self.burn_label(
            wrap,
            "0x00000000",
            bg=BURN_ITEM["panel_2"],
            fg=BURN_ITEM["lilac"],
            font=("Consolas", 8, "bold"),
            anchor="e",
        )
        hex_label.grid(row=1, column=1, columnspan=2, sticky="e", pady=(3, 0))
        setattr(self, f"{name}_hex_label", hex_label)

    def build_preview_panel(self, parent):
        parent.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            parent,
            height=210,
            bg=BURN_ITEM["panel"],
            bd=0,
            highlightthickness=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="ew")
        self.preview_canvas.bind("<Configure>", lambda event: self.update_preview())

        details = tk.Frame(parent, bg=BURN_ITEM["panel_2"], padx=12, pady=10)
        details.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        details.columnconfigure(1, weight=1)
        rows = [
            ("offset_detail_label", "Table offset"),
            ("count_detail_label", "Records"),
            ("record_detail_label", "Record format"),
            ("range_detail_label", "Value range"),
        ]
        for row, (attr, label_text) in enumerate(rows):
            self.burn_label(
                details,
                label_text,
                bg=BURN_ITEM["panel_2"],
                fg=BURN_ITEM["muted"],
                font=("Segoe UI", 8, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=3)
            value = self.burn_label(
                details,
                "",
                bg=BURN_ITEM["panel_2"],
                fg=BURN_ITEM["cream"],
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                wraplength=150,
                justify="right",
            )
            value.grid(row=row, column=1, sticky="e", pady=3)
            setattr(self, attr, value)

        self.byte_preview_label = self.burn_label(
            parent,
            "",
            fg=BURN_ITEM["gold"],
            font=("Consolas", 9, "bold"),
            wraplength=290,
            justify="left",
        )
        self.byte_preview_label.grid(row=2, column=0, sticky="ew", pady=(14, 0))

    def build_action_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, minsize=160)
        parent.columnconfigure(3, weight=1)
        parent.columnconfigure(4, weight=3)

        write_button = self.burn_button(
            parent,
            "Apply Values",
            self.item_writer,
            BURN_ITEM["orange"],
            fg=BURN_ITEM["shadow"],
        )
        write_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        reload_button = self.burn_button(
            parent,
            "Reload From ELF",
            self.item_reader,
            BURN_ITEM["lilac_dark"],
            fg=BURN_ITEM["cream"],
        )
        reload_button.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        mod_entry = self.burn_entry(parent, self.modname)
        mod_entry.grid(row=0, column=2, sticky="ew", padx=(0, 8))

        create_button = self.burn_button(
            parent,
            "Create Item Mod",
            self.create_item_mod,
            BURN_ITEM["red_dark"],
            fg=BURN_ITEM["cream"],
        )
        create_button.grid(row=0, column=3, sticky="ew", padx=(0, 12))

        self.status_label = self.burn_label(
            parent,
            "",
            fg=BURN_ITEM["green"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            wraplength=520,
            justify="left",
        )
        self.status_label.grid(row=0, column=4, sticky="ew")

    def draw_header(self, event=None):
        c = self.header_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("static")

        for y in range(0, h, 8):
            fill = mix(BURN_ITEM["void"], BURN_ITEM["panel_3"], y / max(h, 1) * 0.7)
            c.create_rectangle(0, y, w, y + 8, fill=fill, outline="", tags="static")

        c.create_polygon(
            0, h - 28, w * 0.34, h - 10, w, h - 36, w, h, 0, h,
            fill=BURN_ITEM["shadow"],
            outline="",
            tags="static",
        )
        c.create_line(24, h - 18, w - 24, h - 18, fill=BURN_ITEM["orange"], width=4, tags="static")
        c.create_line(24, h - 24, w - 24, h - 24, fill=BURN_ITEM["gold"], width=1, tags="static")

        c.create_text(
            34,
            40,
            text="Item Editor",
            anchor="w",
            fill=BURN_ITEM["cream"],
            font=("Segoe UI", 28, "bold"),
            tags="static",
        )
        c.create_text(
            36,
            70,
            text=f"{ITEM_COUNT} item values/4 bytes each/IDs and effects preserved",
            anchor="w",
            fill=BURN_ITEM["muted"],
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
                [0.18, 94, 2, BURN_ITEM["gold"]],
                [0.30, 101, 2, BURN_ITEM["orange"]],
                [0.42, 102, 3, BURN_ITEM["orange"]],
                [0.54, 91, 2, BURN_ITEM["gold"]],
                [0.65, 90, 2, BURN_ITEM["red"]],
                [0.74, 99, 2, BURN_ITEM["orange"]],
                [0.82, 100, 3, BURN_ITEM["gold"]],
                [0.90, 92, 2, BURN_ITEM["red"]],
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

    def item_reader(self):
        self.itemlist.clear()
        self.item_records.clear()

        try:
            record_bytes = ITEM_COUNT * ITEM_RECORD_SIZE
            with open(HOSTFS_ELF, "rb") as f1:
                f1.seek(itemsoffset)
                data = f1.read(record_bytes)
            if len(data) != record_bytes:
                raise IOError("Unexpected EOF while reading item records.")

            mem = io.BytesIO(data)
            for _ in range(ITEM_COUNT):
                item_id = mem.read(4)
                value_bytes = mem.read(4)
                itemeffect = mem.read(4)
                itemvalue = int.from_bytes(value_bytes, "little")
                self.itemlist.append(itemvalue)
                self.item_records.append((item_id, value_bytes, itemeffect))
            self.item_mem = mem

            for i, (name, label, col, row) in enumerate(FIELD_DEFS):
                self.field_vars[name].set(self.itemlist[i])

            self.update_preview()
            self.set_status("Item values loaded from hostfs ELF.", ok=True)

        except Exception as e:
            self.set_status(f"Error reading item values: {e}", ok=False)

    def item_writer(self):
        if self.item_mem is None:
            self.set_status("Item data not loaded.", ok=False)
            return

        try:
            values = self.collect_values()
            if len(values) != ITEM_COUNT:
                raise ValueError(f"Expected {ITEM_COUNT} values to write, got {len(values)}.")

            for index, value in enumerate(values):
                value_bytes = value.to_bytes(ITEM_VALUE_SIZE, "little")
                self.item_mem.seek(index * ITEM_RECORD_SIZE + 4)
                self.item_mem.write(value_bytes)
                self.itemlist[index] = value
                item_id, old_value, item_effect = self.item_records[index]
                self.item_records[index] = (item_id, value_bytes, item_effect)

            self.update_preview()
            self.set_status("Values applied in memory. Use Create Item Mod to save them.", ok=True)

        except Exception as e:
            self.set_status(f"Error with entries: {e}", ok=False)

    def create_item_mod(self):
        """Dump the current in-memory item records to a .DW2ItemMod file"""
        if self.item_mem is None:
            self.set_status("Item data not loaded.", ok=False)
            return

        sep = "."
        base_name = self.modname.get().split(sep, 1)[0] or "DW2Item"
        usermodname = base_name + DW2_ITEM_MOD_EXT

        try:
            os.makedirs(MODS_DIR, exist_ok=True)
            mod_path = os.path.join(MODS_DIR, usermodname)
            with open(mod_path, "wb") as w1:
                w1.write(self.item_mem.getvalue())

            self.set_status(f"Mod file '{usermodname}' created in DW2_Mods.", ok=True)
        except Exception as e:
            self.set_status(f"Error creating mod file '{usermodname}': {e}", ok=False)

    def collect_values(self):
        values = []
        for name, label, col, row in FIELD_DEFS:
            value = self.field_value(name)
            if value is None:
                raise ValueError(f"{label} is blank or invalid.")
            if not (0 <= value <= 0xFFFFFFFF):
                raise ValueError(f"{label} must fit in 4 bytes.")
            values.append(value)
        return values

    def field_value(self, name):
        try:
            return int(self.field_vars[name].get())
        except (ValueError, tk.TclError):
            return None

    def adjust_field(self, name, delta):
        value = self.field_value(name)
        if value is None:
            value = 0
        self.field_vars[name].set(max(0, min(0xFFFFFFFF, value + delta)))

    def update_preview(self):
        if not hasattr(self, "preview_canvas"):
            return

        values = []
        for name, label, col, row in FIELD_DEFS:
            value = self.field_value(name)
            values.append(value)
            hex_label = getattr(self, f"{name}_hex_label", None)
            if hex_label is not None:
                hex_label.config(text="--" if value is None else f"0x{value:08X}")

        self.draw_preview_chart(values)

        if hasattr(self, "offset_detail_label"):
            self.offset_detail_label.config(text=f"0x{itemsoffset:X}")
            self.count_detail_label.config(text=f"{ITEM_COUNT} records")
            self.record_detail_label.config(text="ID/Value/Effect")
            self.range_detail_label.config(text="0-4294967295")

            byte_parts = []
            for value in values[:8]:
                if value is None:
                    byte_parts.append("-- -- -- --")
                else:
                    byte_parts.append(" ".join(f"{byte:02X}" for byte in value.to_bytes(4, "little")))
            self.byte_preview_label.config(text=" | ".join(byte_parts))

    def draw_preview_chart(self, values):
        c = self.preview_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=BURN_ITEM["panel"], outline="")

        valid_values = [value for value in values if value is not None]
        max_value = max(valid_values) if valid_values else 1
        max_value = max(max_value, 1)
        left = 22
        top = 34
        bar_area_h = h - 78
        gap = 4
        bar_w = max(6, int((w - left * 2 - gap * (ITEM_COUNT - 1)) / ITEM_COUNT))

        for index, value in enumerate(values):
            x1 = left + index * (bar_w + gap)
            x2 = x1 + bar_w
            if value is None:
                bar_h = 0
                fill = BURN_ITEM["red"]
            else:
                bar_h = int(bar_area_h * value / max_value)
                name, label, col, row = FIELD_DEFS[index]
                fill = COLUMN_TITLES[col][1]
            y2 = top + bar_area_h
            y1 = y2 - bar_h
            c.create_rectangle(x1, top, x2, y2, fill=BURN_ITEM["entry_lit"], outline="")
            c.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")

        c.create_text(
            w / 2,
            18,
            text="CURRENT VALUE SHAPE",
            fill=BURN_ITEM["gold"],
            font=("Segoe UI", 10, "bold"),
        )
        c.create_line(18, h - 26, w - 18, h - 26, fill=BURN_ITEM["orange"], width=3)
        c.create_line(18, h - 32, w - 18, h - 32, fill=BURN_ITEM["gold"], width=1)

    def set_status(self, text, ok=True):
        if not hasattr(self, "status_label"):
            return
        self.status_label.config(
            text=text,
            fg=BURN_ITEM["green"] if ok else BURN_ITEM["red"],
        )
