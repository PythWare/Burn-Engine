# DW2_Tools/Mov_Editor.py
"""
MOV motion-chain graph editor
"""

from .Move_Common import MoveGraphEditor, BURN_MV, mix

class MovEditor(MoveGraphEditor):
    EXT = ".MOV"
    MOD_EXT = ".DW2MovMod"
    RECORD_SIZE = 16
    FIXED_COUNT = None
    WINDOW_TITLE = "Emberflow"
    HEADER_TITLE = "MOV Motion Graph"
    HEADER_SUB = "Editor for MOV files"
    GRAPH_TITLE = "Motion Chain"
    DETAIL_TITLE = "Motion Node"

    FIELD_SPECS = [
        {"key": "flags", "label": "Behavior Flags", "off": 0x00, "size": 4, "kind": "flags",
         "bits": [(5, "terrain gate"), (7, "flag 7"), (10, "movement physics"),
                  (14, "dir/interp"), (19, "chain gate"), (20, "common-motion src"),
                  (23, "flag 23"), (27, "flag 27")]},
        {"key": "clip", "label": "Animation Clip id", "off": 0x04, "size": 4,
         "note": "clip id, not .MOT block index"},
        {"key": "next_move", "label": "Default Next Move", "off": 0x08, "size": 1,
         "note": "motion id to auto advance to when this finishes"},
        {"key": "delay", "label": "Transition Delay", "off": 0x09, "size": 1},
        {"key": "sfx", "label": "Sound Effect id", "off": 0x0A, "size": 2,
         "note": "0 = silent"},
        {"key": "sfx_frame", "label": "SFX Trigger Frame", "off": 0x0C, "size": 2,
         "note": "used when int == this, 255 on silent moves"},
    ]

    def is_used(self, index, rec):
        return any(rec)

    def edges_for(self, index, rec):
        srcs = []
        for j, r in enumerate(self.records):
            if j == index or not self.is_used(j, r):
                continue
            if r[0x08] == index:
                srcs.append(j)
        return srcs

    def node_label(self, index, rec):
        clip = int.from_bytes(rec[4:8], "little")
        return (f"motion {index}", f"clip {clip} {rec[0x08]}")

    def node_color(self, index, rec):
        if index >= 128:                 # attack motions
            return mix(BURN_MV["panel_2"], BURN_MV["orange"], 0.35)
        return BURN_MV["panel_2"]

    def node_head_text(self, index, rec):
        kind = "attack" if index >= 128 else "basic"
        return f"MOV motion {index}  ({kind})"
