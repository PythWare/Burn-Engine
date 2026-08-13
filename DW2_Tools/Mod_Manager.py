# DW2_Tools/Mod_Manager.py
"""
Unified DW2 Mod Manager
"""
import os
import tkinter as tk
from tkinter import ttk

from .Utility import BACKUP_DIR, HOSTFS_ELF, ICON_DIR, MODS_DIR, itemsoffset, unit_data
from .Item_Editor import DW2_ITEM_MOD_EXT, ITEM_COUNT, ITEM_RECORD_SIZE
from .Name_Editor import DW2_NAME_MOD_EXT, NAME_GROUP_DEFS
from .DW2_Bodyguard_Progression import DW2_GUARD_MOD_EXT, GUARD_BYTE_COUNT, GuardTool
from .Unit_Editor import DW2_UNIT_MOD_EXT, NUM_SLOTS_FIRST, NUM_SLOTS_SECOND, SLOT_SIZE
from .DW2_VGuider import DW2_STAGE_MOD_EXT, STAGE_MORALE_DATA, STAGE_NAMES, find_stage_side_file
from .Utility import STAGE_DIRS
from .Move_Common import CHARA_DIR, char_label
from .Atk_Editor import AtkEditor
from .Mov_Editor import MovEditor


STATE_FILE = os.path.join(os.path.dirname(__file__), "mod_state.json")

ITEM_BACKUP = os.path.join(BACKUP_DIR, "Hostfs_Item.backup")
NAME_BACKUP = os.path.join(BACKUP_DIR, "Hostfs_Name.backup")
GUARD_BACKUP = os.path.join(BACKUP_DIR, "Hostfs_Guard.backup")
UNIT_BACKUP = os.path.join(BACKUP_DIR, "DW2_Original.unitdata")

STAGE_SLOT_BYTES = 256 * 32

MOD_TYPES = {
    "item": {"ext": DW2_ITEM_MOD_EXT, "label": "Item Values", "icon": "item"},
    "name": {"ext": DW2_NAME_MOD_EXT, "label": "Names", "icon": "name"},
    "guard": {"ext": DW2_GUARD_MOD_EXT, "label": "Bodyguard Progression", "icon": "guard"},
    "unit": {"ext": DW2_UNIT_MOD_EXT, "label": "Unit Data", "icon": "unit"},
    "stage": {"ext": DW2_STAGE_MOD_EXT, "label": "Stage Data", "icon": "stage"},
    "atk": {"ext": AtkEditor.MOD_EXT, "label": "Attack / Combo Data", "icon": "atk"},
    "mov": {"ext": MovEditor.MOD_EXT, "label": "Motion Chain Data", "icon": "mov"},
}

MOD_TYPE_ORDER = ["item", "name", "guard", "unit", "stage", "atk", "mov"]

SCOPED_TYPES = ("stage", "atk", "mov")

CHARA_TYPES = {
    "atk": {"file_ext": AtkEditor.EXT, "sizes": (2048,)},
    "mov": {"file_ext": MovEditor.EXT, "sizes": (2048, 4096)},
}


def ensure_dirs():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(MODS_DIR, exist_ok=True)

def scan_mods():
    ensure_dirs()
    result = {key: [] for key in MOD_TYPE_ORDER}
    for fname in sorted(os.listdir(MODS_DIR)):
        full = os.path.join(MODS_DIR, fname)
        if not os.path.isfile(full):
            continue
        for key in MOD_TYPE_ORDER:
            ext = MOD_TYPES[key]["ext"]
            if fname.lower().endswith(ext.lower()):
                entry = {"filename": fname, "path": full, "size": os.path.getsize(full),
                         "stage_idx": None, "char": None}
                if key == "stage":
                    entry["stage_idx"] = peek_stage_index(full)
                elif key in CHARA_TYPES:
                    entry["char"] = peek_char(fname, ext)
                result[key].append(entry)
                break
    return result


