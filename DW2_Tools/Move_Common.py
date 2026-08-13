# DW2_Tools/Move_Common.py
"""
Shared scaffolding for the graph-based move editors
"""

import io, os
import tkinter as tk
from tkinter import ttk
from collections import defaultdict

from .Utility import LINKDATA_DIR, MODS_DIR

CHARA_DIR = os.path.join(LINKDATA_DIR, "CHARA")

CHARA_LABELS = {
    "CHOUUN": "Zhao Yun", "KANU": "Guan Yu", "CHOUHI": "Zhang Fei",
    "KAKOUTO": "Xiahou Dun", "TENI": "Dian Wei", "KYOCHO": "Xu Zhu",
    "SHUUYU": "Zhou Yu", "RIKUSON": "Lu Xun", "TAISHIJ": "Taishi Ci",
    "CHOUSEN": "Diao Chan", "KOUMEI": "Zhuge Liang", "SOUSOU": "Cao Cao",
    "RYOFU": "Lu Bu", "SHOUKOU": "Sun Shang Xiang",
}

BURN_MV = {
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
    "graph_bg": "#0f0805",
    "edge_dim": "#3a2415",
    "edge_in": "#ff8a1e",
    "edge_out": "#ffd23c",
    "node_root": "#6e4c83",
    "node_basic": "#3b2415",
    "node_dim": "#150d08",
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


def char_label(basename):
    key = basename.upper()
    friendly = CHARA_LABELS.get(key)
    return f"{basename}  ({friendly})" if friendly else basename

NODE_W = 150
NODE_H = 48
COL_W = 214
ROW_H = 66
MARGIN = 40


class MoveGraphEditor:
    """
    Base class for the ATK/MOV graph editors
    """

    EXT = ".ATK"
    MOD_EXT = ".DW2AtkMod"
    RECORD_SIZE = 32
    FIXED_COUNT = None
    WINDOW_TITLE = "Move Editor"
    HEADER_TITLE = "Move Editor"
    HEADER_SUB = ""
    GRAPH_TITLE = "Graph"
    DETAIL_TITLE = "Node Detail"
    FIELD_SPECS = []
    NEUTRAL_LABEL = "Neutral"

    ZOOM_MIN = 0.12
    ZOOM_MAX = 2.6

    def __init__(self, root):
        self.root = root
        self.root.title(self.WINDOW_TITLE)
        self.root.configure(bg=BURN_MV["void"])
        self.root.minsize(1120, 700)
        self.root.geometry("1280x800")
        self.root.resizable(True, True)

        self.mem = None
        self.records = []
        self.count = 0
        self.selected = None
        self.focus_id = None

        self.node_ids = set()
        self.edges = []
        self.world = {}
        self.children = defaultdict(list)
        self.parents = defaultdict(list)
        self.screen_boxes = {}

        self.zoom = 1.0
        self.ox = 0.0
        self.oy = 0.0
        self.pan_last = None
        self.needs_fit = False

        self.field_vars = {}
        self.flag_state = {}
        self.flag_checks = {}
        self.flag_hex_vars = {}
        self.header_embers = []
        self.animation_job = None

        self.char_var = tk.StringVar()
        self.modname = tk.StringVar()

        self.build_gui()
        self.discover_chars()

        self.root.bind("<Destroy>", self.on_destroy, add="+")
        self.start_header_animation()

    def build_gui(self):
        self.shell = tk.Frame(self.root, bg=BURN_MV["void"])
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(2, weight=1)

        self.header_canvas = tk.Canvas(
            self.shell, height=112, bg=BURN_MV["void"], bd=0, highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self.draw_header)

        self.build_control_row()

        content = tk.Frame(self.shell, bg=BURN_MV["void"], padx=18, pady=8)
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, minsize=372)
        content.rowconfigure(0, weight=1)

        graph_panel, graph_body = self.make_panel(content, self.GRAPH_TITLE, BURN_MV["orange"])
        graph_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        graph_body.columnconfigure(0, weight=1)
        graph_body.rowconfigure(1, weight=1)
        self.build_graph_canvas(graph_body)

        detail_panel, detail_body = self.make_panel(content, self.DETAIL_TITLE, BURN_MV["red"])
        detail_panel.grid(row=0, column=1, sticky="nsew")
        detail_body.columnconfigure(0, weight=1)
        detail_body.rowconfigure(1, weight=1)
        self.build_detail(detail_body)

    def build_control_row(self):
        bar_panel, bar = self.make_panel(self.shell, "Character & Mod", BURN_MV["lilac"])
        bar_panel.grid(row=1, column=0, sticky="ew", padx=18, pady=(10, 0))
        bar.columnconfigure(5, weight=1)

        self.burn_label(bar, "Character", fg=BURN_MV["muted"], font=("Segoe UI", 8, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 6))

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Burn.TCombobox",
            fieldbackground=BURN_MV["entry"], background=BURN_MV["red_dark"],
            foreground=BURN_MV["cream"], arrowcolor=BURN_MV["gold"], bordercolor=BURN_MV["line"],
        )
        self.char_combo = ttk.Combobox(
            bar, textvariable=self.char_var, state="readonly", width=26, style="Burn.TCombobox",
        )
        self.char_combo.grid(row=0, column=1, sticky="w", padx=(0, 10), ipady=2)
        self.char_combo.bind("<<ComboboxSelected>>", lambda e: self.load_character())

        self.burn_button(bar, "Reload", self.load_character, BURN_MV["lilac_dark"]).grid(
            row=0, column=2, sticky="w", padx=(0, 16))

        self.burn_label(bar, "Mod name", fg=BURN_MV["muted"], font=("Segoe UI", 8, "bold")).grid(
            row=0, column=3, sticky="e", padx=(0, 6))
        self.burn_entry(bar, self.modname, width=18).grid(row=0, column=4, sticky="w", padx=(0, 10))
        self.burn_button(bar, "Create Mod", self.create_mod, BURN_MV["red_dark"]).grid(
            row=0, column=5, sticky="w")

    def make_panel(self, parent, title, accent=None):
        accent = accent or BURN_MV["orange"]
        outer = tk.Frame(
            parent, bg=BURN_MV["panel"],
            highlightbackground=BURN_MV["line"], highlightcolor=BURN_MV["line"], highlightthickness=1,
        )
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)
        header = tk.Frame(outer, bg=BURN_MV["red_dark"], height=34)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(header, text=title, bg=BURN_MV["red_dark"], fg=BURN_MV["cream"],
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=10)
        body = tk.Frame(outer, bg=BURN_MV["panel"], padx=12, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        return outer, body

    def burn_label(self, parent, text, **kwargs):
        bg = kwargs.pop("bg", BURN_MV["panel"])
        fg = kwargs.pop("fg", BURN_MV["cream"])
        font = kwargs.pop("font", ("Segoe UI", 9))
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)

    def burn_entry(self, parent, textvariable, width=None):
        return tk.Entry(
            parent, textvariable=textvariable, width=width,
            bg=BURN_MV["entry"], fg=BURN_MV["cream"], insertbackground=BURN_MV["gold"],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=BURN_MV["line_dim"], highlightcolor=BURN_MV["gold"],
            font=("Consolas", 10),
        )

    def burn_button(self, parent, text, command, accent=None, fg=None):
        accent = accent or BURN_MV["red_dark"]
        fg = fg or BURN_MV["cream"]
        return tk.Button(
            parent, text=text, command=command, bg=accent, fg=fg,
            activebackground=BURN_MV["gold"], activeforeground=BURN_MV["shadow"],
            bd=0, highlightthickness=1, highlightbackground=BURN_MV["line"], relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"), padx=12, pady=7, cursor="hand2",
        )

    def build_graph_canvas(self, parent):
        toolbar = tk.Frame(parent, bg=BURN_MV["panel"])
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        for text, cmd in (("–  Zoom", lambda: self.zoom_step(1 / 1.25)),
                          ("+  Zoom", lambda: self.zoom_step(1.25)),
                          ("Fit", self.fit_view)):
            self.burn_button(toolbar, text, cmd, BURN_MV["lilac_dark"]).pack(side=tk.LEFT, padx=(0, 6))
        self.zoom_label = self.burn_label(toolbar, "100%", fg=BURN_MV["muted"], font=("Consolas", 9, "bold"))
        self.zoom_label.pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(toolbar, text="right-drag pan • wheel zoom • left-click focus",
                 bg=BURN_MV["panel"], fg=BURN_MV["muted"], font=("Segoe UI", 8)).pack(side=tk.RIGHT)

        self.graph = tk.Canvas(parent, bg=BURN_MV["graph_bg"], bd=0, highlightthickness=0)
        self.graph.grid(row=1, column=0, sticky="nsew")

        self.graph.bind("<Button-1>", self.on_left_click)
        self.graph.bind("<ButtonPress-3>", self.on_pan_start)
        self.graph.bind("<B3-Motion>", self.on_pan_move)
        self.graph.bind("<ButtonPress-2>", self.on_pan_start)
        self.graph.bind("<B2-Motion>", self.on_pan_move)
        self.graph.bind("<MouseWheel>", self.on_wheel_zoom)
        self.graph.bind("<Configure>", self.on_graph_configure)

    def build_detail(self, parent):
        self.detail_head = self.burn_label(
            parent, "No node selected", fg=BURN_MV["gold"], font=("Segoe UI", 13, "bold"),
            wraplength=340, justify="left",
        )
        self.detail_head.grid(row=0, column=0, sticky="w", pady=(0, 8))

        wrap = tk.Frame(parent, bg=BURN_MV["panel"])
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.form_canvas = tk.Canvas(wrap, bg=BURN_MV["panel"], bd=0, highlightthickness=0)
        self.form_canvas.grid(row=0, column=0, sticky="nsew")
        vsb = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.form_canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.form_canvas.configure(yscrollcommand=vsb.set)

        inner = tk.Frame(self.form_canvas, bg=BURN_MV["panel"])
        inner.columnconfigure(1, weight=1)
        self.form_window = self.form_canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all")))
        self.form_canvas.bind("<Configure>", lambda e: self.form_canvas.itemconfigure(self.form_window, width=e.width))

        row = 0
        for spec in self.FIELD_SPECS:
            if spec.get("kind") == "flags":
                row = self.build_flag_field(inner, row, spec)
            else:
                row = self.build_int_field(inner, row, spec)

        self.bind_wheel(inner)
        self.bind_wheel(self.form_canvas)

        self.apply_button = self.burn_button(
            parent, "Apply To Node", self.apply_detail, BURN_MV["orange"], fg=BURN_MV["shadow"])
        self.apply_button.grid(row=2, column=0, sticky="ew", pady=(10, 4))

        self.status_label = self.burn_label(
            parent, "", fg=BURN_MV["green"], font=("Segoe UI", 9, "bold"),
            anchor="w", wraplength=350, justify="left",
        )
        self.status_label.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    def bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self.on_form_wheel)
        for child in widget.winfo_children():
            self.bind_wheel(child)

    def on_form_wheel(self, event):
        self.form_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def build_int_field(self, parent, row, spec):
        self.burn_label(parent, spec["label"], fg=BURN_MV["cream"], font=("Segoe UI", 9, "bold"),
                         anchor="w").grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        var = tk.StringVar()
        self.field_vars[spec["key"]] = var
        entry = self.burn_entry(parent, var, width=12)
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        note = spec.get("note")
        if note:
            self.burn_label(parent, note, fg=BURN_MV["muted"], font=("Segoe UI", 8),
                             anchor="w", wraplength=330, justify="left").grid(
                row=row + 1, column=0, columnspan=2, sticky="w")
            return row + 2
        return row + 1

    def build_flag_field(self, parent, row, spec):
        key = spec["key"]
        group = tk.Frame(parent, bg=BURN_MV["panel_2"], padx=8, pady=6,
                         highlightbackground=BURN_MV["line_dim"], highlightthickness=1)
        group.grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
        group.columnconfigure(0, weight=1)
        head = tk.Frame(group, bg=BURN_MV["panel_2"])
        head.grid(row=0, column=0, sticky="ew")
        self.burn_label(head, spec["label"], bg=BURN_MV["panel_2"], fg=BURN_MV["gold"],
                         font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        hexvar = tk.StringVar(value="0x0")
        hexent = self.burn_entry(head, hexvar, width=10)
        hexent.pack(side=tk.RIGHT)
        hexent.bind("<Return>", lambda e, k=key: self.commit_flag_hex(k))
        hexent.bind("<FocusOut>", lambda e, k=key: self.commit_flag_hex(k))
        self.flag_hex_vars[key] = hexvar

        self.flag_checks[key] = {}
        self.flag_state[key] = 0
        r = 1
        for bit, name in spec["bits"]:
            v = tk.IntVar()
            self.flag_checks[key][bit] = v
            cb = tk.Checkbutton(
                group, text=f"bit{bit}  {name}", variable=v,
                command=lambda k=key, b=bit: self.toggle_flag_bit(k, b),
                bg=BURN_MV["panel_2"], fg=BURN_MV["cream"], selectcolor=BURN_MV["red_dark"],
                activebackground=BURN_MV["panel_2"], activeforeground=BURN_MV["gold"],
                anchor="w", font=("Segoe UI", 8), bd=0, highlightthickness=0,
            )
            cb.grid(row=r, column=0, sticky="w")
            r += 1
        return row + 1

    def toggle_flag_bit(self, key, bit):
        cur = self.flag_state.get(key, 0)
        if self.flag_checks[key][bit].get():
            cur |= (1 << bit)
        else:
            cur &= ~(1 << bit)
        self.flag_state[key] = cur
        self.refresh_flag_hex(key)

    def refresh_flag_hex(self, key):
        var = self.flag_hex_vars.get(key)
        if var is not None:
            var.set(f"0x{self.flag_state.get(key, 0):X}")

    def commit_flag_hex(self, key):
        """Parse the typed raw word back into flag_state and re-sync the checkboxes"""
        var = self.flag_hex_vars.get(key)
        if var is None:
            return
        spec = next((s for s in self.FIELD_SPECS if s["key"] == key), None)
        width = (spec["size"] * 8) if spec else 32
        try:
            val = int(var.get().strip(), 0) & ((1 << width) - 1)
        except ValueError:
            self.refresh_flag_hex(key)
            self.set_status("Flags must be a number, e.g. 0x4020.", ok=False)
            return
        self.flag_state[key] = val
        for bit, v in self.flag_checks[key].items():
            v.set(1 if (val >> bit) & 1 else 0)
        self.refresh_flag_hex(key)

    def discover_chars(self):
        try:
            files = sorted(f for f in os.listdir(CHARA_DIR) if f.upper().endswith(self.EXT))
        except OSError:
            files = []
        self.char_files = files
        labels = [char_label(os.path.splitext(f)[0]) for f in files]
        self.char_combo.configure(values=labels)
        if labels:
            self.char_combo.current(0)
            self.load_character()
        else:
            self.set_status(f"No {self.EXT} files found in {CHARA_DIR}.", ok=False)

    def current_file(self):
        idx = self.char_combo.current()
        if idx < 0 or idx >= len(self.char_files):
            return None
        return self.char_files[idx]

    def load_character(self):
        fname = self.current_file()
        if not fname:
            return
        path = os.path.join(CHARA_DIR, fname)
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.mem = io.BytesIO(data)
            self.count = self.FIXED_COUNT or (len(data) // self.RECORD_SIZE)
            self.records = [
                bytearray(data[i * self.RECORD_SIZE:(i + 1) * self.RECORD_SIZE])
                for i in range(self.count)
            ]
            self.selected = None
            self.focus_id = None
            self.clear_detail()
            self.rebuild_graph(refit=True)
            self.set_status(f"Loaded {fname} ({self.count} records).", ok=True)
        except Exception as e:
            self.set_status(f"Error reading {fname}: {e}", ok=False)

    def rebuild_graph(self, refit=False):
        self.node_ids, self.edges = self.collect_graph()
        self.children = defaultdict(list)
        self.parents = defaultdict(list)
        for s, d in self.edges:
            if s == d:
                continue
            self.children[s].append(d)
            self.parents[d].append(s)
        self.world = self.layout(self.node_ids, self.edges)
        if refit:
            self.needs_fit = True
            self.graph.after(40, self.maybe_fit)
        self.draw_graph()

    def on_graph_configure(self, event=None):
        if self.needs_fit and self.graph.winfo_width() > 60:
            self.fit_view()
        else:
            self.draw_graph()

    def maybe_fit(self):
        if self.needs_fit and self.graph.winfo_width() > 60:
            self.fit_view()

    def collect_graph(self):
        node_ids = set()
        edges = []
        for i, rec in enumerate(self.records):
            if not self.is_used(i, rec):
                continue
            node_ids.add(i)
            for src in self.edges_for(i, rec):
                node_ids.add(src)
                edges.append((src, i))
        return node_ids, edges

    def layout(self, node_ids, edges):
        ids = set(node_ids)
        parents = defaultdict(list)
        for s, d in edges:
            if s in ids and d in ids and s != d:
                parents[d].append(s)

        depth = {}
        state = {}
        for start in sorted(ids, key=lambda x: (isinstance(x, str), x)):
            if state.get(start, 0) != 0:
                continue
            stack = [(start, False)]
            while stack:
                u, processed = stack.pop()
                if processed:
                    d = 0
                    for p in parents.get(u, ()):
                        if state.get(p) == 2:
                            d = max(d, depth[p] + 1)
                    depth[u] = d
                    state[u] = 2
                    continue
                if state.get(u, 0) != 0:
                    continue
                state[u] = 1
                stack.append((u, True))
                for p in parents.get(u, ()):
                    if state.get(p, 0) == 0:
                        stack.append((p, False))

        cols = defaultdict(list)
        for i in sorted(ids, key=lambda x: (isinstance(x, str), x)):
            cols[depth[i]].append(i)
        pos = {}
        for col in cols:
            for r, i in enumerate(cols[col]):
                pos[i] = r
        col_keys = sorted(cols)
        for sweep in range(4):
            for col in col_keys[1:]:
                cols[col].sort(key=lambda n: self.bary(n, self.parents, pos))
                for r, i in enumerate(cols[col]):
                    pos[i] = r
            for col in reversed(col_keys[:-1]):
                cols[col].sort(key=lambda n: self.bary(n, self.children, pos))
                for r, i in enumerate(cols[col]):
                    pos[i] = r
        import math
        max_rows = 10
        world = {}
        x_cursor = MARGIN
        for col in sorted(cols):
            members = cols[col]
            n_sub = max(1, math.ceil(len(members) / max_rows))
            for idx, i in enumerate(members):
                sub = idx // max_rows
                r = idx % max_rows
                world[i] = (x_cursor + sub * COL_W, MARGIN + r * ROW_H)
            x_cursor += n_sub * COL_W + 24
        return world

    @staticmethod
    def bary(node, adj, pos):
        rows = [pos[n] for n in adj.get(node, ()) if n in pos]
        return sum(rows) / len(rows) if rows else pos.get(node, 0)

    def w2s(self, wx, wy):
        return wx * self.zoom + self.ox, wy * self.zoom + self.oy

    def fit_view(self):
        self.needs_fit = False
        if not self.world:
            self.draw_graph()
            return
        xs = [x for x, _ in self.world.values()]
        ys = [y for _, y in self.world.values()]
        wmin, wmax = min(xs), max(xs) + NODE_W
        hmin, hmax = min(ys), max(ys) + NODE_H
        cw = max(self.graph.winfo_width(), 200)
        ch = max(self.graph.winfo_height(), 200)
        zx = (cw - 60) / max(wmax - wmin, 1)
        zy = (ch - 60) / max(hmax - hmin, 1)
        self.zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, min(zx, zy, 1.0)))
        self.ox = (cw - (wmax - wmin) * self.zoom) / 2 - wmin * self.zoom
        self.oy = (ch - (hmax - hmin) * self.zoom) / 2 - hmin * self.zoom
        self.draw_graph()

    def zoom_step(self, factor):
        cw = max(self.graph.winfo_width(), 1)
        ch = max(self.graph.winfo_height(), 1)
        self.zoom_at(cw / 2, ch / 2, factor)

    def zoom_at(self, sx, sy, factor):
        new = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self.zoom * factor))
        if new == self.zoom:
            return
        wx = (sx - self.ox) / self.zoom
        wy = (sy - self.oy) / self.zoom
        self.zoom = new
        self.ox = sx - wx * new
        self.oy = sy - wy * new
        self.draw_graph()

    def on_wheel_zoom(self, event):
        self.zoom_at(event.x, event.y, 1.15 if event.delta > 0 else 1 / 1.15)

    def on_pan_start(self, event):
        self.pan_last = (event.x, event.y)
        self.graph.configure(cursor="fleur")

    def on_pan_move(self, event):
        if self.pan_last is None:
            return
        dx = event.x - self.pan_last[0]
        dy = event.y - self.pan_last[1]
        self.pan_last = (event.x, event.y)
        self.ox += dx
        self.oy += dy
        self.draw_graph()

    def draw_graph(self):
        c = self.graph
        c.delete("all")
        self.screen_boxes.clear()
        if not self.world:
            return
        z = self.zoom
        self.zoom_label.config(text=f"{int(z * 100)}%")

        neighbors = set()
        if self.focus_id is not None:
            neighbors = set(self.children.get(self.focus_id, ())) | set(self.parents.get(self.focus_id, ()))
            neighbors.add(self.focus_id)

        nw, nh = NODE_W * z, NODE_H * z

        deferred = []
        for s, d in self.edges:
            if s == d or s not in self.world or d not in self.world:
                continue
            sx, sy = self.w2s(*self.world[s])
            dx, dy = self.w2s(*self.world[d])
            hot = self.focus_id is not None and (s == self.focus_id or d == self.focus_id)
            if hot:
                deferred.append((s, d, sx, sy, dx, dy))
                continue
            col = BURN_MV["edge_dim"] if self.focus_id is not None else mix(BURN_MV["edge_dim"], BURN_MV["orange"], 0.35)
            c.create_line(sx + nw, sy + nh / 2, dx, dy + nh / 2, fill=col, width=1, smooth=True)
        for s, d, sx, sy, dx, dy in deferred:
            col = BURN_MV["edge_out"] if s == self.focus_id else BURN_MV["edge_in"]
            c.create_line(sx + nw, sy + nh / 2, dx, dy + nh / 2, fill=col, width=max(2, int(2.4 * z)),
                          arrow=tk.LAST, smooth=True)

        for i in sorted(self.node_ids, key=lambda x: (isinstance(x, str), x)):
            self.draw_node(i, nw, nh, z, neighbors)

    def draw_node(self, node_id, nw, nh, z, neighbors):
        c = self.graph
        x, y = self.w2s(*self.world[node_id])
        dim = self.focus_id is not None and node_id not in neighbors
        focused = node_id == self.focus_id

        if isinstance(node_id, str):
            label = self.NEUTRAL_LABEL if node_id == "N" else node_id
            base = BURN_MV["node_root"] if node_id == "N" else BURN_MV["node_basic"]
            fill = mix(base, BURN_MV["graph_bg"], 0.6) if dim else base
        else:
            base = self.node_color(node_id, self.records[node_id])
            fill = mix(base, BURN_MV["graph_bg"], 0.62) if dim else base
        is_neighbor = node_id in neighbors and self.focus_id is not None
        outline = BURN_MV["gold"] if focused else (BURN_MV["orange"] if is_neighbor else BURN_MV["line"])
        width = 3 if focused else 1

        c.create_rectangle(x, y, x + nw, y + nh, fill=fill, outline=outline, width=width)
        self.screen_boxes[node_id] = (x, y, x + nw, y + nh)
        if z < 0.5:
            return
        tsize = max(6, int(9 * z))
        ssize = max(5, int(8 * z))
        text_fill = BURN_MV["muted"] if dim else BURN_MV["cream"]
        if isinstance(node_id, str):
            c.create_text(x + nw / 2, y + nh / 2, text=label, fill=text_fill, font=("Segoe UI", tsize, "bold"))
        else:
            title, sub = self.node_label(node_id, self.records[node_id])
            c.create_rectangle(x, y, x + nw, y + max(3, 5 * z),
                               fill=BURN_MV["orange"] if focused else BURN_MV["line"], outline="")
            c.create_text(x + 10 * z, y + nh * 0.34, text=title, anchor="w", fill=text_fill,
                          font=("Segoe UI", tsize, "bold"))
            c.create_text(x + 10 * z, y + nh * 0.70, text=sub, anchor="w",
                          fill=BURN_MV["muted"], font=("Consolas", ssize))

    def on_left_click(self, event):
        hit = self.hit_node(event.x, event.y)
        if hit is None:
            return
        if isinstance(hit, str):
            self.focus_id = hit
            self.selected = None
            self.clear_detail()
            label = self.NEUTRAL_LABEL if hit == "N" else hit
            kids = len(self.children.get(hit, ()))
            self.detail_head.config(text=f"{label}")
            self.set_status(f"{label} is a source motion (no editable record), {kids} attack(s) chain from it.", ok=True)
            self.draw_graph()
            return
        self.select_node(hit)

    def hit_node(self, sx, sy):
        for node_id, (x1, y1, x2, y2) in self.screen_boxes.items():
            if x1 <= sx <= x2 and y1 <= sy <= y2:
                return node_id
        return None

    def select_node(self, index):
        self.selected = index
        self.focus_id = index
        self.load_detail(index, self.records[index])
        self.draw_graph()

    def load_detail(self, index, rec):
        self.detail_head.config(text=self.node_head_text(index, rec))
        for spec in self.FIELD_SPECS:
            key = spec["key"]
            if spec.get("kind") == "flags":
                val = int.from_bytes(rec[spec["off"]:spec["off"] + spec["size"]], "little")
                self.flag_state[key] = val
                for bit, v in self.flag_checks[key].items():
                    v.set(1 if (val >> bit) & 1 else 0)
                self.refresh_flag_hex(key)
            else:
                raw = int.from_bytes(rec[spec["off"]:spec["off"] + spec["size"]], "little")
                if spec.get("signed") and raw >= (1 << (spec["size"] * 8 - 1)):
                    raw -= (1 << (spec["size"] * 8))
                self.field_vars[key].set(str(raw))

    def clear_detail(self):
        self.detail_head.config(text="No node selected")
        for spec in self.FIELD_SPECS:
            if spec.get("kind") == "flags":
                self.flag_state[spec["key"]] = 0
                for v in self.flag_checks[spec["key"]].values():
                    v.set(0)
                self.refresh_flag_hex(spec["key"])
            else:
                self.field_vars[spec["key"]].set("")

    def apply_detail(self):
        if self.selected is None:
            self.set_status("Left-click an editable node first.", ok=False)
            return
        rec = self.records[self.selected]
        try:
            for spec in self.FIELD_SPECS:
                key = spec["key"]
                off, size = spec["off"], spec["size"]
                if spec.get("kind") == "flags":
                    val = self.flag_state.get(key, 0) & ((1 << (size * 8)) - 1)
                else:
                    text = self.field_vars[key].get().strip()
                    if text == "":
                        raise ValueError(f"{spec['label']} is blank.")
                    val = int(text, 0)
                    lo = -(1 << (size * 8 - 1)) if spec.get("signed") else 0
                    hi = (1 << (size * 8 - 1)) - 1 if spec.get("signed") else (1 << (size * 8)) - 1
                    if not (lo <= val <= hi):
                        raise ValueError(f"{spec['label']} out of range ({lo}..{hi}).")
                    if val < 0:
                        val += (1 << (size * 8))
                rec[off:off + size] = val.to_bytes(size, "little")
            self.mem.seek(self.selected * self.RECORD_SIZE)
            self.mem.write(rec)
            self.rebuild_graph(refit=False)
            self.set_status("Applied in memory. Use Create Mod to save.", ok=True)
        except Exception as e:
            self.set_status(f"Apply failed: {e}", ok=False)

    def create_mod(self):
        if self.mem is None:
            self.set_status("No character loaded.", ok=False)
            return
        fname = self.current_file()
        char = os.path.splitext(fname)[0] if fname else "UNK"
        base = self.modname.get().split(".", 1)[0] or ("DW2" + self.EXT.lstrip(".").title())
        out = f"{base}__{char}{self.MOD_EXT}"
        try:
            os.makedirs(MODS_DIR, exist_ok=True)
            with open(os.path.join(MODS_DIR, out), "wb") as w:
                w.write(self.mem.getvalue())
            self.set_status(f"Mod '{out}' created in DW2_Mods.", ok=True)
        except Exception as e:
            self.set_status(f"Error creating mod '{out}': {e}", ok=False)

    def draw_header(self, event=None):
        c = self.header_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("static")
        for y in range(0, h, 8):
            fill = mix(BURN_MV["void"], BURN_MV["panel_3"], y / max(h, 1) * 0.7)
            c.create_rectangle(0, y, w, y + 8, fill=fill, outline="", tags="static")
        c.create_polygon(0, h - 26, w * 0.34, h - 8, w, h - 34, w, h, 0, h,
                         fill=BURN_MV["shadow"], outline="", tags="static")
        c.create_line(24, h - 16, w - 24, h - 16, fill=BURN_MV["orange"], width=4, tags="static")
        c.create_line(24, h - 22, w - 24, h - 22, fill=BURN_MV["gold"], width=1, tags="static")
        c.create_text(34, 38, text=self.HEADER_TITLE, anchor="w", fill=BURN_MV["cream"],
                      font=("Segoe UI", 26, "bold"), tags="static")
        c.create_text(36, 68, text=self.HEADER_SUB, anchor="w", fill=BURN_MV["muted"],
                      font=("Segoe UI", 10), tags="static")
        self.draw_header_embers()

    def draw_header_embers(self):
        c = self.header_canvas
        c.delete("ember")
        w = max(c.winfo_width(), 1)
        if not self.header_embers:
            self.header_embers = [
                [0.20, 90, 2, BURN_MV["gold"]], [0.33, 97, 2, BURN_MV["orange"]],
                [0.46, 98, 3, BURN_MV["orange"]], [0.58, 88, 2, BURN_MV["gold"]],
                [0.69, 86, 2, BURN_MV["red"]], [0.80, 95, 2, BURN_MV["orange"]],
            ]
        for xf, y, radius, color in self.header_embers:
            x = int(w * xf)
            c.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="", tags="ember")

    def start_header_animation(self):
        if not self.root.winfo_exists():
            return
        for e in self.header_embers:
            e[0] += 0.012
            if e[0] > 0.86:
                e[0] = 0.18
            e[1] -= 1
            if e[1] < 78:
                e[1] = 100
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

    def set_status(self, text, ok=True):
        if hasattr(self, "status_label"):
            self.status_label.config(text=text, fg=BURN_MV["green"] if ok else BURN_MV["red"])

    def is_used(self, index, rec):
        return any(rec)

    def edges_for(self, index, rec):
        return ()

    def node_label(self, index, rec):
        return (f"#{index}", "")

    def node_color(self, index, rec):
        return BURN_MV["panel_2"]

    def node_head_text(self, index, rec):
        return f"Record {index}"
