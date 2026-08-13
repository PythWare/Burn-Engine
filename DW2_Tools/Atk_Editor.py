# DW2_Tools/Atk_Editor.py
"""
ATK combo graph editor
"""

from .Move_Common import MoveGraphEditor, BURN_MV, mix


class AtkEditor(MoveGraphEditor):
    EXT = ".ATK"
    MOD_EXT = ".DW2AtkMod"
    RECORD_SIZE = 32
    FIXED_COUNT = 64
    WINDOW_TITLE = "Emberchain"
    HEADER_TITLE = "ATK Combo Graph"
    HEADER_SUB = "Editor for ATK files"
    GRAPH_TITLE = "Combo Graph"
    DETAIL_TITLE = "Attack Node"
    NEUTRAL_LABEL = "Neutral"

    FIELD_SPECS = [
        {"key": "cmd", "label": "Combo Command", "off": 0x00, "size": 4, "signed": True},
        {"key": "flags", "label": "Flags", "off": 0x04, "size": 2, "kind": "flags",
         "bits": [(0, "draw locus"), (1, "clash/parry"), (2, "combo cond 2"),
                  (3, "live/hit-downed"), (4, "target filter"),
                  (5, "combo cond 5"), (6, "combo cond 6"),
                  (7, "not combo-scannable"), (8, "fixed damage"),
                  (9, "KO camera"), (10, "combo cond"), (11, "alt hit anim"),
                  (12, "2x range"), (13, "combo cond 13"),
                  (14, "2x damage"), (15, "no target switch")]},
        {"key": "src", "label": "Source Motion", "off": 0x06, "size": 1,
         "note": "chains from this motion id (0=neutral, 128+=another attack)"},
        {"key": "window", "label": "Combo Window", "off": 0x07, "size": 1,
         "note": "frames the combo input is accepted (255=none)"},
        {"key": "part", "label": "Weapon-Part Mask", "off": 0x08, "size": 1,
         "note": "two nibbles, one per part slot: 0=unused, 1=weapon sweep, "
                 "N>1=bone from gHitPartID[N-1] (enter 0x.. for hex)"},
        {"key": "power", "label": "Attack Power", "off": 0x09, "size": 1},
        {"key": "hit_start", "label": "Hit Window Start", "off": 0x0A, "size": 1,
         "note": "255 = non-damaging move"},
        {"key": "hit_end", "label": "Hit Window End", "off": 0x0B, "size": 1},
        {"key": "knock", "label": "Knockback / Launch", "off": 0x0D, "size": 1, "signed": True},
        {"key": "push_x", "label": "Push X/Z", "off": 0x10, "size": 1, "signed": True},
        {"key": "push_y", "label": "Push Y (height)", "off": 0x11, "size": 1, "signed": True},
        {"key": "hit_anim", "label": "Hit-React Anim", "off": 0x12, "size": 1},
        {"key": "hit_anim_alt", "label": "Hit-React Anim (air)", "off": 0x14, "size": 1},
        {"key": "voice", "label": "Attack Voice Type", "off": 0x15, "size": 1},
        {"key": "voice_frame", "label": "Voice Frame", "off": 0x16, "size": 1},
        {"key": "fx_start", "label": "Weapon-FX Start Frame", "off": 0x18, "size": 1},
        {"key": "fixed_dmg", "label": "Fixed Damage", "off": 0x1C, "size": 4,
         "note": "used only when flag bit8 is set"},
    ]

    def is_used(self, index, rec):
        return any(rec)

    def edges_for(self, index, rec):
        src = rec[0x06]
        if src == 0:
            return ["N"]
        if 128 <= src <= 191:
            return [src - 128]
        return [f"m{src}"]

    def node_label(self, index, rec):
        cmd = rec[0]
        if cmd >= 0x80:
            cmd -= 0x100
        return (f"#{index} m{index + 128}", f"cmd {cmd}  pow {rec[9]}")

    def node_color(self, index, rec):
        power = rec[9]
        damaging = rec[0x0A] != 255 and power > 0
        if damaging:
            return mix(BURN_MV["panel_2"], BURN_MV["orange"], min(power / 40.0, 1.0) * 0.6)
        return BURN_MV["panel_2"]

    def node_head_text(self, index, rec):
        head = f"ATK #{index} motion {index + 128}"
        if index == 0:
            head += "  (also the shared neutral record)"
        if rec[0x04] & 0x80:
            head += "  [not combo-scannable]"
        return head