def peek_char(fname, ext):
    """Recover the target CHARA name from a mod filename"""
    stem = fname[:-len(ext)] if fname.lower().endswith(ext.lower()) else os.path.splitext(fname)[0]
    if "__" not in stem:
        return None
    char = stem.rsplit("__", 1)[1].strip()
    return char if char else None


def chara_target_path(type_key, char):
    """The loose CHARA file an atk/mov mod replaces"""
    return os.path.join(CHARA_DIR, f"{char}{CHARA_TYPES[type_key]['file_ext']}")


def peek_stage_index(path):
    try:
        with open(path, "rb") as f:
            f.seek(STAGE_SLOT_BYTES * 2)
            b = f.read(1)
        if not b:
            return None
        idx = b[0]
        return idx if 0 <= idx < len(STAGE_NAMES) else None
    except OSError:
        return None

def load_state():
    default = {"item": None, "name": None, "guard": None, "unit": None,
               "stage": {str(i): None for i in range(8)}, "atk": {}, "mov": {}}
    if os.path.exists(STATE_FILE):
        try:
            import json
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            for key in ("item", "name", "guard", "unit"):
                default[key] = data.get(key)
            stage_state = data.get("stage", {})
            if isinstance(stage_state, dict):
                for i in range(8):
                    default["stage"][str(i)] = stage_state.get(str(i))
            for key in ("atk", "mov"):
                saved = data.get(key, {})
                if isinstance(saved, dict):
                    default[key] = {k: v for k, v in saved.items() if v}
        except Exception:
            pass
    return default


def save_state(state):
    import json
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def snapshot_item():
    ensure_dirs()
    if os.path.exists(ITEM_BACKUP):
        return
    length = ITEM_COUNT * ITEM_RECORD_SIZE
    with open(HOSTFS_ELF, "rb") as f:
        f.seek(itemsoffset)
        data = f.read(length)
    with open(ITEM_BACKUP, "wb") as f:
        f.write(data)


def apply_item(path):
    with open(path, "rb") as f:
        data = f.read()
    with open(HOSTFS_ELF, "r+b") as f:
        f.seek(itemsoffset)
        f.write(data)

def snapshot_name():
    ensure_dirs()
    if os.path.exists(NAME_BACKUP):
        return
    buf = bytearray()
    with open(HOSTFS_ELF, "rb") as f:
        for base, count, byte_len, spacing in NAME_GROUP_DEFS:
            f.seek(base)
            buf += f.read(count * spacing)
    with open(NAME_BACKUP, "wb") as f:
        f.write(buf)
        for base, count, byte_len, spacing in NAME_GROUP_DEFS:
            f.write(base.to_bytes(4, "little"))


def apply_name(path):
    with open(path, "rb") as f:
        data = f.read()
    pos = 0
    spans = []
    for base, count, byte_len, spacing in NAME_GROUP_DEFS:
        size = count * spacing
        spans.append((base, data[pos:pos + size]))
        pos += size
    with open(HOSTFS_ELF, "r+b") as f:
        for base, chunk in spans:
            f.seek(base)
            f.write(chunk)

def snapshot_guard():
    ensure_dirs()
    if os.path.exists(GUARD_BACKUP):
        return
    with open(HOSTFS_ELF, "rb") as f:
        f.seek(GuardTool.GUARD_PROG_OFFSET)
        guard_bytes = f.read(GUARD_BYTE_COUNT)
        f.seek(GuardTool.AI_GUARD_FOLLOW)
        follow_byte = f.read(1)
    with open(GUARD_BACKUP, "wb") as f:
        f.write(guard_bytes)
        f.write(follow_byte)
        f.write(GuardTool.GUARD_PROG_OFFSET.to_bytes(4, "little"))
        f.write(GuardTool.AI_GUARD_FOLLOW.to_bytes(4, "little"))

