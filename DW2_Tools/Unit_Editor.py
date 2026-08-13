# DW2_Tools/Unit_Editor.py

import os
import tkinter as tk
from io import BytesIO
from tkinter import ttk
from .Utility import BACKUP_DIR, HOSTFS_ELF, ICON_DIR, MODS_DIR, TheCheck, unit_data, unit_slot_names

DW2_UNIT_MOD_EXT = ".DW2UnitMod"

SLOT_SIZE = 7
NUM_SLOTS_FIRST = 53
NUM_SLOTS_SECOND = 201
NUM_SLOTS_TOTAL = NUM_SLOTS_FIRST + NUM_SLOTS_SECOND  # 254

FIELD_DEFS = [
    ("name",      "Name",                         0),
    ("unknown",   "Unknown",                      1),
    ("model",     "Model",                        2),
    ("color",     "Color",                        3),
    ("motion",    "Weapon + Motion",              4),
    ("horse",     "Horse",                        5),
    ("itemcount", "Amount of items and heals",    6),
]

BURN_UNIT = {
    "void": "#080504",
    "coal": "#120805",
    "panel": "#1d0d08",
    "panel_2": "#2a1209",
    "panel_3": "#3b100f",
    "line": "#8d3f19",
    "line_dim": "#5a2b17",
    "cream": "#ffe8b4",
    "gold": "#ffd23c",
    "hair": "#ffdd58",
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


class UnitEditor(TheCheck):
    """
    Dynasty Warriors 2 Unit Editor
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Knuckleforge")

        self.root.configure(bg=BURN_UNIT["void"])
        self.root.minsize(980, 640)
        self.root.geometry("1080x700")
        self.root.resizable(True, True)

        self.unit_mem: BytesIO | None = None
        self.current_slot_index = 0
        self.slot_index_by_list_pos = []
        self.field_entries = {}
        self.animation_job = None
        self.header_embers = []

        load_error = None
        try:
            self.load_unit_data_in_memory()
        except Exception as exc:
            load_error = exc

        self.field_vars = {}
        for name, label, row in FIELD_DEFS:
            var = tk.IntVar()
            setattr(self, name, var)
            self.field_vars[name] = var
            var.trace_add("write", lambda *args: self.update_record_preview())

        self.modname = tk.StringVar()
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_slot_list())

        self.hex_values = [hex(i) for i in range(NUM_SLOTS_TOTAL)]
        self.selected_slot_str = tk.StringVar(self.root, self.hex_values[0])

        self.configure_ttk()
        self.build_gui()

        if load_error:
            self.set_status(f"Unit data could not load: {load_error}", ok=False)
        else:
            self.unit_display(0)
            self.refresh_slot_list(select_slot=0)
            self.set_status("Unit data loaded. Ready to edit.", ok=True)

        self.root.bind("<Destroy>", self.on_destroy, add="+")
        self.start_header_animation()

    def load_unit_data_in_memory(self):
        """
        Build a single BytesIO
        """
        os.makedirs(BACKUP_DIR, exist_ok=True)

        mem = BytesIO()
        with open(HOSTFS_ELF, "rb") as f:
            f.seek(unit_data[0])
            for _ in range(NUM_SLOTS_FIRST):
                chunk = f.read(SLOT_SIZE)
                if len(chunk) != SLOT_SIZE:
                    raise IOError(
                        f"Unexpected EOF reading unit data at 0x{unit_data[0]:X}"
                    )
                mem.write(chunk)

            f.seek(unit_data[1])
            for _ in range(NUM_SLOTS_SECOND):
                chunk = f.read(SLOT_SIZE)
                if len(chunk) != SLOT_SIZE:
                    raise IOError(
                        f"Unexpected EOF reading unit data at 0x{unit_data[1]:X}"
                    )
                mem.write(chunk)

            for a in unit_data:
                mem.write(a.to_bytes(4, "little"))

        mem.seek(0)
        self.unit_mem = mem

        backup_path = os.path.join(BACKUP_DIR, "DW2_Original.unitdata")
        if not os.path.exists(backup_path):
            with open(backup_path, "wb") as bf:
                bf.write(mem.getbuffer())

    def configure_ttk(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "BurnUnit.TCombobox",
            fieldbackground=BURN_UNIT["entry"],
            background=BURN_UNIT["red_dark"],
            foreground=BURN_UNIT["cream"],
            arrowcolor=BURN_UNIT["gold"],
            bordercolor=BURN_UNIT["line"],
            lightcolor=BURN_UNIT["line"],
            darkcolor=BURN_UNIT["line"],
            padding=(6, 4),
        )
        style.map(
            "BurnUnit.TCombobox",
            fieldbackground=[("readonly", BURN_UNIT["entry"])],
            foreground=[("readonly", BURN_UNIT["cream"])],
        )

    def build_gui(self):
        self.shell = tk.Frame(self.root, bg=BURN_UNIT["void"])
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(
            self.shell,
            height=124,
            bg=BURN_UNIT["void"],
            bd=0,
            highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self.draw_header)

        content = tk.Frame(self.shell, bg=BURN_UNIT["void"], padx=18, pady=12)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, minsize=270)
        content.columnconfigure(1, weight=1)
        content.columnconfigure(2, minsize=300)
        content.rowconfigure(0, weight=1)

        roster_panel, roster_body = self.make_panel(content, "Unit Roster", accent=BURN_UNIT["lilac"])
        roster_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.build_roster_panel(roster_body)

        fields_panel, fields_body = self.make_panel(content, "FIELD_DEFS Data", accent=BURN_UNIT["orange"])
        fields_panel.grid(row=0, column=1, sticky="nsew", padx=6)
        fields_body.columnconfigure(0, weight=1)
        fields_body.rowconfigure(1, weight=1)
        self.build_field_panel(fields_body)

        preview_panel, preview_body = self.make_panel(content, "Record Preview", accent=BURN_UNIT["red"])
        preview_panel.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        self.build_preview_panel(preview_body)

        forge_panel, forge_body = self.make_panel(self.shell, "Unit Mod Forge", accent=BURN_UNIT["gold"])
        forge_panel.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        forge_body.columnconfigure(1, weight=1)
        self.build_forge_panel(forge_body)

    def make_panel(self, parent, title, accent=None):
        accent = accent or BURN_UNIT["orange"]
        outer = tk.Frame(
            parent,
            bg=BURN_UNIT["panel"],
            highlightbackground=BURN_UNIT["line"],
            highlightcolor=BURN_UNIT["line"],
            highlightthickness=1,
        )
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=BURN_UNIT["red_dark"], height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            header,
            text=title,
            bg=BURN_UNIT["red_dark"],
            fg=BURN_UNIT["cream"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(outer, bg=BURN_UNIT["panel"], padx=12, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        return outer, body

    def burn_label(self, parent, text, **kwargs):
        bg = kwargs.pop("bg", BURN_UNIT["panel"])
        fg = kwargs.pop("fg", BURN_UNIT["cream"])
        font = kwargs.pop("font", ("Segoe UI", 9))
        label = tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)
        return label

    def burn_button(self, parent, text, command, accent=None, fg=None):
        accent = accent or BURN_UNIT["red_dark"]
        fg = fg or BURN_UNIT["cream"]
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg=fg,
            activebackground=BURN_UNIT["gold"],
            activeforeground=BURN_UNIT["shadow"],
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_UNIT["line"],
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
        )
        return button

    def burn_entry(self, parent, textvariable, width=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=BURN_UNIT["entry"],
            fg=BURN_UNIT["cream"],
            insertbackground=BURN_UNIT["gold"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BURN_UNIT["line_dim"],
            highlightcolor=BURN_UNIT["gold"],
            font=("Consolas", 10),
        )

    def build_roster_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

        self.burn_label(
            parent,
            "Character slot",
            fg=BURN_UNIT["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w")

        slot_row = tk.Frame(parent, bg=BURN_UNIT["panel"])
        slot_row.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        slot_row.columnconfigure(0, weight=1)

        self.slot_combobox = ttk.Combobox(
            slot_row,
            textvariable=self.selected_slot_str,
            values=self.hex_values,
            state="readonly",
            style="BurnUnit.TCombobox",
            width=9,
        )
        self.slot_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.slot_combobox.bind("<<ComboboxSelected>>", self.slot_selected)
        load_button = self.burn_button(
            slot_row,
            "Load",
            self.slot_selected,
            BURN_UNIT["lilac_dark"],
            fg=BURN_UNIT["cream"],
        )
        load_button.grid(row=0, column=1, sticky="ew")

        self.burn_label(
            parent,
            "Search roster",
            fg=BURN_UNIT["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=2, column=0, sticky="w")
        search = self.burn_entry(parent, self.search_var)
        search.grid(row=3, column=0, sticky="ew", pady=(4, 8))

        list_frame = tk.Frame(parent, bg=BURN_UNIT["shadow"])
        list_frame.grid(row=4, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.slot_listbox = tk.Listbox(
            list_frame,
            bg=BURN_UNIT["shadow"],
            fg=BURN_UNIT["cream"],
            selectbackground=BURN_UNIT["lilac_dark"],
            selectforeground=BURN_UNIT["cream"],
            activestyle="none",
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_UNIT["line_dim"],
            font=("Consolas", 9),
            exportselection=False,
        )
        self.slot_listbox.grid(row=0, column=0, sticky="nsew")
        self.slot_listbox.bind("<<ListboxSelect>>", self.slot_list_selected)
        scroll = tk.Scrollbar(list_frame, command=self.slot_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.slot_listbox.configure(yscrollcommand=scroll.set)

        stats = tk.Frame(parent, bg=BURN_UNIT["panel_2"], padx=10, pady=8)
        stats.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        stats.columnconfigure(0, weight=1)
        self.roster_count_label = self.burn_label(
            stats,
            f"{NUM_SLOTS_TOTAL} slots",
            bg=BURN_UNIT["panel_2"],
            fg=BURN_UNIT["gold"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.roster_count_label.grid(row=0, column=0, sticky="ew")

    def build_field_panel(self, parent):
        top_row = tk.Frame(parent, bg=BURN_UNIT["panel"])
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_row.columnconfigure(0, weight=1)
        self.selected_slot_label = self.burn_label(
            top_row,
            "Slot 0x0",
            fg=BURN_UNIT["gold"],
            font=("Segoe UI", 16, "bold"),
        )
        self.selected_slot_label.grid(row=0, column=0, sticky="w")
        self.selected_name_label = self.burn_label(
            top_row,
            "",
            fg=BURN_UNIT["lilac"],
            font=("Segoe UI", 10, "bold"),
            anchor="e",
        )
        self.selected_name_label.grid(row=0, column=1, sticky="e")

        cards = tk.Frame(parent, bg=BURN_UNIT["panel"])
        cards.grid(row=1, column=0, sticky="nsew")
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        vcmd = (self.root.register(self.validate_numeric_input), "%P")
        for index, (name, label_text, row) in enumerate(FIELD_DEFS):
            card = self.field_card(cards, name, label_text, vcmd)
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=(0, 8) if index % 2 == 0 else (8, 0),
                pady=7,
            )

        byte_panel = tk.Frame(parent, bg=BURN_UNIT["panel_2"], padx=12, pady=10)
        byte_panel.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        byte_panel.columnconfigure(1, weight=1)
        self.burn_label(
            byte_panel,
            "Record bytes",
            bg=BURN_UNIT["panel_2"],
            fg=BURN_UNIT["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.record_bytes_label = self.burn_label(
            byte_panel,
            "",
            bg=BURN_UNIT["panel_2"],
            fg=BURN_UNIT["gold"],
            font=("Consolas", 12, "bold"),
            anchor="e",
        )
        self.record_bytes_label.grid(row=0, column=1, sticky="e")

    def field_card(self, parent, name, label_text, vcmd):
        card = tk.Frame(
            parent,
            bg=BURN_UNIT["panel_2"],
            highlightbackground=BURN_UNIT["line_dim"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        card.columnconfigure(1, weight=1)
        self.burn_label(
            card,
            label_text,
            bg=BURN_UNIT["panel_2"],
            fg=BURN_UNIT["cream"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w")
        self.burn_label(
            card,
            name,
            bg=BURN_UNIT["panel_2"],
            fg=BURN_UNIT["muted"],
            font=("Segoe UI", 8),
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))

        minus = tk.Button(
            card,
            text="-",
            command=lambda field=name: self.adjust_field(field, -1),
            bg=BURN_UNIT["entry_lit"],
            fg=BURN_UNIT["cream"],
            activebackground=BURN_UNIT["red"],
            activeforeground=BURN_UNIT["cream"],
            bd=0,
            width=3,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        minus.grid(row=2, column=0, sticky="ew", padx=(0, 5))

        entry = self.burn_entry(card, self.field_vars[name], width=8)
        entry.configure(validate="key", validatecommand=vcmd)
        entry.grid(row=2, column=1, sticky="ew")
        self.field_entries[name] = entry

        plus = tk.Button(
            card,
            text="+",
            command=lambda field=name: self.adjust_field(field, 1),
            bg=BURN_UNIT["entry_lit"],
            fg=BURN_UNIT["cream"],
            activebackground=BURN_UNIT["gold"],
            activeforeground=BURN_UNIT["shadow"],
            bd=0,
            width=3,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        plus.grid(row=2, column=2, sticky="ew", padx=(5, 0))

        hex_label = self.burn_label(
            card,
            "0x00",
            bg=BURN_UNIT["panel_2"],
            fg=BURN_UNIT["lilac"],
            font=("Consolas", 10, "bold"),
            anchor="e",
        )
        hex_label.grid(row=2, column=3, sticky="e", padx=(10, 0))
        setattr(self, f"{name}_hex_label", hex_label)
        return card

    def build_preview_panel(self, parent):
        parent.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            parent,
            height=170,
            bg=BURN_UNIT["panel"],
            bd=0,
            highlightthickness=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="ew")
        self.preview_canvas.bind("<Configure>", self.draw_preview_badge)

        details = tk.Frame(parent, bg=BURN_UNIT["panel_2"], padx=12, pady=10)
        details.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        details.columnconfigure(1, weight=1)

        rows = [
            ("slot_detail_label", "Slot"),
            ("offset_detail_label", "DW2 offset"),
            ("name_detail_label", "Slot owner"),
            ("range_detail_label", "Value range"),
        ]
        for row, (attr, label_text) in enumerate(rows):
            self.burn_label(
                details,
                label_text,
                bg=BURN_UNIT["panel_2"],
                fg=BURN_UNIT["muted"],
                font=("Segoe UI", 8, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=3)
            value = self.burn_label(
                details,
                "",
                bg=BURN_UNIT["panel_2"],
                fg=BURN_UNIT["cream"],
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                wraplength=160,
                justify="right",
            )
            value.grid(row=row, column=1, sticky="e", pady=3)
            setattr(self, attr, value)

    def build_forge_panel(self, parent):
        self.burn_label(
            parent,
            "Mod name",
            fg=BURN_UNIT["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        mod_entry = self.burn_entry(parent, self.modname)
        mod_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        apply_button = self.burn_button(
            parent,
            "Apply Slot",
            self.submit_unit,
            BURN_UNIT["lilac_dark"],
            fg=BURN_UNIT["cream"],
        )
        apply_button.grid(row=0, column=2, sticky="ew", padx=(0, 8))

        create_button = self.burn_button(
            parent,
            "Create Unit Mod",
            self.create_unit_mod,
            BURN_UNIT["orange"],
            fg=BURN_UNIT["shadow"],
        )
        create_button.grid(row=0, column=3, sticky="ew")

        self.status_label = self.burn_label(
            parent,
            "",
            fg=BURN_UNIT["green"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))

    def draw_header(self, event=None):
        c = self.header_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("static")

        for y in range(0, h, 8):
            fill = mix(BURN_UNIT["void"], BURN_UNIT["panel_3"], y / max(h, 1) * 0.7)
            c.create_rectangle(0, y, w, y + 8, fill=fill, outline="", tags="static")

        c.create_polygon(
            0, h - 28, w * 0.34, h - 10, w, h - 36, w, h, 0, h,
            fill=BURN_UNIT["shadow"],
            outline="",
            tags="static",
        )
        c.create_line(24, h - 18, w - 24, h - 18, fill=BURN_UNIT["orange"], width=4, tags="static")
        c.create_line(24, h - 24, w - 24, h - 24, fill=BURN_UNIT["gold"], width=1, tags="static")

        c.create_text(
            34,
            40,
            text="Unit Editor",
            anchor="w",
            fill=BURN_UNIT["cream"],
            font=("Segoe UI", 28, "bold"),
            tags="static",
        )
        c.create_text(
            36,
            70,
            text=f"{NUM_SLOTS_TOTAL} unit slots/{SLOT_SIZE} bytes per unit",
            anchor="w",
            fill=BURN_UNIT["muted"],
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
                [0.18, 94, 2, BURN_UNIT["gold"]],
                [0.30, 101, 2, BURN_UNIT["orange"]],
                [0.42, 102, 3, BURN_UNIT["orange"]],
                [0.54, 91, 2, BURN_UNIT["gold"]],
                [0.65, 90, 2, BURN_UNIT["red"]],
                [0.74, 99, 2, BURN_UNIT["orange"]],
                [0.82, 100, 3, BURN_UNIT["gold"]],
                [0.90, 92, 2, BURN_UNIT["red"]],
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

    def draw_preview_badge(self, event=None):
        c = self.preview_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("badge")

        c.create_rectangle(0, 0, w, h, fill=BURN_UNIT["panel"], outline="", tags="badge")
        c.create_polygon(
            12, h - 18, w * 0.45, h - 6, w - 12, h - 26, w - 12, h - 10, 12, h,
            fill=BURN_UNIT["shadow"],
            outline="",
            tags="badge",
        )

        cx, cy = w / 2, 82
        c.create_oval(cx - 54, cy - 54, cx + 54, cy + 54, outline=BURN_UNIT["line"], width=2, tags="badge")
        c.create_oval(cx - 42, cy - 42, cx + 42, cy + 42, outline=BURN_UNIT["lilac"], width=1, tags="badge")
        c.create_polygon(
            cx - 44, cy + 12,
            cx - 12, cy - 42,
            cx + 36, cy - 20,
            cx + 48, cy + 22,
            cx + 4, cy + 40,
            fill=BURN_UNIT["panel_2"],
            outline=BURN_UNIT["orange"],
            tags="badge",
        )
        c.create_rectangle(cx - 22, cy - 12, cx + 28, cy + 20, fill=BURN_UNIT["orange"], outline="", tags="badge")
        c.create_rectangle(cx - 8, cy - 6, cx + 8, cy + 14, fill=BURN_UNIT["red"], outline="", tags="badge")
        c.create_line(cx - 36, cy + 34, cx + 40, cy + 34, fill=BURN_UNIT["gold"], width=5, tags="badge")

        slot = getattr(self, "current_slot_index", 0)
        c.create_text(
            cx,
            h - 24,
            text=f"SLOT {slot:03d} / {slot:#04x}",
            fill=BURN_UNIT["gold"],
            font=("Segoe UI", 10, "bold"),
            tags="badge",
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

    def get_selected_slot_index(self) -> int:
        """
        Parse the selected slot hex string into an integer index
        """
        slot_str = self.selected_slot_str.get()
        try:
            return int(slot_str, 16)
        except ValueError:
            return 0

    def slot_selected(self, event=None):
        """Update display when a new slot is selected from the combobox"""
        slot_index = self.get_selected_slot_index()
        self.unit_display(slot_index)
        self.select_slot_in_list(slot_index)

    def slot_list_selected(self, event=None):
        selection = self.slot_listbox.curselection()
        if not selection:
            return
        slot_index = self.slot_index_by_list_pos[selection[0]]
        self.selected_slot_str.set(hex(slot_index))
        self.unit_display(slot_index)

    def refresh_slot_list(self, select_slot=None):
        if not hasattr(self, "slot_listbox"):
            return
        query = self.search_var.get().strip().lower()
        current = self.current_slot_index if select_slot is None else select_slot
        self.slot_listbox.delete(0, tk.END)
        self.slot_index_by_list_pos.clear()

        for slot_index in range(NUM_SLOTS_TOTAL):
            label = self.slot_display_text(slot_index)
            if query and query not in label.lower():
                continue
            self.slot_index_by_list_pos.append(slot_index)
            self.slot_listbox.insert(tk.END, label)

        self.roster_count_label.config(text=f"{len(self.slot_index_by_list_pos)} shown")
        self.select_slot_in_list(current)

    def select_slot_in_list(self, slot_index):
        if not hasattr(self, "slot_listbox"):
            return
        try:
            list_pos = self.slot_index_by_list_pos.index(slot_index)
        except ValueError:
            return
        self.slot_listbox.selection_clear(0, tk.END)
        self.slot_listbox.selection_set(list_pos)
        self.slot_listbox.see(list_pos)

    def slot_display_text(self, slot_index):
        resolved = self.unit_slot_name(slot_index)
        return f"{slot_index:03d} {slot_index:#04x}  {resolved}"

    def unit_slot_name(self, slot_index):
        if 0 <= slot_index < len(unit_slot_names):
            return unit_slot_names[slot_index]
        return f"Slot {slot_index}"

    def unit_display(self, slot_index: int):
        """
        Read one 7 byte unit entry from in-memory buffer and populate TK vars
        """
        if self.unit_mem is None:
            self.set_status("Unit data not loaded.", ok=False)
            return

        if not (0 <= slot_index < NUM_SLOTS_TOTAL):
            self.set_status(f"Slot {slot_index} out of range (0-{NUM_SLOTS_TOTAL - 1}).", ok=False)
            return

        offset = slot_index * SLOT_SIZE
        self.unit_mem.seek(offset)
        data = self.unit_mem.read(SLOT_SIZE)
        if len(data) != SLOT_SIZE:
            self.set_status(f"Unexpected end of unit data at slot {slot_index}.", ok=False)
            return

        for index, (name, label, row) in enumerate(FIELD_DEFS):
            self.field_vars[name].set(data[index])

        self.current_slot_index = slot_index
        self.selected_slot_str.set(hex(slot_index))
        self.update_slot_header()
        self.update_record_preview()
        self.draw_preview_badge()
        self.set_status(f"Loaded slot {slot_index} at buffer offset 0x{offset:X}.", ok=True)

    def submit_unit(self):
        """
        Write current TK var values into the in-memory buffer for the selected slot
        """
        if self.unit_mem is None:
            self.set_status("Unit data not loaded.", ok=False)
            return

        try:
            slot_index = self.get_selected_slot_index()
            if not (0 <= slot_index < NUM_SLOTS_TOTAL):
                raise ValueError(f"Slot {slot_index} out of range.")

            values = []
            for name, label_text, row in FIELD_DEFS:
                value = self.field_value(name)
                if value is None:
                    raise ValueError(f"{label_text} is blank or invalid.")
                if not (0 <= value <= 255):
                    raise ValueError(f"{label_text} must be 0-255.")
                values.append(value)

            record = bytes(values)
            offset = slot_index * SLOT_SIZE
            self.unit_mem.seek(offset)
            self.unit_mem.write(record)

            self.current_slot_index = slot_index
            self.refresh_slot_list(select_slot=slot_index)
            self.update_slot_header()
            self.update_record_preview()
            self.set_status(f"Values written for slot {slot_index}.", ok=True)

        except Exception as e:
            self.set_status(f"Error with entries: {e}", ok=False)

    def field_value(self, name):
        try:
            return int(self.field_vars[name].get())
        except (ValueError, tk.TclError):
            return None

    def adjust_field(self, name, delta):
        value = self.field_value(name)
        if value is None:
            value = 0
        self.field_vars[name].set(max(0, min(255, value + delta)))

    def update_slot_header(self):
        slot = self.current_slot_index
        self.selected_slot_label.config(text=f"Slot {slot:03d}/{slot:#04x}")
        self.selected_name_label.config(text=self.unit_slot_name(slot))

    def update_record_preview(self):
        if not hasattr(self, "record_bytes_label"):
            return

        values = []
        for name, label_text, row in FIELD_DEFS:
            value = self.field_value(name)
            values.append(value)
            hex_label = getattr(self, f"{name}_hex_label", None)
            if hex_label is not None:
                hex_label.config(text="--" if value is None else f"0x{value:02X}")

        if any(value is None for value in values):
            self.record_bytes_label.config(text="-- -- -- -- -- -- --")
        else:
            self.record_bytes_label.config(text=" ".join(f"{value:02X}" for value in values))

        slot = self.current_slot_index
        self.slot_detail_label.config(text=f"{slot:03d}/{slot:#04x}")
        self.offset_detail_label.config(text=f"0x{self.dw2_offset_for_slot(slot):X}")
        self.range_detail_label.config(text="0-255 per field")

        self.name_detail_label.config(text=self.unit_slot_name(slot))

    def dw2_offset_for_slot(self, slot_index):
        if slot_index < NUM_SLOTS_FIRST:
            return unit_data[0] + slot_index * SLOT_SIZE
        return unit_data[1] + (slot_index - NUM_SLOTS_FIRST) * SLOT_SIZE

    def set_status(self, text, ok=True):
        if not hasattr(self, "status_label"):
            return
        self.status_label.config(
            text=text,
            fg=BURN_UNIT["green"] if ok else BURN_UNIT["red"],
        )

    def create_unit_mod(self):
        if self.unit_mem is None:
            self.set_status("Unit data not loaded.", ok=False)
            return

        sep = "."
        base_name = self.modname.get().split(sep, 1)[0] or "DW2Unit"
        usermodname = base_name + DW2_UNIT_MOD_EXT

        try:
            os.makedirs(MODS_DIR, exist_ok=True)
            mod_path = os.path.join(MODS_DIR, usermodname)
            data = self.unit_mem.getvalue()
            with open(mod_path, "wb") as w1:
                w1.write(data)

            self.set_status(f"Mod file '{usermodname}' created in DW2_Mods.", ok=True)
        except Exception as e:
            self.set_status(f"Error creating mod file '{usermodname}': {e}", ok=False)
