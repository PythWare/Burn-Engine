"""
DW2 HostFS TOC Updater
"""

import queue, threading, traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

if __package__:
    from . import dw2_hostfs_patch as patchmod
else:
    import dw2_hostfs_patch as patchmod

SCRIPT_DIR = Path(__file__).resolve().parent
GAME_DIR = SCRIPT_DIR.parent

BG = "#120b08"
CARD = "#1d120c"
ACCENT = "#ff6a00"
ACCENT_DK = "#ff8a1e"
ACCENT_DKR = "#ffd23c"
TEXT = "#ffe8b4"
MUTED = "#d7a86c"
OK = "#8fd15a"
WARN = "#ff8a1e"
ERR = "#ff2f36"
FIELD = "#2b160c"
SOFT = "#4b2c1c"
DISABLED_BG = "#3a2415"
DISABLED_FG = "#8a5a2f"
LOG_BG = "#0b0604"
BTN_TEXT = "#120b08"

FONT = ("Segoe UI", 10)


class TocUpdaterApp:
    def __init__(self, root):
        self.root = root
        self.queue = queue.Queue()
        self.worker = None

        root.title("DW2 HostFS TOC Updater")
        root.configure(bg=BG)
        root.minsize(720, 640)

        self.elf_var = tk.StringVar(value=str(GAME_DIR / "SLUS_200.79"))
        self.unpack_var = tk.StringVar(value=str(GAME_DIR / "unpacked_linkdata"))
        self.out_var = tk.StringVar(value=str(GAME_DIR / "SLUS_200.79.hostfs.elf"))
        self.prefix_var = tk.StringVar(value="")

        self.setup_style()
        self.build_ui()
        self.poll_queue()

    def setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Title.TLabel", background=BG, foreground=ACCENT_DKR,
                        font=("Segoe UI Semibold", 19))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Field.TLabel", background=BG, foreground=TEXT,
                        font=("Segoe UI Semibold", 9))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT)
        style.configure("TileValue.TLabel", background=CARD, foreground=ACCENT_DKR,
                        font=("Segoe UI Semibold", 21))
        style.configure("TileKey.TLabel", background=CARD, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9, "italic"))

        style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT,
                        bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT,
                        insertcolor=TEXT, padding=5)

        style.configure("Accent.TButton", background=ACCENT, foreground=BTN_TEXT,
                        font=("Segoe UI Semibold", 12), padding=(20, 11),
                        borderwidth=0, focusthickness=0)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_DK), ("pressed", ACCENT_DKR),
                              ("disabled", DISABLED_BG)],
                  foreground=[("disabled", DISABLED_FG)])

        style.configure("Browse.TButton", background=SOFT, foreground=TEXT,
                        font=("Segoe UI", 9), padding=(12, 5), borderwidth=0)
        style.map("Browse.TButton",
                  background=[("active", ACCENT), ("pressed", ACCENT_DK)],
                  foreground=[("active", BTN_TEXT)])

        style.configure("Heat.Horizontal.TProgressbar",
                        troughcolor=SOFT, background=ACCENT,
                        bordercolor=SOFT, lightcolor=ACCENT, darkcolor=ACCENT,
                        thickness=10)

        style.configure("TScrollbar", background=SOFT, troughcolor=BG,
                        bordercolor=BG, arrowcolor=TEXT,
                        lightcolor=SOFT, darkcolor=SOFT)
        style.map("TScrollbar", background=[("active", ACCENT)])

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=(22, 20))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="HostFS TOC Updater", style="Title.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(outer, style="Sub.TLabel",
                  text="Reflect edits in unpacked_linkdata back into the game's "
                       "sector tables. Grown files are relocated automatically.").grid(
            row=1, column=0, sticky="w", pady=(2, 16))

        paths = ttk.Frame(outer)
        paths.grid(row=2, column=0, sticky="ew")
        paths.columnconfigure(1, weight=1)
        self.add_path_row(paths, 0, "Original ELF", self.elf_var, self.browse_elf)
        self.add_path_row(paths, 1, "Unpacked dir", self.unpack_var, self.browse_unpack)
        self.add_path_row(paths, 2, "Output ELF", self.out_var, self.browse_out)
        self.add_path_row(paths, 3, "Host prefix", self.prefix_var, None)

        action = ttk.Frame(outer)
        action.grid(row=3, column=0, sticky="ew", pady=(16, 12))
        action.columnconfigure(1, weight=1)
        self.update_btn = ttk.Button(action, text="Update TOCs",
                                     style="Accent.TButton", command=self.start_update)
        self.update_btn.grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(action, style="Heat.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100)
        self.progress.grid(row=0, column=1, sticky="ew", padx=(16, 0))

        self.status = ttk.Label(outer, text="Ready.", style="Status.TLabel")
        self.status.grid(row=4, column=0, sticky="w", pady=(0, 12))

        self.tiles = {}
        tilerow = ttk.Frame(outer)
        tilerow.grid(row=5, column=0, sticky="ew")
        specs = [("served", "Served"), ("relocated", "Relocated"),
                 ("shrunk", "Shrunk"), ("unchanged", "Unchanged"),
                 ("unsupported", "Unsupported"), ("missing", "Missing")]
        for i, (key, label) in enumerate(specs):
            tilerow.columnconfigure(i, weight=1)
            self.tiles[key] = self.make_tile(tilerow, i, label)

        logframe = ttk.Frame(outer)
        logframe.grid(row=6, column=0, sticky="nsew", pady=(16, 0))
        outer.rowconfigure(6, weight=1)
        logframe.columnconfigure(0, weight=1)
        logframe.rowconfigure(0, weight=1)
        self.log = tk.Text(logframe, height=12, wrap="word", relief="flat",
                           background=LOG_BG, foreground=TEXT,
                           insertbackground=TEXT, font=("Consolas", 9),
                           padx=12, pady=10, highlightthickness=1,
                           highlightbackground=SOFT, highlightcolor=ACCENT)
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(logframe, command=self.log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set, state="disabled")
        self.log.tag_configure("ok", foreground=OK)
        self.log.tag_configure("warn", foreground=WARN)
        self.log.tag_configure("err", foreground=ERR)
        self.log.tag_configure("head", foreground=ACCENT_DKR,
                               font=("Consolas", 9, "bold"))
        self.log.tag_configure("muted", foreground=MUTED)

    def add_path_row(self, parent, row, label, var, browse, hint=None):
        ttk.Label(parent, text=label, style="Field.TLabel").grid(
            row=row * 2, column=0, sticky="w", pady=(6, 1), padx=(0, 10))
        entry = ttk.Entry(parent, textvariable=var, font=FONT)
        entry.grid(row=row * 2, column=1, sticky="ew", pady=(6, 1))
        if browse is not None:
            ttk.Button(parent, text="Browse", style="Browse.TButton",
                       command=browse).grid(row=row * 2, column=2, padx=(8, 0))
        if hint:
            ttk.Label(parent, text=hint, style="Sub.TLabel").grid(
                row=row * 2 + 1, column=1, sticky="w")

    def make_tile(self, parent, col, label):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(10, 12))
        card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
        value = ttk.Label(card, text="-", style="TileValue.TLabel", anchor="center")
        value.pack(fill="x")
        ttk.Label(card, text=label, style="TileKey.TLabel", anchor="center").pack(fill="x")
        return value

    def write_log(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", (tag,) if tag else ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def browse_elf(self):
        path = filedialog.askopenfilename(title="Select the original SLUS_200.79",
                                          initialdir=GAME_DIR)
        if path:
            self.elf_var.set(path)

    def browse_unpack(self):
        path = filedialog.askdirectory(title="Select unpacked_linkdata",
                                       initialdir=GAME_DIR)
        if path:
            self.unpack_var.set(path)

    def browse_out(self):
        path = filedialog.asksaveasfilename(title="Output hostfs ELF",
                                            initialdir=GAME_DIR,
                                            defaultextension=".elf")
        if path:
            self.out_var.set(path)

    def start_update(self):
        if self.worker and self.worker.is_alive():
            return
        elf = Path(self.elf_var.get())
        unpack = Path(self.unpack_var.get())
        out = Path(self.out_var.get())

        if not elf.is_file():
            messagebox.showerror("Missing ELF", "Original ELF not found:\n%s" % elf)
            return
        if not (unpack / "toc_entries.txt").is_file():
            messagebox.showerror("Missing TOC",
                                 "toc_entries.txt not found in:\n%s" % unpack)
            return
        if out.resolve() == elf.resolve():
            messagebox.showerror("Bad output",
                                 "Output must differ from the original ELF or the "
                                 "pristine copy would be destroyed.")
            return

        prefixes = None
        if self.prefix_var.get().strip():
            prefixes = [self.prefix_var.get().strip()]

        self.clear_log()
        for tile in self.tiles.values():
            tile.configure(text="-")
        self.progress["value"] = 0
        self.update_btn.state(["disabled"])
        self.status.configure(text="Working")
        self.write_log("Building %s" % out.name, "head")

        self.worker = threading.Thread(
            target=self.run_build, args=(elf, unpack, out, prefixes), daemon=True)
        self.worker.start()

    def run_build(self, elf, unpack, out, prefixes):
        def progress(message, frac):
            self.queue.put(("progress", frac, message))
        try:
            report = patchmod.build_hostfs_elf(
                elf, unpack / "toc_entries.txt", unpack, out,
                prefixes=prefixes, progress=progress)
            self.queue.put(("done", report))
        except patchmod.BuildError as exc:
            self.queue.put(("error", str(exc)))
        except Exception:
            self.queue.put(("error", traceback.format_exc()))

    def poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, frac, message = item
                    if frac is not None:
                        self.progress["value"] = round(frac * 100)
                    self.status.configure(text=message)
                    self.write_log("  " + message, "muted")
                elif kind == "done":
                    self.on_done(item[1])
                elif kind == "error":
                    self.on_error(item[1])
        except queue.Empty:
            pass
        self.root.after(80, self.poll_queue)

    def on_done(self, report):
        self.progress["value"] = 100
        self.update_btn.state(["!disabled"])
        unsupported = len(report["direct_grown"]) + len(report["sound_changed"])
        self.tiles["served"].configure(text=str(report["served"]))
        self.tiles["relocated"].configure(text=str(report["relocated_count"]))
        self.tiles["shrunk"].configure(text=str(len(report["shrunk"])))
        self.tiles["unchanged"].configure(text=str(len(report["unchanged"])))
        self.tiles["unsupported"].configure(text=str(unsupported))
        self.tiles["missing"].configure(text=str(len(report["missing"])))

        self.write_log("")
        if report.get("select_loader_addr"):
            self.write_log("Select model loader: table driven, relocated to 0x%08X."
                           % report["select_loader_addr"], "head")
            self.write_log("  The officer block now sizes itself from model_file_sec / "
                           "face_mot_sec, so a ported model may be any size.", "ok")
            self.write_log("")

        if report["relocated"]:
            self.write_log("Relocated to the sector arena "
                           "(a grown file moves its whole contiguous run):", "head")
            for rel, orig, new in report["relocated"]:
                self.write_log("  %-42s %d -> %d sectors (+%d)"
                               % (rel, orig, new, new - orig), "ok")
        else:
            self.write_log("No files grew past their original size, nothing to "
                           "relocate.", "ok")

        if report["direct_grown"]:
            self.write_log("")
            self.write_log("UNSUPPORTED growth (offset baked into code tail "
                           "ignored ingame):", "warn")
            for rel in report["direct_grown"]:
                self.write_log("  " + rel, "warn")
        if report["sound_changed"]:
            self.write_log("")
            self.write_log("UNSUPPORTED sound change (IOP side .bd/.hd, rebuild the "
                           "ISO's LINKDATA to apply):", "warn")
            for rel in report["sound_changed"]:
                self.write_log("  " + rel, "warn")
        if report["missing"]:
            self.write_log("")
            self.write_log("%d TOC files absent from disk, served from the mounted "
                           "disc instead." % len(report["missing"]), "muted")

        self.write_log("")
        self.write_log("Wrote %s" % report["out"], "head")
        self.write_log("blob 0x%X below the stack, relocation arena starts at sector "
                       "0x%X." % (report["blob_size"], report["arena_base"]), "muted")
        self.status.configure(
            text="Done, %d served, %d relocated%s."
            % (report["served"], report["relocated_count"],
               (", %d unsupported" % unsupported) if unsupported else ""))

    def on_error(self, message):
        self.progress["value"] = 0
        self.update_btn.state(["!disabled"])
        self.status.configure(text="Failed.")
        self.write_log("")
        self.write_log("BUILD FAILED", "err")
        for line in message.rstrip().splitlines():
            self.write_log("  " + line, "err")
        messagebox.showerror("Build failed", message.strip().splitlines()[-1]
                             if message.strip() else "Unknown error")


def main():
    root = tk.Tk()
    TocUpdaterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