def apply_guard(path):
    with open(path, "rb") as f:
        data = f.read()
    guard_bytes = data[0:GUARD_BYTE_COUNT]
    follow_byte = data[GUARD_BYTE_COUNT:GUARD_BYTE_COUNT + 1]
    guard_off = int.from_bytes(data[GUARD_BYTE_COUNT + 1:GUARD_BYTE_COUNT + 5], "little")
    follow_off = int.from_bytes(data[GUARD_BYTE_COUNT + 5:GUARD_BYTE_COUNT + 9], "little")
    with open(HOSTFS_ELF, "r+b") as f:
        f.seek(guard_off)
        f.write(guard_bytes)
        f.seek(follow_off)
        f.write(follow_byte)

def snapshot_unit():
    ensure_dirs()
    if os.path.exists(UNIT_BACKUP):
        return
    with open(HOSTFS_ELF, "rb") as f:
        f.seek(unit_data[0])
        block0 = f.read(NUM_SLOTS_FIRST * SLOT_SIZE)
        f.seek(unit_data[1])
        block1 = f.read(NUM_SLOTS_SECOND * SLOT_SIZE)
    with open(UNIT_BACKUP, "wb") as f:
        f.write(block0)
        f.write(block1)
        for off in unit_data:
            f.write(off.to_bytes(4, "little"))


def apply_unit(path):
    with open(path, "rb") as f:
        data = f.read()
    size0 = NUM_SLOTS_FIRST * SLOT_SIZE
    size1 = NUM_SLOTS_SECOND * SLOT_SIZE
    block0 = data[0:size0]
    block1 = data[size0:size0 + size1]
    off0 = int.from_bytes(data[size0 + size1:size0 + size1 + 4], "little")
    off1 = int.from_bytes(data[size0 + size1 + 4:size0 + size1 + 8], "little")
    with open(HOSTFS_ELF, "r+b") as f:
        f.seek(off0)
        f.write(block0)
        f.seek(off1)
        f.write(block1)

def stage_backup_path(stage_idx):
    safe_name = STAGE_NAMES[stage_idx].replace(" ", "")
    return os.path.join(BACKUP_DIR, f"Hostfs_Stage_{safe_name}.backup")


def snapshot_stage(stage_idx):
    ensure_dirs()
    backup_path = stage_backup_path(stage_idx)
    if os.path.exists(backup_path):
        return

    stage_dir = STAGE_DIRS[stage_idx]
    ub0_path = find_stage_side_file(stage_dir, ".ub0")
    ub1_path = find_stage_side_file(stage_dir, ".ub1")
    if not ub0_path or not ub1_path:
        raise FileNotFoundError(f"Hostfs stage files not found in {stage_dir}")

    with open(ub0_path, "rb") as f:
        side1 = f.read(STAGE_SLOT_BYTES)
    with open(ub1_path, "rb") as f:
        side2 = f.read(STAGE_SLOT_BYTES)

    stg_name = STAGE_NAMES[stage_idx]
    with open(backup_path, "wb") as f:
        f.write(side1)
        f.write(side2)
        f.write(stage_idx.to_bytes(1, "little"))
        if stg_name in STAGE_MORALE_DATA and os.path.exists(HOSTFS_ELF):
            f.write(b"MORALE")
            with open(HOSTFS_ELF, "rb") as ef:
                for side_id in (1, 2):
                    m_off, m_count = STAGE_MORALE_DATA[stg_name][side_id]
                    ef.seek(m_off)
                    values = ef.read(m_count * 2)
                    f.write(m_count.to_bytes(2, "little"))
                    f.write(values)
        else:
            f.write(b"NOMORALE")


