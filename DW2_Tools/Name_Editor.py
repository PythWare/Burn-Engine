import io, os
import tkinter as tk
from tkinter import ttk

from .Utility import HOSTFS_ELF, ICON_DIR, MODS_DIR


NAME_SLOT_COUNT = 146
DW2_NAME_MOD_EXT = ".DW2NameMod"
NAME_GROUP_DEFS = [
    [0x1CDC00, 64, 15, 16],
    [0x1CE000, 27, 15, 16],
    [0x1E2EB8, 41, 7, 8],
    [0x1E3000, 14, 7, 8],
]

BURN_NAME = {
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


class NameEditor:
    """DW2 name editor"""

    def __init__(self, root):
        self.root = root
        self.root.title("Ember Registry")

        self.root.configure(bg=BURN_NAME["void"])
        self.root.minsize(920, 560)
        self.root.geometry("980x620")
        self.root.resizable(True, True)

        self.name_mem: io.BytesIO | None = None
        self.name_groups = []

        self.current_offset_group = None
        self.current_offset = None
        self.current_byte_length = None
        self.slot_index_by_list_pos = []
        self.header_embers = []
        self.animation_job = None

        self.noffset1 = tk.StringVar()
        self.noffset1.trace_add("write", lambda *args: self.update_name_preview())
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_slot_list())
        self.selected_slot = tk.IntVar(self.root, value=0)
        self.modname = tk.StringVar()

        load_error = None
        try:
            self.load_name_data_in_memory()
        except Exception as exc:
            load_error = exc

        self.configure_ttk()
        self.build_gui()

        if load_error:
            self.set_status(f"Name data could not load: {load_error}", ok=False)
        else:
            self.slot_selected()
            self.refresh_slot_list(select_slot=0)

        self.root.bind("<Destroy>", self.on_destroy, add="+")
        self.start_header_animation()

    def load_name_data_in_memory(self):
        mem = io.BytesIO()
        groups = []
        with open(HOSTFS_ELF, "rb") as f:
            for base, count, byte_len, spacing in NAME_GROUP_DEFS:
                buf_start = mem.tell()
                for index in range(count):
                    f.seek(base + index * spacing)
                    chunk = f.read(spacing)
                    if len(chunk) != spacing:
                        raise IOError(
                            f"Unexpected EOF reading name data at 0x{base + index * spacing:X}"
                        )
                    mem.write(chunk)
                groups.append({
                    "base": base,
                    "count": count,
                    "byte_len": byte_len,
                    "spacing": spacing,
                    "buf_start": buf_start,
                })

        mem.seek(0)
        self.name_mem = mem
        self.name_groups = groups

    def reload_from_source(self):
        """Rebuild the in-memory name buffer from the hostfs ELF, discarding unsaved edits"""
        try:
            self.load_name_data_in_memory()
            self.slot_selected()
            self.refresh_slot_list(select_slot=int(self.selected_slot.get()))
            self.set_status("Name data reloaded from hostfs ELF.", ok=True)
        except Exception as e:
            self.set_status(f"Error reloading name data: {e}", ok=False)

    def configure_ttk(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "BurnName.TCombobox",
            fieldbackground=BURN_NAME["entry"],
            background=BURN_NAME["red_dark"],
            foreground=BURN_NAME["cream"],
            arrowcolor=BURN_NAME["gold"],
            bordercolor=BURN_NAME["line"],
            lightcolor=BURN_NAME["line"],
            darkcolor=BURN_NAME["line"],
            padding=(6, 4),
        )
        style.map(
            "BurnName.TCombobox",
            fieldbackground=[("readonly", BURN_NAME["entry"])],
            foreground=[("readonly", BURN_NAME["cream"])],
        )

    def build_gui(self):
        self.shell = tk.Frame(self.root, bg=BURN_NAME["void"])
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(
            self.shell,
            height=118,
            bg=BURN_NAME["void"],
            bd=0,
            highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self.draw_header)

        content = tk.Frame(self.shell, bg=BURN_NAME["void"], padx=18, pady=12)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, minsize=290)
        content.columnconfigure(1, weight=1)
        content.columnconfigure(2, minsize=280)
        content.rowconfigure(0, weight=1)

        roster_panel, roster_body = self.make_panel(content, "Name Slots", BURN_NAME["lilac"])
        roster_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.build_roster_panel(roster_body)

        editor_panel, editor_body = self.make_panel(content, "Name Editor", BURN_NAME["orange"])
        editor_panel.grid(row=0, column=1, sticky="nsew", padx=6)
        editor_body.columnconfigure(0, weight=1)
        self.build_editor_panel(editor_body)

        preview_panel, preview_body = self.make_panel(content, "Write Preview", BURN_NAME["red"])
        preview_panel.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        self.build_preview_panel(preview_body)

    def make_panel(self, parent, title, accent=None):
        accent = accent or BURN_NAME["orange"]
        outer = tk.Frame(
            parent,
            bg=BURN_NAME["panel"],
            highlightbackground=BURN_NAME["line"],
            highlightcolor=BURN_NAME["line"],
            highlightthickness=1,
        )
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=BURN_NAME["red_dark"], height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            header,
            text=title,
            bg=BURN_NAME["red_dark"],
            fg=BURN_NAME["cream"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(outer, bg=BURN_NAME["panel"], padx=12, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        return outer, body

    def burn_label(self, parent, text, **kwargs):
        bg = kwargs.pop("bg", BURN_NAME["panel"])
        fg = kwargs.pop("fg", BURN_NAME["cream"])
        font = kwargs.pop("font", ("Segoe UI", 9))
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)

    def burn_entry(self, parent, textvariable, width=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=BURN_NAME["entry"],
            fg=BURN_NAME["cream"],
            insertbackground=BURN_NAME["gold"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BURN_NAME["line_dim"],
            highlightcolor=BURN_NAME["gold"],
            font=("Consolas", 12),
        )

    def burn_button(self, parent, text, command, accent=None, fg=None):
        accent = accent or BURN_NAME["red_dark"]
        fg = fg or BURN_NAME["cream"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg=fg,
            activebackground=BURN_NAME["gold"],
            activeforeground=BURN_NAME["shadow"],
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_NAME["line"],
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
        )

    def build_roster_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

        self.burn_label(
            parent,
            "Search",
            fg=BURN_NAME["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w")
        search = self.burn_entry(parent, self.search_var)
        search.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        self.burn_label(
            parent,
            "Slot",
            fg=BURN_NAME["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=2, column=0, sticky="w")

        slot_row = tk.Frame(parent, bg=BURN_NAME["panel"])
        slot_row.grid(row=3, column=0, sticky="ew", pady=(4, 10))
        slot_row.columnconfigure(0, weight=1)
        self.slot_combobox = ttk.Combobox(
            slot_row,
            textvariable=self.selected_slot,
            values=list(range(NAME_SLOT_COUNT)),
            width=10,
            state="readonly",
            style="BurnName.TCombobox",
        )
        self.slot_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.slot_combobox.bind("<<ComboboxSelected>>", self.slot_selected)
        load_button = self.burn_button(slot_row, "Load", self.slot_selected, BURN_NAME["lilac_dark"])
        load_button.grid(row=0, column=1, sticky="ew")

        list_frame = tk.Frame(parent, bg=BURN_NAME["shadow"])
        list_frame.grid(row=4, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.slot_listbox = tk.Listbox(
            list_frame,
            bg=BURN_NAME["shadow"],
            fg=BURN_NAME["cream"],
            selectbackground=BURN_NAME["lilac_dark"],
            selectforeground=BURN_NAME["cream"],
            activestyle="none",
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_NAME["line_dim"],
            font=("Consolas", 9),
            exportselection=False,
        )
        self.slot_listbox.grid(row=0, column=0, sticky="nsew")
        self.slot_listbox.bind("<<ListboxSelect>>", self.slot_list_selected)
        scroll = tk.Scrollbar(list_frame, command=self.slot_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.slot_listbox.configure(yscrollcommand=scroll.set)

        footer = tk.Frame(parent, bg=BURN_NAME["panel_2"], padx=10, pady=8)
        footer.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        self.slot_count_label = self.burn_label(
            footer,
            f"{NAME_SLOT_COUNT} slots",
            bg=BURN_NAME["panel_2"],
            fg=BURN_NAME["gold"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.slot_count_label.grid(row=0, column=0, sticky="ew")

    def build_editor_panel(self, parent):
        parent.rowconfigure(4, weight=1)

        top = tk.Frame(parent, bg=BURN_NAME["panel"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        top.columnconfigure(0, weight=1)
        self.selected_slot_label = self.burn_label(
            top,
            "Slot 000",
            fg=BURN_NAME["gold"],
            font=("Segoe UI", 16, "bold"),
        )
        self.selected_slot_label.grid(row=0, column=0, sticky="w")
        self.selected_name_label = self.burn_label(
            top,
            "",
            fg=BURN_NAME["lilac"],
            font=("Segoe UI", 11, "bold"),
            anchor="e",
        )
        self.selected_name_label.grid(row=0, column=1, sticky="e")

        self.burn_label(
            parent,
            "Name text",
            fg=BURN_NAME["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=1, column=0, sticky="w")

        name_entry = self.burn_entry(parent, self.noffset1)
        name_entry.grid(row=2, column=0, sticky="ew", pady=(4, 10), ipady=5)

        meter_wrap = tk.Frame(parent, bg=BURN_NAME["panel_2"], padx=10, pady=10)
        meter_wrap.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        meter_wrap.columnconfigure(0, weight=1)
        self.length_canvas = tk.Canvas(
            meter_wrap,
            width=380,
            height=28,
            bg=BURN_NAME["entry"],
            bd=0,
            highlightthickness=0,
        )
        self.length_canvas.grid(row=0, column=0, sticky="ew")
        self.length_canvas.bind("<Configure>", lambda event: self.update_name_preview())

        action_row = tk.Frame(parent, bg=BURN_NAME["panel"])
        action_row.grid(row=4, column=0, sticky="new")
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        update_button = self.burn_button(
            action_row,
            "Update Name",
            self.update_name,
            BURN_NAME["orange"],
            fg=BURN_NAME["shadow"],
        )
        update_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        reload_button = self.burn_button(
            action_row,
            "Reload Slot",
            self.slot_selected,
            BURN_NAME["lilac_dark"],
            fg=BURN_NAME["cream"],
        )
        reload_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        mod_row = tk.Frame(parent, bg=BURN_NAME["panel"])
        mod_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        mod_row.columnconfigure(1, weight=1)
        reload_all_button = self.burn_button(
            mod_row,
            "Reload From ELF",
            self.reload_from_source,
            BURN_NAME["lilac_dark"],
            fg=BURN_NAME["cream"],
        )
        reload_all_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        mod_entry = self.burn_entry(mod_row, self.modname)
        mod_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        create_button = self.burn_button(
            mod_row,
            "Create Name Mod",
            self.create_name_mod,
            BURN_NAME["red_dark"],
            fg=BURN_NAME["cream"],
        )
        create_button.grid(row=0, column=2, sticky="ew")

        self.status_label = self.burn_label(
            parent,
            "",
            fg=BURN_NAME["green"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            wraplength=390,
            justify="left",
        )
        self.status_label.grid(row=6, column=0, sticky="ew", pady=(18, 0))

    def build_preview_panel(self, parent):
        parent.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            parent,
            height=160,
            bg=BURN_NAME["panel"],
            bd=0,
            highlightthickness=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="ew")
        self.preview_canvas.bind("<Configure>", lambda event: self.update_name_preview())

        details = tk.Frame(parent, bg=BURN_NAME["panel_2"], padx=12, pady=10)
        details.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        details.columnconfigure(1, weight=1)

        rows = [
            ("slot_detail_label", "Slot"),
            ("offset_detail_label", "DW2 offset"),
            ("limit_detail_label", "Byte limit"),
            ("written_detail_label", "Bytes used"),
        ]
        for row, (attr, label_text) in enumerate(rows):
            self.burn_label(
                details,
                label_text,
                bg=BURN_NAME["panel_2"],
                fg=BURN_NAME["muted"],
                font=("Segoe UI", 8, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=3)
            value = self.burn_label(
                details,
                "",
                bg=BURN_NAME["panel_2"],
                fg=BURN_NAME["cream"],
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
            fg=BURN_NAME["gold"],
            font=("Consolas", 10, "bold"),
            wraplength=250,
            justify="left",
        )
        self.byte_preview_label.grid(row=2, column=0, sticky="ew", pady=(14, 0))

    def draw_header(self, event=None):
        c = self.header_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("static")

        for y in range(0, h, 8):
            fill = mix(BURN_NAME["void"], BURN_NAME["panel_3"], y / max(h, 1) * 0.7)
            c.create_rectangle(0, y, w, y + 8, fill=fill, outline="", tags="static")

        c.create_polygon(
            0, h - 28, w * 0.34, h - 10, w, h - 36, w, h, 0, h,
            fill=BURN_NAME["shadow"],
            outline="",
            tags="static",
        )
        c.create_line(24, h - 18, w - 24, h - 18, fill=BURN_NAME["orange"], width=4, tags="static")
        c.create_line(24, h - 24, w - 24, h - 24, fill=BURN_NAME["gold"], width=1, tags="static")

        c.create_text(
            34,
            40,
            text="Name Editor",
            anchor="w",
            fill=BURN_NAME["cream"],
            font=("Segoe UI", 28, "bold"),
            tags="static",
        )
        c.create_text(
            36,
            70,
            text=f"{NAME_SLOT_COUNT} name slots/ASCII labels/edits staged, saved via mod file",
            anchor="w",
            fill=BURN_NAME["muted"],
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
                [0.18, 94, 2, BURN_NAME["gold"]],
                [0.30, 101, 2, BURN_NAME["orange"]],
                [0.42, 102, 3, BURN_NAME["orange"]],
                [0.54, 91, 2, BURN_NAME["gold"]],
                [0.65, 90, 2, BURN_NAME["red"]],
                [0.74, 99, 2, BURN_NAME["orange"]],
                [0.82, 100, 3, BURN_NAME["gold"]],
                [0.90, 92, 2, BURN_NAME["red"]],
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

    def slot_selected(self, event=None):
        """Update display data when a new slot is selected"""
        try:
            selected_slot_value = int(self.selected_slot.get())
        except (ValueError, tk.TclError):
            selected_slot_value = 0
            self.selected_slot.set(0)
        self.name_display(selected_slot_value)
        self.select_slot_in_list(selected_slot_value)

    def slot_list_selected(self, event=None):
        selection = self.slot_listbox.curselection()
        if not selection:
            return
        slot = self.slot_index_by_list_pos[selection[0]]
        self.selected_slot.set(slot)
        self.name_display(slot)

    def locate_slot(self, selected_slot_value):
        """Find which group owns a slot number and its index within that group"""
        running = 0
        for group in self.name_groups:
            count = group["count"]
            if running <= selected_slot_value < running + count:
                return group, selected_slot_value - running
            running += count
        return None, None

    def resolve_slot_offset(self, selected_slot_value):
        """
        Determine which offset group and in-memory buffer offset/length apply
        for the given slot
        """
        group, rel = self.locate_slot(selected_slot_value)
        if group is None:
            return None, None, None
        buf_offset = group["buf_start"] + rel * group["spacing"]
        return buf_offset, group["byte_len"], group

    def source_offset(self, selected_slot_value):
        """The slot's original hostfs ELF offset, for display purposes only."""
        group, rel = self.locate_slot(selected_slot_value)
        if group is None:
            return None
        return group["base"] + rel * group["spacing"]

    def read_name(self, selected_slot_value):
        offset, byte_length, group = self.resolve_slot_offset(selected_slot_value)
        if offset is None or self.name_mem is None:
            return None, None, None, None
        self.name_mem.seek(offset)
        name_bytes = self.name_mem.read(byte_length)
        clean_bytes = name_bytes.split(b"\x00", 1)[0]
        try:
            name_str = clean_bytes.decode("ascii", errors="ignore")
        except Exception:
            name_str = repr(name_bytes)
        return name_str, offset, byte_length, group

    def name_display(self, selected_slot_value: int):
        """Read the name for the selected slot from memory and show it"""
        name_str, offset, byte_length, group = self.read_name(selected_slot_value)
        if offset is None:
            self.set_status(f"Slot {selected_slot_value} is out of known ranges.", ok=False)
            return

        self.current_offset_group = group
        self.current_offset = self.source_offset(selected_slot_value)
        self.current_byte_length = byte_length
        self.noffset1.set(name_str)
        self.selected_slot_label.config(text=f"Slot {selected_slot_value:03d}")
        self.selected_name_label.config(text=name_str or "(blank)")
        self.update_name_preview()
        self.set_status(
            f"Loaded slot {selected_slot_value} at ELF offset 0x{self.current_offset:X}.",
            ok=True,
        )

    def refresh_slot_list(self, select_slot=None):
        if not hasattr(self, "slot_listbox"):
            return
        query = self.search_var.get().strip().lower()
        current = int(self.selected_slot.get()) if select_slot is None else select_slot

        self.slot_listbox.delete(0, tk.END)
        self.slot_index_by_list_pos.clear()

        for slot in range(NAME_SLOT_COUNT):
            try:
                name_str, offset, byte_length, group = self.read_name(slot)
            except Exception:
                name_str = "(read error)"
                byte_length = 0
            label = f"{slot:03d}  {name_str or '(blank)'}  [{byte_length}]"
            if query and query not in label.lower():
                continue
            self.slot_index_by_list_pos.append(slot)
            self.slot_listbox.insert(tk.END, label)

        self.slot_count_label.config(text=f"{len(self.slot_index_by_list_pos)} shown")
        self.select_slot_in_list(current)

    def select_slot_in_list(self, slot):
        if not hasattr(self, "slot_listbox"):
            return
        try:
            list_pos = self.slot_index_by_list_pos.index(slot)
        except ValueError:
            return
        self.slot_listbox.selection_clear(0, tk.END)
        self.slot_listbox.selection_set(list_pos)
        self.slot_listbox.see(list_pos)

    def encoded_name_bytes(self, new_name=None, byte_limit=None):
        text = self.noffset1.get() if new_name is None else new_name
        limit = self.current_byte_length if byte_limit is None else byte_limit
        if limit is None:
            return b"", b""
        text_capacity = max(limit, 0)

        try:
            raw_bytes = text.encode("ascii", errors="ignore")
        except Exception:
            raw_bytes = text.encode("utf-8", errors="ignore")

        truncated = raw_bytes[:text_capacity]
        padded = truncated.ljust(limit, b"\x00")
        return raw_bytes, padded

    def update_name_preview(self):
        if not hasattr(self, "length_canvas"):
            return

        raw_bytes, padded = self.encoded_name_bytes()
        limit = self.current_byte_length or 0
        text_capacity = max(limit, 0)
        slot_size = limit + 1 if limit else 0
        used = min(len(raw_bytes), text_capacity)
        overflow = max(0, len(raw_bytes) - text_capacity)
        preview_bytes = padded + (b"\x00" if limit else b"")

        self.draw_length_meter(used, text_capacity, overflow, slot_size)
        self.draw_byte_preview(preview_bytes, used, slot_size, terminator_index=limit)

        slot = int(self.selected_slot.get()) if hasattr(self, "selected_slot") else 0
        if hasattr(self, "slot_detail_label"):
            self.slot_detail_label.config(text=f"{slot:03d}")
            self.offset_detail_label.config(
                text="-" if self.current_offset is None else f"0x{self.current_offset:X}"
            )
            self.limit_detail_label.config(text=f"{limit} text bytes + null ({slot_size} stored)")
            used_text = f"{used}/{text_capacity}"
            if overflow:
                used_text += f" ({overflow} cut)"
            self.written_detail_label.config(text=used_text)
            self.byte_preview_label.config(text=" ".join(f"{byte:02X}" for byte in preview_bytes))

        if hasattr(self, "selected_name_label"):
            self.selected_name_label.config(text=self.noffset1.get() or "(blank)")

    def draw_length_meter(self, used, text_capacity, overflow, byte_limit):
        c = self.length_canvas
        w = max(c.winfo_width(), int(c.cget("width")), 1)
        h = max(c.winfo_height(), int(c.cget("height")), 1)
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=BURN_NAME["entry"], outline="")

        fill_w = 0 if text_capacity <= 0 else int(w * min(used, text_capacity) / text_capacity)
        fill = BURN_NAME["red"] if overflow else BURN_NAME["lilac"]
        c.create_rectangle(0, 0, fill_w, h, fill=fill, outline="")
        c.create_text(
            10,
            h / 2,
            text=f"{used}/{text_capacity} text bytes",
            anchor="w",
            fill=BURN_NAME["cream"],
            font=("Segoe UI", 9, "bold"),
        )
        c.create_text(
            w - 10,
            h / 2,
            text=f"{byte_limit} stored, terminator is 00",
            anchor="e",
            fill=BURN_NAME["cream"],
            font=("Segoe UI", 8, "bold"),
        )
        if overflow:
            c.create_text(
                w - 10,
                h - 7,
                text=f"{overflow} truncated",
                anchor="e",
                fill=BURN_NAME["cream"],
                font=("Segoe UI", 8, "bold"),
            )

    def draw_byte_preview(self, padded, used, limit, terminator_index=None):
        if not hasattr(self, "preview_canvas"):
            return
        c = self.preview_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=BURN_NAME["panel"], outline="")

        box_count = max(limit, 1)
        gap = 4
        box_w = max(16, min(28, int((w - 24 - gap * (box_count - 1)) / box_count)))
        total_w = box_w * box_count + gap * (box_count - 1)
        x = max(12, (w - total_w) / 2)
        y = 54
        for idx in range(box_count):
            byte = padded[idx] if idx < len(padded) else 0
            active = idx < used
            terminator = terminator_index is not None and idx == terminator_index
            fill = BURN_NAME["red_dark"] if terminator else BURN_NAME["lilac_dark"] if active else BURN_NAME["entry_lit"]
            outline = BURN_NAME["red"] if terminator else BURN_NAME["lilac"] if active else BURN_NAME["line_dim"]
            c.create_rectangle(x, y, x + box_w, y + 34, fill=fill, outline=outline)
            c.create_text(
                x + box_w / 2,
                y + 17,
                text=f"{byte:02X}",
                fill=BURN_NAME["cream"] if active else BURN_NAME["muted"],
                font=("Consolas", 8, "bold"),
            )
            x += box_w + gap

        c.create_text(
            w / 2,
            26,
            text=f"SLOT {int(self.selected_slot.get()):03d}",
            fill=BURN_NAME["gold"],
            font=("Segoe UI", 10, "bold"),
        )
        c.create_line(18, h - 24, w - 18, h - 24, fill=BURN_NAME["orange"], width=3)
        c.create_line(18, h - 30, w - 18, h - 30, fill=BURN_NAME["gold"], width=1)

    def update_name(self):
        """Apply the edited name into the in-memory buffer for the current slot"""
        if self.current_offset_group is None or self.name_mem is None:
            self.set_status("No valid name slot selected.", ok=False)
            return

        byte_limit = self.current_offset_group["byte_len"]
        raw_bytes, new_name_padded = self.encoded_name_bytes(byte_limit=byte_limit)

        try:
            slot = int(self.selected_slot.get())
        except (ValueError, tk.TclError):
            self.set_status("No valid name slot selected.", ok=False)
            return

        buf_offset, byte_length, group = self.resolve_slot_offset(slot)
        if buf_offset is None or group is not self.current_offset_group:
            self.set_status("Internal mismatch in name slot range.", ok=False)
            return

        try:
            self.name_mem.seek(buf_offset)
            self.name_mem.write(new_name_padded)
            self.name_mem.write(b"\x00")

            self.refresh_slot_list(select_slot=slot)
            self.update_name_preview()
            self.set_status(f"Applied name for slot {slot} in memory. Use Create Name Mod to save it.", ok=True)
        except Exception as e:
            self.set_status(f"Error applying name: {e}", ok=False)

    def create_name_mod(self):
        """Dump the current in-memory name buffer to a .DW2NameMod file"""
        if self.name_mem is None:
            self.set_status("Name data not loaded.", ok=False)
            return

        sep = "."
        base_name = self.modname.get().split(sep, 1)[0] or "DW2Name"
        usermodname = base_name + DW2_NAME_MOD_EXT

        try:
            os.makedirs(MODS_DIR, exist_ok=True)
            mod_path = os.path.join(MODS_DIR, usermodname)
            with open(mod_path, "wb") as w1:
                w1.write(self.name_mem.getvalue())
                for group in self.name_groups:
                    w1.write(group["base"].to_bytes(4, "little"))

            self.set_status(f"Mod file '{usermodname}' created in DW2_Mods.", ok=True)
        except Exception as e:
            self.set_status(f"Error creating mod file '{usermodname}': {e}", ok=False)

    def set_status(self, text, ok=True):
        if not hasattr(self, "status_label"):
            return
        self.status_label.config(
            text=text,
            fg=BURN_NAME["green"] if ok else BURN_NAME["red"],
        )