def apply_stage(path):
    """Apply a stage mod and return the stage index it targeted"""
    with open(path, "rb") as f:
        data = f.read()
    slot_bytes = data[0:STAGE_SLOT_BYTES * 2]
    stage_idx = data[STAGE_SLOT_BYTES * 2]
    rest = data[STAGE_SLOT_BYTES * 2 + 1:]

    stage_dir = STAGE_DIRS[stage_idx]
    ub0_path = find_stage_side_file(stage_dir, ".ub0")
    ub1_path = find_stage_side_file(stage_dir, ".ub1")
    if not ub0_path or not ub1_path:
        raise FileNotFoundError(f"Hostfs stage files not found in {stage_dir}")

    with open(ub0_path, "r+b") as f:
        f.write(slot_bytes[0:STAGE_SLOT_BYTES])
    with open(ub1_path, "r+b") as f:
        f.write(slot_bytes[STAGE_SLOT_BYTES:STAGE_SLOT_BYTES * 2])

    if rest[:6] == b"MORALE":
        stg_name = STAGE_NAMES[stage_idx]
        pos = 6
        if stg_name in STAGE_MORALE_DATA and os.path.exists(HOSTFS_ELF):
            with open(HOSTFS_ELF, "r+b") as ef:
                for side_id in (1, 2):
                    count = int.from_bytes(rest[pos:pos + 2], "little")
                    pos += 2
                    values = rest[pos:pos + count * 2]
                    pos += count * 2
                    m_off, m_count = STAGE_MORALE_DATA[stg_name][side_id]
                    write_len = min(len(values), m_count * 2)
                    ef.seek(m_off)
                    ef.write(values[:write_len])

    return stage_idx

def chara_backup_path(type_key, char):
    return os.path.join(BACKUP_DIR, f"Chara_{char}{CHARA_TYPES[type_key]['file_ext']}.backup")


def snapshot_chara(type_key, char):
    """Stash the pristine CHARA file the first time this character is modded"""
    ensure_dirs()
    backup_path = chara_backup_path(type_key, char)
    if os.path.exists(backup_path):
        return
    target = chara_target_path(type_key, char)
    if not os.path.exists(target):
        raise FileNotFoundError(f"No {os.path.basename(target)} in {CHARA_DIR}")
    with open(target, "rb") as f:
        data = f.read()
    with open(backup_path, "wb") as f:
        f.write(data)


def apply_chara(type_key, char, path):
    """Replace the loose CHARA file with the mod's bytes"""
    target = chara_target_path(type_key, char)
    if not os.path.exists(target):
        raise FileNotFoundError(f"No {os.path.basename(target)} in {CHARA_DIR}")
    with open(path, "rb") as f:
        data = f.read()
    allowed = CHARA_TYPES[type_key]["sizes"]
    if len(data) not in allowed:
        raise ValueError(
            f"{os.path.basename(path)} is {len(data)} bytes; {type_key.upper()} "
            f"files must be {' or '.join(str(s) for s in allowed)}."
        )
    current = os.path.getsize(target)
    if len(data) != current:
        raise ValueError(
            f"{os.path.basename(path)} is {len(data)} bytes but "
            f"{os.path.basename(target)} is {current}; refusing to change the "
            "file size (it would move every following sector)."
        )
    with open(target, "wb") as f:
        f.write(data)

SNAPSHOT_FUNCS = {
    "item": lambda entry=None: snapshot_item(),
    "name": lambda entry=None: snapshot_name(),
    "guard": lambda entry=None: snapshot_guard(),
    "unit": lambda entry=None: snapshot_unit(),
    "stage": None,
    "atk": None,
    "mov": None,
}

APPLY_FUNCS = {
    "item": apply_item,
    "name": apply_name,
    "guard": apply_guard,
    "unit": apply_unit,
    "stage": apply_stage,
}

BACKUP_PATHS = {
    "item": lambda entry=None: ITEM_BACKUP,
    "name": lambda entry=None: NAME_BACKUP,
    "guard": lambda entry=None: GUARD_BACKUP,
    "unit": lambda entry=None: UNIT_BACKUP,
}


BURN_MM = {
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
    "dim": "#4a3527",
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


class DW2ModManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Ember Celica")

        self.root.configure(bg=BURN_MM["void"])
        self.root.minsize(1080, 660)
        self.root.geometry("1180x720")
        self.root.resizable(True, True)

        self.mods = {}
        self.state = {}
        self.row_lookup = {}
        self.selected_key = None
        self.header_embers = []
        self.animation_job = None
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_tree())

        self.configure_ttk()
        self.build_gui()
        self.scan()

        self.root.bind("<Destroy>", self.on_destroy, add="+")
        self.start_header_animation()

    def scan(self):
        self.mods = scan_mods()
        self.state = load_state()
        self.refresh_tree()
        self.draw_header()
        self.show_details(None)

    def configure_ttk(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Burn.Treeview",
            background=BURN_MM["entry"],
            fieldbackground=BURN_MM["entry"],
            foreground=BURN_MM["cream"],
            bordercolor=BURN_MM["line"],
            rowheight=24,
            font=("Segoe UI", 9),
        )
        style.map(
            "Burn.Treeview",
            background=[("selected", BURN_MM["red_dark"])],
            foreground=[("selected", BURN_MM["cream"])],
        )
        style.configure(
            "Burn.Treeview.Heading",
            background=BURN_MM["red_dark"],
            foreground=BURN_MM["cream"],
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
        )
        style.map("Burn.Treeview.Heading", background=[("active", BURN_MM["orange"])])

    def build_gui(self):
        self.shell = tk.Frame(self.root, bg=BURN_MM["void"])
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(
            self.shell,
            height=132,
            bg=BURN_MM["void"],
            bd=0,
            highlightthickness=0,
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self.draw_header)

        content = tk.Frame(self.shell, bg=BURN_MM["void"], padx=18, pady=12)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, minsize=340)
        content.rowconfigure(0, weight=1)

        bay_panel, bay_body = self.make_panel(content, "Mod Bay", BURN_MM["orange"])
        bay_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        bay_body.columnconfigure(0, weight=1)
        bay_body.rowconfigure(2, weight=1)
        self.build_bay_panel(bay_body)

        detail_panel, detail_body = self.make_panel(content, "Mod Details", BURN_MM["red"])
        detail_panel.grid(row=0, column=1, sticky="nsew")
        self.build_detail_panel(detail_body)

        action_panel, action_body = self.make_panel(self.shell, "Vault Control", BURN_MM["lilac"])
        action_panel.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        self.build_action_panel(action_body)

    def make_panel(self, parent, title, accent=None):
        accent = accent or BURN_MM["orange"]
        outer = tk.Frame(
            parent,
            bg=BURN_MM["panel"],
            highlightbackground=BURN_MM["line"],
            highlightcolor=BURN_MM["line"],
            highlightthickness=1,
        )
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        header = tk.Frame(outer, bg=BURN_MM["red_dark"], height=36)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            header,
            text=title,
            bg=BURN_MM["red_dark"],
            fg=BURN_MM["cream"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10)

        body = tk.Frame(outer, bg=BURN_MM["panel"], padx=12, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        return outer, body

    def burn_label(self, parent, text, **kwargs):
        bg = kwargs.pop("bg", BURN_MM["panel"])
        fg = kwargs.pop("fg", BURN_MM["cream"])
        font = kwargs.pop("font", ("Segoe UI", 9))
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)

    def burn_entry(self, parent, textvariable, width=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=BURN_MM["entry"],
            fg=BURN_MM["cream"],
            insertbackground=BURN_MM["gold"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BURN_MM["line_dim"],
            highlightcolor=BURN_MM["gold"],
            font=("Consolas", 10),
        )

    def burn_button(self, parent, text, command, accent=None, fg=None):
        accent = accent or BURN_MM["red_dark"]
        fg = fg or BURN_MM["cream"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg=fg,
            activebackground=BURN_MM["gold"],
            activeforeground=BURN_MM["shadow"],
            bd=0,
            highlightthickness=1,
            highlightbackground=BURN_MM["line"],
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
        )

    def build_bay_panel(self, parent):
        self.burn_label(
            parent,
            "Filter",
            fg=BURN_MM["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w")
        search = self.burn_entry(parent, self.search_var)
        search.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        tree_frame = tk.Frame(parent, bg=BURN_MM["shadow"])
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("type", "name", "size", "status")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Burn.Treeview",
        )
        self.tree.heading("type", text="Type")
        self.tree.heading("name", text="Mod File")
        self.tree.heading("size", text="Bytes")
        self.tree.heading("status", text="Status")
        self.tree.column("type", width=90, anchor="w")
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("status", width=80, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scroll = tk.Scrollbar(tree_frame, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

    def build_detail_panel(self, parent):
        parent.columnconfigure(0, weight=1)

        self.detail_title = self.burn_label(
            parent,
            "No mod selected",
            fg=BURN_MM["gold"],
            font=("Segoe UI", 14, "bold"),
            wraplength=300,
            justify="left",
        )
        self.detail_title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        rows_frame = tk.Frame(parent, bg=BURN_MM["panel_2"], padx=12, pady=10)
        rows_frame.grid(row=1, column=0, sticky="ew")
        rows_frame.columnconfigure(1, weight=1)

        rows = [
            ("detail_type", "Mod type"),
            ("detail_target", "Target"),
            ("detail_size", "File size"),
            ("detail_state", "Live status"),
        ]
        for row, (attr, label_text) in enumerate(rows):
            self.burn_label(
                rows_frame,
                label_text,
                bg=BURN_MM["panel_2"],
                fg=BURN_MM["muted"],
                font=("Segoe UI", 8, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=3)
            value = self.burn_label(
                rows_frame,
                "-",
                bg=BURN_MM["panel_2"],
                fg=BURN_MM["cream"],
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                wraplength=170,
                justify="right",
            )
            value.grid(row=row, column=1, sticky="e", pady=3)
            setattr(self, attr, value)

        note = self.burn_label(
            parent,
            "Enable writes this mod's bytes into the hostfs loose files. "
            "Disable restores the original bytes captured the first time this "
            "target was ever modified.",
            fg=BURN_MM["muted"],
            font=("Segoe UI", 8),
            wraplength=300,
            justify="left",
        )
        note.grid(row=2, column=0, sticky="w", pady=(14, 0))

    def build_action_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.columnconfigure(3, weight=3)

        enable_button = self.burn_button(
            parent, "Enable", self.enable_selected, BURN_MM["orange"], fg=BURN_MM["shadow"]
        )
        enable_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        disable_button = self.burn_button(
            parent, "Disable/Restore", self.disable_selected, BURN_MM["red_dark"], fg=BURN_MM["cream"]
        )
        disable_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        refresh_button = self.burn_button(
            parent, "Refresh", self.scan, BURN_MM["lilac_dark"], fg=BURN_MM["cream"]
        )
        refresh_button.grid(row=0, column=2, sticky="ew", padx=(0, 12))

        self.status_label = self.burn_label(
            parent,
            f"Watching {MODS_DIR}",
            fg=BURN_MM["green"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            wraplength=520,
            justify="left",
        )
        self.status_label.grid(row=0, column=3, sticky="ew")

    def draw_header(self, event=None):
        c = self.header_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("static")

        for y in range(0, h, 8):
            fill = mix(BURN_MM["void"], BURN_MM["panel_3"], y / max(h, 1) * 0.7)
            c.create_rectangle(0, y, w, y + 8, fill=fill, outline="", tags="static")

        c.create_polygon(
            0, h - 28, w * 0.34, h - 10, w, h - 36, w, h, 0, h,
            fill=BURN_MM["shadow"],
            outline="",
            tags="static",
        )
        c.create_line(24, h - 18, w - 24, h - 18, fill=BURN_MM["orange"], width=4, tags="static")
        c.create_line(24, h - 24, w - 24, h - 24, fill=BURN_MM["gold"], width=1, tags="static")

        c.create_text(
            34, 34,
            text="Ember Celica",
            anchor="w",
            fill=BURN_MM["cream"],
            font=("Segoe UI", 28, "bold"),
            tags="static",
        )
        c.create_text(
            36, 64,
            text="One vault for every mod type/applies straight to the hostfs loose files",
            anchor="w",
            fill=BURN_MM["muted"],
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
                [0.10, 94, 2, BURN_MM["gold"]],
                [0.18, 101, 2, BURN_MM["orange"]],
                [0.26, 102, 3, BURN_MM["orange"]],
                [0.34, 91, 2, BURN_MM["gold"]],
                [0.42, 90, 2, BURN_MM["red"]],
                [0.50, 99, 2, BURN_MM["orange"]],
            ]
        for x_factor, y, radius, color in self.header_embers:
            x = int(w * x_factor)
            c.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=color, outline="", tags="ember",
            )

    def start_header_animation(self):
        if not self.root.winfo_exists():
            return
        if self.header_embers:
            for ember in self.header_embers:
                ember[0] += 0.010
                if ember[0] > 0.52:
                    ember[0] = 0.08
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

    def refresh_tree(self):
        if not hasattr(self, "tree"):
            return
        query = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.row_lookup.clear()

        for type_key in MOD_TYPE_ORDER:
            label = MOD_TYPES[type_key]["label"]
            for entry in self.mods.get(type_key, []):
                if query and query not in entry["filename"].lower() and query not in label.lower():
                    continue
                status = self.entry_status(type_key, entry)
                iid = entry["path"]
                self.row_lookup[iid] = (type_key, entry)
                self.tree.insert(
                    "", "end", iid=iid,
                    values=(label, entry["filename"], entry["size"], status),
                )

    def entry_scope(self, type_key, entry):
        if type_key == "stage":
            idx = entry.get("stage_idx")
            return None if idx is None else str(idx)
        if type_key in CHARA_TYPES:
            return entry.get("char")
        return None

    def entry_status(self, type_key, entry):
        if type_key in SCOPED_TYPES:
            scope = self.entry_scope(type_key, entry)
            if scope is None:
                return "?"
            active_name = self.state.get(type_key, {}).get(scope)
            return "Live" if active_name == entry["filename"] else ""
        active_name = self.state.get(type_key)
        return "Live" if active_name == entry["filename"] else ""

    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self.show_details(None)
            return
        key = sel[0]
        self.selected_key = key
        self.show_details(self.row_lookup.get(key))

    def show_details(self, item):
        if item is None:
            self.detail_title.config(text="No mod selected")
            for attr in ("detail_type", "detail_target", "detail_size", "detail_state"):
                getattr(self, attr).config(text="-")
            return

        type_key, entry = item
        label = MOD_TYPES[type_key]["label"]
        self.detail_title.config(text=entry["filename"])
        self.detail_type.config(text=label)
        self.detail_size.config(text=f"{entry['size']} bytes")
        self.detail_state.config(text=self.entry_status(type_key, entry) or "Not applied")

        if type_key == "stage":
            idx = entry.get("stage_idx")
            target = STAGE_NAMES[idx] if idx is not None else "Unknown stage (corrupt mod?)"
            self.detail_target.config(text=f"{target}\n(.ub0 / .ub1)")
        elif type_key == "item":
            self.detail_target.config(text=f"Hostfs ELF @ 0x{itemsoffset:X}")
        elif type_key == "name":
            self.detail_target.config(text="Hostfs ELF, 4 name tables")
        elif type_key == "guard":
            self.detail_target.config(text="Hostfs ELF, guard + follow byte")
        elif type_key == "unit":
            self.detail_target.config(text="Hostfs ELF, 2 unit tables")
        elif type_key in CHARA_TYPES:
            char = entry.get("char")
            if char is None:
                self.detail_target.config(
                    text="Unknown character (expected '<name>__<CHAR>" + MOD_TYPES[type_key]["ext"] + "')")
            else:
                target = chara_target_path(type_key, char)
                exists = "" if os.path.exists(target) else "\n(missing - unpack LINKDATA first)"
                self.detail_target.config(text=f"{char_label(char)}\nCHARA/{os.path.basename(target)}{exists}")

    def enable_selected(self):
        item = self.row_lookup.get(self.selected_key)
        if item is None:
            self.set_status("Select a mod from the Mod Bay first.", ok=False)
            return
        type_key, entry = item

        try:
            if type_key == "stage":
                idx = entry.get("stage_idx")
                if idx is None:
                    raise ValueError("This stage mod has no readable stage id byte.")
                snapshot_stage(idx)
                applied_idx = apply_stage(entry["path"])
                self.state.setdefault("stage", {})[str(applied_idx)] = entry["filename"]
            elif type_key in CHARA_TYPES:
                char = entry.get("char")
                if char is None:
                    raise ValueError(
                        "This mod's filename does not name a character; expected "
                        f"'<name>__<CHAR>{MOD_TYPES[type_key]['ext']}'.")
                snapshot_chara(type_key, char)
                apply_chara(type_key, char, entry["path"])
                self.state.setdefault(type_key, {})[char] = entry["filename"]
            else:
                snapshot_fn = SNAPSHOT_FUNCS[type_key]
                snapshot_fn()
                APPLY_FUNCS[type_key](entry["path"])
                self.state[type_key] = entry["filename"]

            save_state(self.state)
            self.set_status(f"Enabled '{entry['filename']}'.", ok=True)
        except Exception as e:
            self.set_status(f"Failed to enable '{entry['filename']}': {e}", ok=False)

        self.refresh_tree()
        self.draw_header()
        self.show_details(item)

    def disable_selected(self):
        item = self.row_lookup.get(self.selected_key)
        if item is None:
            self.set_status("Select a mod from the Mod Bay first.", ok=False)
            return
        type_key, entry = item

        try:
            if type_key == "stage":
                idx = entry.get("stage_idx")
                if idx is None:
                    raise ValueError("This stage mod has no readable stage id byte.")
                backup_path = stage_backup_path(idx)
                if not os.path.exists(backup_path):
                    raise FileNotFoundError("No backup captured yet for this stage; nothing to restore.")
                apply_stage(backup_path)
                self.state.setdefault("stage", {})[str(idx)] = None
                target_desc = STAGE_NAMES[idx]
            elif type_key in CHARA_TYPES:
                char = entry.get("char")
                if char is None:
                    raise ValueError("This mod's filename does not name a character.")
                backup_path = chara_backup_path(type_key, char)
                if not os.path.exists(backup_path):
                    raise FileNotFoundError(
                        f"No backup captured yet for {char}{CHARA_TYPES[type_key]['file_ext']}; "
                        "nothing to restore.")
                apply_chara(type_key, char, backup_path)
                self.state.setdefault(type_key, {})[char] = None
                target_desc = f"{char}{CHARA_TYPES[type_key]['file_ext']}"
            else:
                backup_path = BACKUP_PATHS[type_key]()
                if not os.path.exists(backup_path):
                    raise FileNotFoundError("No backup captured yet for this target; nothing to restore.")
                APPLY_FUNCS[type_key](backup_path)
                self.state[type_key] = None
                target_desc = MOD_TYPES[type_key]["label"]

            save_state(self.state)
            self.set_status(f"Restored {target_desc} to its original hostfs bytes.", ok=True)
        except Exception as e:
            self.set_status(f"Failed to disable: {e}", ok=False)

        self.refresh_tree()
        self.draw_header()
        self.show_details(item)

    def set_status(self, text, ok=True):
        if not hasattr(self, "status_label"):
            return
        self.status_label.config(
            text=text,
            fg=BURN_MM["green"] if ok else BURN_MM["red"],
        )
