import os, io, struct, shutil, json, random, math, copy, colorsys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from .Utility import HOSTFS_ELF, MODS_DIR, STAGE_DIRS

# Configs and data maps

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_stage_side_file(stage_dir, suffix):
    """Find the loose file ending in .ub0/.ub1 inside a stage's hostfs dir"""
    if not os.path.isdir(stage_dir):
        return None
    suffix = suffix.lower()
    for name in os.listdir(stage_dir):
        if name.lower().endswith(suffix):
            return os.path.join(stage_dir, name)
    return None

LILAC = "#C8A2C8"
LILAC_LIGHT = "#E6E6FA"
CYAN_BTN = "#BF98D9"
GOLD_BTN = "#BF98D9"
ORANGE_BTN = "#ff8a1e"

DW2_STAGE_MOD_EXT = ".DW2StageMod"

BURN_UI = {
    "void": "#080504",
    "coal": "#120805",
    "panel": "#BF98D9",
    "panel_2": "#d7b7e8",
    "panel_3": "#6f111c",
    "line": "#8d2132",
    "line_hot": "#ff3b3b",
    "gold": "#ffd23c",
    "orange": "#ff8a1e",
    "red": "#ff3b3b",
    "blue": "#5b8def",
    "green": "#78bf8d",
    "teal": "#BF98D9",
    "purple": "#BF98D9",
    "lilac": "#BF98D9",
    "text": "#17070c",
    "header_text": "#ffe8b4",
    "muted": "#4a1d2a",
    "dark_text": "#0d0502",
    "entry": "#ead6f3",
    "entry_text": "#17070c",
}

MAP_FILES = [
    "YellowTurban.png", "HuLaoGate.png", "GuanDu.png", "ChangBan.png", 
    "ChiBi.png", "HeFei.png", "YiLing1.png", "WuZhangPlains.png"
]

STAGE_NAMES = [
    "Yellow Turban Rebellion", "Hu Lao Gate", "Guan Du", "Chang Ban",
    "Chi Bi", "He Fei", "Yi Ling", "Wu Zhang Plains"
]

# Format: Stage Name: { Side_ID: (File_Offset, Count_of_Chunks) }
STAGE_MORALE_DATA = {
    "Yellow Turban Rebellion": {
        1: (0x16FB52, 11), 
        2: (0x16FB6A, 11)
    },
    "Hu Lao Gate": {
        1: (0x16FC62, 11), 
        2: (0x16FC7A, 11)
    },
    "Guan Du": {
        1: (0x16FD72, 11), 
        2: (0x16FD8A, 11)
    },
    "Chang Ban": {
        1: (0x16FE82, 11), 
        2: (0x16FE9A, 11)
    },
    "Chi Bi": {
        1: (0x16FF92, 11), 
        2: (0x16FFAA, 11)
    },
    "He Fei": {
        1: (0x1700A2, 11), 
        2: (0x1700BA, 11)
    },
    "Yi Ling": {
        1: (0x1701B2, 11), 
        2: (0x1701CA, 11)
    },
    "Wu Zhang Plains": {
        1: (0x1702C2, 11), 
        2: (0x1702DA, 11)
    }
}

# Zone Schemas for procedural generation
STAGES_ZONES = {
    "Yellow Turban Rebellion": {
        "Side 1": [
            {"name": "Top Left", "rect": (51, 551, 157, 631)},
            {"name": "Top Left Mid", "rect": (79, 487, 201, 558)},
            {"name": "Top Left Mid Right", "rect": (151, 429, 286, 534)},
            {"name": "Center", "rect": (307, 209, 521, 529)},
            {"name": "Bottom Left 1", "rect": (56, 120, 229, 192)},
            {"name": "Bottom Left 2", "rect": (187, 199, 286, 342)},
            {"name": "Bottom Right", "rect": (318, 100, 528, 187)}
        ],
        "Side 2": [
            {"name": "Top Left", "rect": (51, 551, 157, 631)},
            {"name": "Top Left Mid", "rect": (79, 487, 201, 558)},
            {"name": "Top Left Mid Right", "rect": (151, 429, 286, 534)},
            {"name": "Center", "rect": (307, 209, 521, 529)},
            {"name": "Top Right 1", "rect": (466, 666, 540, 689)},
            {"name": "Top Right 2", "rect": (633, 635, 743, 733)},
            {"name": "Top Right 3", "rect": (713, 561, 740, 594)},
            {"name": "Top Right 4", "rect": (646, 558, 690, 571)}
        ]
},
	"Hu Lao Gate": {
        "Side 1": [
            {"name": "Top Gate 1", "rect": (557, 731, 575, 750)},
            {"name": "Top Gate 2", "rect": (610, 722, 638, 750)},
            {"name": "Top Near Gate 1", "rect": (498, 720, 541, 734)},
            {"name": "Top Near Gate 2", "rect": (545, 693, 594, 729)},
            {"name": "Top Near Gate 3", "rect": (625, 707, 658, 737)},
            {"name": "Top Right 1", "rect": (667, 629, 721, 669)},
            {"name": "Orig Shu Area 1", "rect": (631, 595, 678, 642)},
	    {"name": "Orig Shu Area 2", "rect": (588, 520, 657, 584)},
            {"name": "Orig Wei Area 1", "rect": (715, 466, 730, 524)},
            {"name": "Orig Wei Area 2", "rect": (696, 378, 731, 412)},
            {"name": "Orig Wei Area Near Gate", "rect": (669, 339, 715, 375)},
            {"name": "Orig Wu Gate", "rect": (259, 732, 284, 749)},
            {"name": "Orig Wu Area 1", "rect": (242, 715, 328, 734)},
            {"name": "Orig Wu Area 2", "rect": (254, 669, 274, 710)},
	    {"name": "Contested 1", "rect": (366, 602, 416, 640)},
            {"name": "Contested 2", "rect": (417, 583, 435, 619)},
            {"name": "Contested 3", "rect": (159, 612, 216, 630)}
        ],
        "Side 2": [
            {"name": "Bottom Castle", "rect": (135, 66, 230, 99)},
            {"name": "Bottom Castle Gates", "rect": (166, 50, 237, 68)},
            {"name": "Bottom Castle Walls", "rect": (143, 105, 223, 116)},
            {"name": "front of Castle 1", "rect": (125, 120, 220, 157)},
            {"name": "Orig Lu Bu Area", "rect": (141, 193, 226, 216)},
            {"name": "Lu Bu Gate Area", "rect": (110, 215, 145, 235)},
            {"name": "Zhang Liao Area 1", "rect": (131, 228, 165, 286)},
	    {"name": "Zhang Liao Area 2", "rect": (135, 266, 207, 334)},
            {"name": "Behind Mid Castle", "rect": (240, 292, 301, 314)},
            {"name": "Mid Castle Gate 1", "rect": (356, 368, 398, 380)},
            {"name": "Mid Castle Tent Area", "rect": (286, 373, 358, 393)},
            {"name": "Mid Castle Walls", "rect": (284, 419, 359, 435)},
            {"name": "Center Area", "rect": (312, 489, 357, 507)},
            {"name": "Shu Gate", "rect": (565, 422, 589, 483)},
	    {"name": "Wu Gate", "rect": (129, 559, 187, 588)},
            {"name": "Wei Gate 1", "rect": (506, 119, 538, 170)},
            {"name": "Wei Gate 2", "rect": (361, 238, 394, 284)},
            {"name": "Contested 1", "rect": (366, 602, 416, 640)},
            {"name": "Contested 2", "rect": (417, 583, 435, 619)},
            {"name": "Contested 3", "rect": (159, 612, 216, 630)},
            {"name": "Contested 4", "rect": (617, 304, 671, 349)}
        ]
    },
    "Guan Du": {
        "Side 1": [
            {"name": "Cao Castle", "rect": (550, 108, 687, 242)},
            {"name": "Cao Castle Behind", "rect": (706, 124, 737, 258)},
            {"name": "Cao Castle Top", "rect": (621, 263, 740, 282)},
            {"name": "Bottom Center 1", "rect": (306, 204, 535, 239)},
            {"name": "Bottom Center 2", "rect": (307, 149, 539, 186)},
            {"name": "Bottom Center 3", "rect": (510, 72, 629, 92)},
            {"name": "Bottom Right", "rect": (318, 100, 528, 187)},
	    {"name": "Cao Mid 1", "rect": (437, 409, 679, 437)},
            {"name": "Cao Mid 2", "rect": (622, 457, 675, 517)},
            {"name": "Wei Top Castle", "rect": (600, 601, 695, 695)},
            {"name": "Wei Top Mid", "rect": (357, 614, 451, 691)},
            {"name": "Contested 1", "rect": (532, 626, 586, 739)},
            {"name": "Contested 2", "rect": (411, 503, 480, 541)},
            {"name": "Contested 3", "rect": (402, 466, 485, 488)}
],
        "Side 2": [
            {"name": "Yuan Castle", "rect": (105, 107, 301, 252)},
            {"name": "Yuan Castle Left", "rect": (67, 66, 97, 183)},
            {"name": "Yuan Castle Below", "rect": (98, 70, 304, 97)},
            {"name": "Yuan Castle Right", "rect": (306, 67, 341, 240)},
            {"name": "Yuan Castle Top", "rect": (170, 261, 287, 342)},
            {"name": "Yuan Mid", "rect": (339, 444, 383, 520)},
            {"name": "Yuan Mid Left", "rect": (62, 366, 223, 475)},
            {"name": "Yuan Top Left", "rect": (172, 693, 280, 740)},
	    {"name": "Yuan Top Under", "rect": (105, 603, 279, 632)},
            {"name": "Yuan Top Over", "rect": (255, 688, 344, 740)},
	    {"name": "Contested 1", "rect": (532, 626, 586, 739)},
            {"name": "Contested 2", "rect": (411, 503, 480, 541)},
            {"name": "Contested 3", "rect": (402, 466, 485, 488)}
        ]
    },
    "Chang Ban": {
        "Side 1": [
            {"name": "Top Right 1", "rect": (636, 623, 746, 711)},
            {"name": "Top Right 2", "rect": (564, 686, 652, 747)},
            {"name": "Contested 1", "rect": (454, 656, 570, 730)},
            {"name": "Bottom Right 1", "rect": (431, 233, 541, 337)},
            {"name": "Bottom Right 2", "rect": (449, 271, 547, 377)},
            {"name": "Bottom Left 1", "rect": (212, 217, 381, 345)},
            {"name": "Mid Left", "rect": (157, 411, 195, 516)},
	    {"name": "Contested 2", "rect": (160, 565, 220, 621)},
	    {"name": "Contested Right", "rect": (513, 582, 533, 648)},
            {"name": "Contested Left 1", "rect": (70, 52, 88, 199)},
	    {"name": "Contested Left 2", "rect": (70, 52, 88, 199)}
],
        "Side 2": [
            {"name": "Top Left", "rect": (165, 666, 187, 729)},
            {"name": "Top Left Mid", "rect": (60, 462, 145, 494)},
            {"name": "Mid", "rect": (313, 357, 364, 430)},
            {"name": "Bottom Right", "rect": (608, 210, 643, 264)},
            {"name": "Right 1", "rect": (611, 281, 639, 315)},
            {"name": "Right 2", "rect": (672, 339, 689, 389)},
            {"name": "Right 3", "rect": (610, 378, 688, 389)},
            {"name": "Right 4", "rect": (601, 413, 692, 439)},
	    {"name": "Right 5", "rect": (625, 500, 682, 523)},
            {"name": "Right 6", "rect": (527, 561, 678, 586)},
            {"name": "Contested Right", "rect": (513, 582, 533, 648)},
            {"name": "Right 4", "rect": (601, 413, 692, 439)},
            {"name": "Contested Left 1", "rect": (70, 52, 88, 199)},
	    {"name": "Contested Left 2", "rect": (70, 52, 88, 199)}
        ]
    },
    "Chi Bi": {
        "Side 1": [
            {"name": "South left", "rect": (65, 115, 171, 167)},
            {"name": "South Half", "rect": (66, 164, 585, 193)},
            {"name": "South Camp", "rect": (266, 113, 367, 153)},
            {"name": "South Right", "rect": (577, 110, 725, 138)},
            {"name": "South Ships", "rect": (207, 177, 700, 293)},
            {"name": "Contested 1", "rect": (594, 355, 735, 631)}
],
        "Side 2": [
            {"name": "Cao Zone", "rect": (255, 407, 408, 685)},
            {"name": "Cao L1 Fleet", "rect": (107, 258, 143, 642)},
            {"name": "Cao L2 Fleet", "rect": (156, 408, 243, 588)},
            {"name": "Cao B1 Fleet", "rect": (256, 408, 394, 442)},
            {"name": "Cao R1 Fleet", "rect": (406, 358, 493, 588)},
            {"name": "Cao R2 Fleet", "rect": (558, 458, 642, 540)},
	    {"name": "Cao TR Def", "rect": (584, 552, 704, 630)}
        ]
    },
    	"He Fei": {
        "Side 1": [
            {"name": "B Left", "rect": (57, 66, 270, 395)},
            {"name": "T Left 1", "rect": (121, 653, 166, 694)},
            {"name": "T Left 2", "rect": (114, 414, 172, 476)},
            {"name": "T Left 3", "rect": (257, 367, 341, 505)},
            {"name": "B Right 1", "rect": (396, 127, 636, 175)},
            {"name": "B Right 2", "rect": (673, 168, 750, 191)},
            {"name": "Contested 1", "rect": (301, 84, 393, 239)},
	    {"name": "Contested 2", "rect": (552, 377, 694, 480)},
	    {"name": "Contested 3", "rect": (269, 655, 476, 714)},
            {"name": "Contested 4", "rect": (361, 314, 441, 448)}
],
        "Side 2": [
            {"name": "T Right", "rect": (501, 503, 750, 749)},
            {"name": "T R2", "rect": (367, 563, 477, 640)},
            {"name": "T R3", "rect": (462, 376, 543, 476)},
            {"name": "T R4", "rect": (527, 211, 581, 321)},
            {"name": "Contested 1", "rect": (301, 84, 393, 239)},
	    {"name": "Contested 2", "rect": (552, 377, 694, 480)},
	    {"name": "Contested 3", "rect": (269, 655, 476, 714)},
            {"name": "Contested 4", "rect": (361, 314, 441, 448)}
        ]
    },
    "Yi Ling": {
        "Side 1": [
	    {"name": "Base", "rect": (568, 43, 733, 187)},
            {"name": "C1", "rect": (392, 360, 644, 558)},
            {"name": "C2", "rect": (350, 102, 445, 354)},
            {"name": "FR1", "rect": (504, 297, 800, 548)},
            {"name": "Boats", "rect": (618, 590, 784, 698)},
            {"name": "Contested 1", "rect": (220, 640, 456, 754)},
            {"name": "Contested 2", "rect": (648, 473, 762, 603)},
            {"name": "Contested 3", "rect": (414, 85, 592, 280)}
],
        "Side 2": [
            {"name": "Top Left", "rect": (67, 629, 229, 733)},
            {"name": "Top Left Mid", "rect": (42, 402, 247, 617)},
            {"name": "Top Left Mid Right", "rect": (226, 492, 409, 629)},
            {"name": "B Left", "rect": (185, 100, 342, 402)},
            {"name": "Contested 1", "rect": (220, 640, 456, 754)},
            {"name": "Contested 2", "rect": (648, 473, 762, 603)},
            {"name": "Contested 3", "rect": (414, 85, 592, 280)}
        ]
    },
    	"Wu Zhang Plains": {
        "Side 1": [
            {"name": "BL", "rect": (126, 157, 196, 353)},
            {"name": "Base Area", "rect": (208, 62, 629, 395)},
            {"name": "BR 1", "rect": (555, 274, 725, 360)},
            {"name": "BR 2", "rect": (604, 157, 684, 266)},
            {"name": "Contested 1", "rect": (576, 417, 746, 538)},
            {"name": "Contested 2", "rect": (592, 659, 691, 734)}
],
        "Side 2": [
            {"name": "Base", "rect": (314, 677, 438, 738)},
            {"name": "Top Left", "rect": (45, 506, 195, 690)},
            {"name": "Top Left Mid", "rect": (334, 517, 417, 538)},
            {"name": "Top Left Mid Right", "rect": (458, 511, 531, 532)},
            {"name": "Center", "rect": (353, 477, 400, 494)},
            {"name": "M Right 1", "rect": (466, 666, 540, 689)}
        ]
    }
}

UNIT_DIR = [
    ("North", 0), ("North East", 1), ("East", 2), ("South East", 3),
    ("South", 4), ("South West", 5), ("West", 6), ("North West", 7)
]

UNIT_TYPES = [
    ("Player", 0), ("Commander", 1), ("General", 2), ("Playable Officer", 3),
    ("NPC Officer", 4), ("Gate C./Troops", 5), ("Troops (respawns)", 6)
]

AI_TYPES = [
    ("Ranged", 2), ("Cavalry", 4)
]

ORDER_TYPES = [
    ("Attack Enemy", 1), ("Follow Ally", 3), ("Hold Position", 4)
]

UNIT_DATA_FIELDS = [
    ("Pos X", "x", 0, 2), ("Pos Y", "y", 2, 2), ("Direction", "dir", 4, 1),
    ("Pathing", "path", 5, 1), ("Gate Mode", "gate_mode", 6, 1), ("Life", "life", 8, 2),
    ("Leader ID", "leader", 10, 1), ("Guard ID", "guard_id", 11, 1), ("Attack", "atk", 12, 1),
    ("Defense", "def", 13, 1), ("Guard Count(9 is max)", "guard_cnt", 14, 1), ("Serves Slot", "own_slot", 15, 1),
    ("Unit Type", "type", 16, 1), ("AI Type", "ai_type", 17, 1), ("Orders", "orders", 18, 1),
    ("Hidden", "hidden", 19, 1), ("Order Tgt", "target", 21, 1), ("Item Drop", "drop", 22, 1),
    ("AI Level", "ai_lvl", 23, 1), ("Delay", "delay", 24, 2), ("Kill Pts", "points", 26, 2),
]

UNIT_LIMITS = {
    "x": 800, "y": 800, "dir": 255, "path": 255, "gate_mode": 255, "life": 3000,
    "leader": 255, "guard_id": 255, "atk": 255, "def": 255, "guard_cnt": 9, "own_slot": 511,
    "type": 255, "ai_type": 255, "orders": 255, "hidden": 255, "target": 511, "drop": 255,
    "ai_lvl": 255, "delay": 65535, "points": 65535,
}

UNIT_NAMES = {
    0: "Zhao Yun", 1: "Guan Yu", 2: "Zhang Fei", 3: "Xiahou Dun", 4: "Dian Wei", 5: "Xu Zhu",
    6: "Zhou Yu", 7: "Lu Xun", 8: "Taishi Ci", 9: "Diao Chan", 10: "Zhuge Liang", 11: "Cao Cao",
    12: "Lu Bu", 13: "Sun Shang Xiang", 14: "Liu Bei", 15: "Sun Jian", 16: "Sun Quan", 17: "Dong Zhuo",
    18: "Yuan Shao", 19: "Ma Chao", 20: "Huang Zhong", 21: "Xiahou Yuan", 22: "Zhang Liao", 23: "Sima Yi",
    24: "Lu Meng", 25: "Gan Ning", 26: "Jiang Wei", 27: "Zhang Jiao", 28: "Cao Ren", 29: "Cheng Pu",
    30: "Huang Gai", 31: "Han Dang", 32: "Zhang Bao", 33: "Zhang Liang", 34: "Zhang Man Cheng", 35: "Bo Zhang",
    36: "Cao Hong", 37: "Yan Liang", 38: "Wen Chou", 39: "Zhang He", 40: "Gongsun Zan", 41: "Hua Xiong",
    42: "Xu Rong", 43: "Gao Shun", 44: "Li Ru", 45: "Li Jue", 46: "Jia Xu", 47: "Guo Si", 48: "Hu Zhen",
    49: "Xu Huang", 50: "Yu Jin", 51: "Chun Yuqiong", 52: "Yue Jin", 53: "Li Dian", 54: "Xiahou En",
    55: "Cheng Yu", 56: "Xun You", 57: "Zhou Tai", 58: "Ling Tong", 59: "Xu Sheng", 60: "Ding Feng",
    61: "Pang De", 62: "Huang Quan", 63: "Guan Xing", 64: "Zhang Bao", 65: "Shamoke", 66: "Deng Ai",
    67: "Zhong Hui", 68: "Wei Yan", 69: "Ma Dai", 70: "Guan Suo", 71: "Yuan Tan", 72: "Yuan Xi",
    73: "Yuan Shang", 74: "Ju Shou", 75: "Gao Lan", 76: "Zhao Cen", 77: "Niou Fu", 78: "Fan Chou",
    79: "Wang Fang", 80: "Li Meng", 81: "He Jin", 82: "Zhu Jun", 83: "Lu Zhi", 84: "Huangfu Song",
    85: "Zhang Chao", 86: "Liu Yan", 87: "Zou Ying", 88: "Cheng Yuanzhi", 89: "Deng Mao", 90: "Guan Hai",
    91: "Pei Yuan Shao", 92: "He Yi", 93: "Yan Zheng", 94: "Gao Sheng", 95: "Liu Yan", 96: "Song Xian",
    97: "Wei Xu", 98: "Dong Xi", 99: "Lu Wei Kuang", 100: "Xun Chen", 101: "Han Meng", 102: "Han Xun",
    103: "Zhou Cang", 104: "Guan Ping", 105: "Sun Qian", 106: "Mi Zhu", 107: "Mi Fang", 108: "Liu Feng",
    109: "Chen Dao", 110: "Liao Hua", 111: "Liu Qi", 112: "Cao Pi", 113: "Cao Zhang", 114: "Zhu Huan",
    115: "Zhu Ran", 116: "Jiang Qin", 117: "Dong Xi", 118: "Pan Zhang", 119: "Yan Yan", 120: "Wu Lan",
    121: "Lei Tong", 122: "Zhang Ji", 123: "Zhu Ran", 124: "Jiang Qin", 125: "Dong Xi", 126: "Pan Zhang",
    127: "Yan Yan", 128: "Private (Wei - sword)", 129: "Corporal(Sergeant) (Wei - sword)", 130: "Sergeant(Major) (Wei - sword)",
    131: "Private (Wei - spear)", 132: "Sergeant (Wei - spear)", 133: "Major (Wei - spear)", 134: "Corporal(Private) (Wei - pike)",
    135: "Sergeant (Wei - pike)", 136: "Major (Wei - pike)", 137: "Guard (Wei - sword)", 138: "Guard Captain (Wei - sword)",
    139: "Guard (Wei - spear)", 140: "Guard Captain (Wei - spear)", 141: "Guard (Wei - pike)", 142: "Guard Captain (Wei - pike)",
    143: "Bowman (Wei)", 144: "First bow (Wei)", 145: "Crossbow (Wei)", 146: "First Crossbow (Wei)", 147: "Gate Guard (Wei)",
    148: "Gate Captain (Wei)", 149: "Private (Wu - sword)", 150: "Sergeant (Wu - sword)", 151: "Major (Wu - sword)",
    152: "Private (Wu - spear)", 153: "Sergeant (Wu - spear)", 154: "Major (Wu - spear)", 155: "Private (Wu - pike)",
    156: "Sergeant (Wu - pike)", 157: "Major (Wu - pike)", 158: "Guard (Wu - sword)", 159: "Guard Captain (Wu - sword)",
    160: "Guard (Wu - spear)", 161: "Guard Captain (Wu - spear)", 162: "Guard (Wu - pike)", 163: "Guard Captain (Wu - pike)",
    164: "Bowman (Wu)", 165: "First Bow (Wu)", 166: "Crossbow (Wu)", 167: "F.Crossbow (Wu)", 168: "Gate guard (Wu)",
    169: "Gate Captain (Wu)", 170: "Private (Shu - sword)", 171: "Sergeant (Shu - sword)", 172: "Major (Shu - sword)",
    173: "Private (Shu - spear)", 174: "Sergeant (Shu - spear)", 175: "Major (Shu - spear)", 176: "Private (Shu - pike)",
    177: "Sergeant (Shu - pike)", 178: "Major (Shu - pike)", 179: "Guard (Shu - sword)", 180: "Guard Captain (Shu - sword)",
    181: "Guard (Shu - spear)", 182: "G.Captain (Shu - spear)", 183: "Guard (Shu - pike)", 184: "G.Captain (Shu - pike)",
    185: "Bowman (Shu)", 186: "First Bow (Shu)", 187: "Crossbow (Shu)", 188: "First Crossbow (Shu)", 189: "G.guard (Shu)",
    190: "Gate Captain (Shu)", 191: "Private (YS - sword)", 192: "Sergeant (YS - sword)", 193: "Major (YS - sword)",
    194: "Private (YS - spear)", 195: "Sergeant (YS - spear)", 196: "Major (YS - spear)?", 197: "Private (YS - pike)?",
    198: "Sergeant (YS - pike)?", 199: "Major (YS - pike)?", 200: "Guard (YS - sword)", 201: "G.Captain (YS - sword)",
    202: "Guard (YS - spear)", 203: "G.Captain (YS - spear)", 204: "Guard (YS - pike)", 205: "G.Captain (YS - pike)",
    206: "Bowman (YS)", 207: "First Bow (YS)", 208: "Crossbow (YS)", 209: "Catapult Chief (YS)", 210: "Gate Guard (YS)",
    211: "G.Captain (YS)", 212: "Private (Purple - sword)", 213: "Sergeant (Purple - sword)?", 214: "Major (Purple - sword)?",
    215: "Private (Purple - spear)?", 216: "Sergeant (Purple - spear)?", 217: "Major (Purple - spear)?", 218: "Private (Purple - pike)?",
    219: "Sergeant (Purple - pike)?", 220: "Major (Purple - pike)", 221: "Guard (Purple - sword)", 222: "G.captain (Purple - sword)",
    223: "Guard (Purple - spear)?", 224: "G.Captain (Purple - spear)?", 225: "Guard (Purple - pike)?", 226: "G.Captain (Purple - pike)",
    227: "Bowman (Purple)", 228: "First Bow (Purple)?", 229: "Crossbow (Purple)?", 230: "First Crossbow (Purple)",
    231: "Gate Guard (Purple)", 232: "G.Captain (Purple)", 233: "Trooper (YT - sword)", 234: "Trooper (YT - spear)",
    235: "Trooper (YT - pike)", 236: "Captain (YT - sword)", 237: "Captain (YT - spear)", 238: "Captain (YT - pike)",
    239: "General (YT - sword)", 240: "General (YT - spear)", 241: "General (YT - pike)", 242: "Bowman (YT)",
    243: "First bow (YT)", 244: "Bowman (YT)", 245: "First Bow (YT)", 246: "Gate guard (YT)", 247: "Gate Captain (YT)",
    248: "Lady Guard", 249: "Lady Guard", 250: "Lady Guard", 251: "Lady Captain", 252: "Lady Bowman",
    253: "First Lady Bow", 254: "Bodyguard"
}

def get_unit_name(idx):
    return UNIT_NAMES.get(idx, f"Unit ID {idx}")

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()

class DW2CoordinateGuider:
    def __init__(self, root):
        self.root = root
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.maps_dir = os.path.join(self.base_dir, "maps")
        os.makedirs(self.maps_dir, exist_ok=True)

        self.original_width = 800
        self.original_height = 800
        self.scale = 1.0
        self.zoom_level = 1.0
        self.view_padding_base = 360
       
        self.base_image = None
        self.current_pil_image = None 
        self.display_image = None
        self.image_id = None

        self.current_stage_index = 0
        self.slots = [] 
        self.markers = [] 
        
        self.selected_indices = set() 
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_rect_id = None
        self.dragging_unit_idx = None 
        
        self.show_guards_var = tk.BooleanVar(value=True)

        self.entry_vars = {}
        self.list_map = []
        self.ui_panels = []
        self.modname = tk.StringVar()

        self.setup_ui()
        self.load_stage_data(0)

    def setup_ui(self):
        self.root.title("Afterburn Stageworks")
        self.root.geometry("1700x950")
        self.root.configure(bg=BURN_UI["void"])
        self.setup_burn_styles()

        self.map_frame = tk.Frame(self.root, bg=BURN_UI["void"], highlightthickness=0)
        self.map_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.map_frame.grid_rowconfigure(0, weight=1)
        self.map_frame.grid_columnconfigure(0, weight=1)

        vbar = tk.Scrollbar(self.map_frame, orient=tk.VERTICAL)
        hbar = tk.Scrollbar(self.map_frame, orient=tk.HORIZONTAL)
        self.canvas = tk.Canvas(
            self.map_frame,
            bg=BURN_UI["void"],
            bd=0,
            highlightthickness=0,
            xscrollcommand=hbar.set,
            yscrollcommand=vbar.set,
        )
        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)

        self.build_control_deck()
        self.build_heads_up_panel()
        self.build_roster_panel()
        self.build_squad_editor_panel()
        self.build_legend_panel()
        self.lift_panels()

    def setup_burn_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Burn.TCombobox",
            fieldbackground=BURN_UI["entry"],
            background=BURN_UI["panel_3"],
            foreground=BURN_UI["entry_text"],
            arrowcolor=BURN_UI["header_text"],
            bordercolor=BURN_UI["line"],
            lightcolor=BURN_UI["line"],
            darkcolor=BURN_UI["line"],
            padding=4,
        )
        style.map(
            "Burn.TCombobox",
            fieldbackground=[("readonly", BURN_UI["entry"])],
            foreground=[("readonly", BURN_UI["entry_text"])],
        )

    def make_panel(self, title, x, y, width, height, accent=None):
        accent = accent or BURN_UI["orange"]
        panel = tk.Frame(
            self.root,
            bg=BURN_UI["panel"],
            highlightbackground=BURN_UI["line"],
            highlightcolor=accent,
            highlightthickness=1,
            bd=0,
        )
        panel.place(x=x, y=y, width=width, height=height)

        header = tk.Frame(panel, bg=BURN_UI["panel_3"], height=34, cursor="fleur")
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text=title,
            bg=BURN_UI["panel_3"],
            fg=BURN_UI["header_text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=12)
        tk.Label(
            header,
            text="Drag",
            bg=BURN_UI["panel_3"],
            fg=BURN_UI["header_text"],
            font=("Segoe UI", 8),
        ).pack(side=tk.RIGHT, padx=10)

        body = tk.Frame(panel, bg=BURN_UI["panel"], padx=10, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        def begin_drag(event):
            panel.lift()
            panel.drag_offset = (event.x_root - panel.winfo_x(), event.y_root - panel.winfo_y())

        def drag_panel(event):
            dx, dy = getattr(panel, "_drag_offset", (event.x, event.y))
            max_x = max(0, self.root.winfo_width() - panel.winfo_width() - 4)
            max_y = max(0, self.root.winfo_height() - panel.winfo_height() - 4)
            new_x = min(max(event.x_root - dx, 0), max_x)
            new_y = min(max(event.y_root - dy, 0), max_y)
            panel.place_configure(x=new_x, y=new_y)

        for widget in (panel, header):
            widget.bind("<ButtonPress-1>", begin_drag)
            widget.bind("<B1-Motion>", drag_panel)

        self.ui_panels.append(panel)
        return panel, body

    def lift_panels(self):
        for panel in getattr(self, "ui_panels", []):
            panel.lift()

    def burn_label(self, parent, text, **kwargs):
        options = {
            "bg": BURN_UI["panel"],
            "fg": BURN_UI["muted"],
            "font": ("Segoe UI", 9),
            "anchor": "w",
        }
        options.update(kwargs)
        return tk.Label(parent, text=text, **options)

    def burn_button(self, parent, text, command, accent=None, fg=None, **pack_kwargs):
        accent = accent or BURN_UI["panel_3"]
        fg = fg or BURN_UI["header_text"]
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=accent,
            fg=fg,
            activebackground=BURN_UI["gold"],
            activeforeground=BURN_UI["dark_text"],
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=7,
            cursor="hand2",
        )
        btn.pack(**pack_kwargs)
        return btn

    def burn_entry(self, parent, variable, width=14):
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            bg=BURN_UI["entry"],
            fg=BURN_UI["entry_text"],
            insertbackground=BURN_UI["gold"],
            relief=tk.FLAT,
            highlightbackground=BURN_UI["line"],
            highlightcolor=BURN_UI["gold"],
            highlightthickness=1,
            disabledbackground="#d2afd6",
            disabledforeground=BURN_UI["muted"],
            font=("Segoe UI", 9),
        )

    def burn_check(self, parent, text, variable, command):
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            bg=BURN_UI["panel"],
            fg=BURN_UI["text"],
            activebackground=BURN_UI["panel"],
            activeforeground=BURN_UI["gold"],
            selectcolor=BURN_UI["entry"],
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 9, "bold"),
        )

    def build_control_deck(self):
        panel, body = self.make_panel("Control Deck", 18, 18, 720, 200, BURN_UI["lilac"])

        self.lbl_hostfs_status = self.burn_label(
            body,
            self.hostfs_status_text(),
            fg=BURN_UI["green"] if self.hostfs_stage_ready() else BURN_UI["red"],
        )
        self.lbl_hostfs_status.pack(fill=tk.X, pady=(0, 9))

        row1 = tk.Frame(body, bg=BURN_UI["panel"])
        row1.pack(fill=tk.X)

        self.stage_combo = ttk.Combobox(row1, values=STAGE_NAMES, state="readonly", width=24, style="Burn.TCombobox")
        self.stage_combo.current(0)
        self.stage_combo.pack(side=tk.LEFT, padx=(0, 8), ipady=3)
        self.stage_combo.bind("<<ComboboxSelected>>", self.on_stage_changed)

        self.burn_check(row1, "Guards", self.show_guards_var, self.refresh_markers).pack(side=tk.LEFT, padx=(0, 8))
        self.show_morale_var = tk.BooleanVar(value=False)
        self.burn_check(row1, "Morale", self.show_morale_var, self.refresh_markers).pack(side=tk.LEFT, padx=(0, 8))
        self.burn_button(row1, "- Zoom", self.zoom_out, BURN_UI["panel_3"], side=tk.LEFT, padx=(8, 4))
        self.lbl_zoom = self.burn_label(row1, "100%", fg=BURN_UI["text"], font=("Segoe UI", 9, "bold"))
        self.lbl_zoom.pack(side=tk.LEFT, padx=6)
        self.burn_button(row1, "+ Zoom", self.zoom_in, BURN_UI["teal"], fg=BURN_UI["dark_text"], side=tk.LEFT, padx=4)

        row2 = tk.Frame(body, bg=BURN_UI["panel"])
        row2.pack(fill=tk.X, pady=(14, 0))
        actions = [
            ("Balance", self.run_auto_balance, BURN_UI["teal"], BURN_UI["dark_text"]),
            ("Predict", self.calculate_likely_outcome, BURN_UI["lilac"], BURN_UI["dark_text"]),
            ("Rnd Stats", self.open_stat_randomizer, "#d56f8d", BURN_UI["dark_text"]),
            ("Gen Stage", self.generate_procedural_stage, "#c9863d", BURN_UI["dark_text"]),
        ]
        for label, cmd, bg, fg in actions:
            self.burn_button(row2, label, cmd, bg, fg, side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        row3 = tk.Frame(body, bg=BURN_UI["panel"])
        row3.pack(fill=tk.X, pady=(8, 0))
        mod_entry = self.burn_entry(row3, self.modname, width=16)
        mod_entry.pack(side=tk.LEFT, padx=(0, 6))
        self.burn_button(row3, "Create Stage Mod", self.create_stage_mod, BURN_UI["green"], BURN_UI["dark_text"], side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.burn_button(row3, "PNACH", self.generate_pnach, BURN_UI["purple"], BURN_UI["text"], side=tk.LEFT, fill=tk.X, expand=True, padx=4)

    def build_heads_up_panel(self):
        panel, body = self.make_panel("Stage Info", 1168, 18, 390, 300, BURN_UI["lilac"])

        card_row = tk.Frame(body, bg=BURN_UI["panel"])
        card_row.pack(fill=tk.X)
        self.lbl_stage_card = self.mini_card(card_row, "Stage", STAGE_NAMES[0], BURN_UI["red"])
        self.lbl_roster_card = self.mini_card(card_row, "Roster", "No squads loaded", BURN_UI["lilac"])

        card_row_2 = tk.Frame(body, bg=BURN_UI["panel"])
        card_row_2.pack(fill=tk.X, pady=(8, 0))
        self.lbl_selection_card = self.mini_card(card_row_2, "Selection", "None", BURN_UI["lilac"])
        self.lbl_view_card = self.mini_card(card_row_2, "View", "100% zoom", BURN_UI["red"])

        self.burn_label(body, "Morale Balance", fg=BURN_UI["text"], font=("Segoe UI", 10, "bold")).pack(fill=tk.X, pady=(12, 3))
        self.morale_canvas = tk.Canvas(body, width=340, height=28, bg=BURN_UI["entry"], highlightthickness=0)
        self.morale_canvas.pack(fill=tk.X)
        self.morale_canvas.bind("<Configure>", lambda event: self.update_global_morale())

        self.lbl_selected = tk.Label(
            body,
            text="No Selection",
            bg=BURN_UI["panel"],
            fg=BURN_UI["muted"],
            font=("Segoe UI", 10, "bold"),
            wraplength=340,
        )
        self.lbl_selected.pack(fill=tk.X, pady=(9, 0))

    def mini_card(self, parent, label, value, accent):
        card = tk.Frame(parent, bg=BURN_UI["panel_2"], highlightbackground=BURN_UI["line"], highlightthickness=1)
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Frame(card, bg=accent, width=5).pack(side=tk.LEFT, fill=tk.Y)
        inner = tk.Frame(card, bg=BURN_UI["panel_2"], padx=10, pady=8)
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.burn_label(inner, label, bg=BURN_UI["panel_2"], fg=BURN_UI["muted"], font=("Segoe UI", 8)).pack(fill=tk.X)
        value_label = self.burn_label(inner, value, bg=BURN_UI["panel_2"], fg=BURN_UI["text"], font=("Segoe UI", 8, "bold"), wraplength=130)
        value_label.pack(fill=tk.X)
        return value_label

    def build_roster_panel(self):
        panel, body = self.make_panel("Roster Browser", 26, 390, 430, 390, BURN_UI["lilac"])

        self.burn_label(
            body,
            "Choose a squad here and the editor updates without switching context.",
            fg=BURN_UI["muted"],
            wraplength=390,
        ).pack(fill=tk.X, pady=(0, 8))

        add_frame = tk.Frame(body, bg=BURN_UI["panel_2"], highlightbackground=BURN_UI["line"], highlightthickness=1, padx=10, pady=9)
        add_frame.pack(fill=tk.X)
        self.burn_label(add_frame, "Add New Unit", bg=BURN_UI["panel_2"], fg=BURN_UI["text"], font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        cap_row = tk.Frame(add_frame, bg=BURN_UI["panel_2"])
        cap_row.pack(fill=tk.X, pady=(6, 8))
        self.lbl_cap_s1 = self.burn_label(cap_row, "Side 1 (Blue): 0/256", bg=BURN_UI["panel_2"], fg=BURN_UI["blue"])
        self.lbl_cap_s1.pack(side=tk.LEFT)
        self.lbl_cap_s2 = self.burn_label(cap_row, "Side 2 (Red): 0/256", bg=BURN_UI["panel_2"], fg=BURN_UI["red"])
        self.lbl_cap_s2.pack(side=tk.LEFT, padx=(20, 0))
        btn_add_frame = tk.Frame(add_frame, bg=BURN_UI["panel_2"])
        btn_add_frame.pack(fill=tk.X)
        self.burn_button(btn_add_frame, "Add to Side 1", lambda: self.add_unit(1), BURN_UI["blue"], BURN_UI["header_text"], side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.burn_button(btn_add_frame, "Add to Side 2", lambda: self.add_unit(2), BURN_UI["red"], BURN_UI["header_text"], side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        search_frame = tk.Frame(body, bg=BURN_UI["panel_2"], highlightbackground=BURN_UI["line"], highlightthickness=1, padx=10, pady=9)
        search_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.burn_label(search_frame, "Roster Search", bg=BURN_UI["panel_2"], fg=BURN_UI["text"], font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        filter_frame = tk.Frame(search_frame, bg=BURN_UI["panel_2"])
        filter_frame.pack(fill=tk.X, pady=(8, 8))
        self.burn_label(filter_frame, "Search:", bg=BURN_UI["panel_2"]).pack(side=tk.LEFT, padx=(0, 6))
        self.var_search = tk.StringVar()
        self.var_search.trace("w", self.filter_list)
        self.burn_entry(filter_frame, self.var_search, width=28).pack(side=tk.LEFT, fill=tk.X, expand=True)

        list_wrap = tk.Frame(search_frame, bg=BURN_UI["void"])
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(
            list_wrap,
            exportselection=False,
            selectmode=tk.EXTENDED,
            bg=BURN_UI["void"],
            fg=BURN_UI["header_text"],
            selectbackground=BURN_UI["orange"],
            selectforeground=BURN_UI["dark_text"],
            bd=0,
            highlightthickness=0,
            font=("Consolas", 9),
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(list_wrap, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        lookup_frame = tk.Frame(body, bg=BURN_UI["panel"])
        lookup_frame.pack(fill=tk.X, pady=(8, 0))
        self.burn_label(lookup_frame, "ID Lookup Reference:", fg=BURN_UI["text"], font=("Segoe UI", 9, "bold")).pack(fill=tk.X)
        sorted_all_units = sorted(UNIT_NAMES.items(), key=lambda x: x[0])
        self.all_unit_values = [f"{name} ({uid})" for uid, name in sorted_all_units]
        cb_unit_ref = ttk.Combobox(lookup_frame, values=self.all_unit_values, state="normal", style="Burn.TCombobox")
        cb_unit_ref.set("Type name to find ID")
        cb_unit_ref.pack(fill=tk.X, pady=(3, 0), ipady=3)
        cb_unit_ref.bind("<KeyRelease>", self.on_combo_keyrelease)

    def build_squad_editor_panel(self):
        panel, body = self.make_panel("Squad Editor", 1136, 330, 530, 512, BURN_UI["red"])

        self.burn_label(
            body,
            "Click a squad and this panel becomes your active editor.",
            fg=BURN_UI["muted"],
            wraplength=386,
        ).pack(fill=tk.X, pady=(0, 8))

        TOOLTIPS = {
            "x": "Horizontal coordinate on the map (0-800)",
            "y": "Vertical coordinate on the map (0-800)",
            "dir": "Facing direction (0-7). 0 is North/Up.",
            "path": "Pathing, relates to what the squad prioritizes.",
            "gate_mode": "Behavior state of the Gate",
            "life": "Life of the squad leader, guards get 33.3% less of it.",
            "leader": "The ID of this squad's Officer/Commander.",
            "guard_id": "The ID of the squad leader's guards.",
            "atk": "Attack of the squad leader, guards get 33.3% less of it.",
            "def": "Defense of the squad leader, guards get 33.3% less of it.",
            "guard_cnt": "Number of bodyguards, including the leader. Max value is 9.",
            "own_slot": "Determines which force owns this squad.",
            "type": "Unit class: player, commander, general, officer, gate captain, or troop.",
            "ai_type": "Ranged or mounted behavior hints.",
            "orders": "Attack, follow, hold, and other order behaviors.",
            "hidden": "Hides this squad until an event reveals it.",
            "target": "Enemy or ally slot targeted by this squad.",
            "drop": "Item ID dropped upon defeat.",
            "ai_lvl": "Aggression and intelligence.",
            "delay": "Delay before advancing.",
            "points": "Points awarded to player for KO of this squad.",
        }

        grid_frame = tk.Frame(body, bg=BURN_UI["panel"])
        grid_frame.pack(fill=tk.X)
        for col_idx in range(4):
            grid_frame.grid_columnconfigure(col_idx, weight=1)

        row = 0
        col = 0
        for label_text, key, _, _ in UNIT_DATA_FIELDS:
            label = self.burn_label(grid_frame, label_text + ":", fg=BURN_UI["muted"], font=("Segoe UI", 8))
            label.grid(row=row, column=col * 2, sticky="e", padx=(0, 6), pady=4)
            if key in TOOLTIPS:
                ToolTip(label, TOOLTIPS[key])

            var = tk.StringVar()
            self.entry_vars[key] = var
            entry = self.burn_entry(grid_frame, var, width=13)
            entry.grid(row=row, column=col * 2 + 1, sticky="ew", padx=(0, 8), pady=4)

            col += 1
            if col > 1:
                col = 0
                row += 1

        lbl_morale = self.burn_label(grid_frame, "Morale:", fg=BURN_UI["muted"], font=("Segoe UI", 8))
        lbl_morale.grid(row=row, column=0, sticky="e", padx=(0, 6), pady=4)
        ToolTip(lbl_morale, "Force Morale (0-899). Leaders only.")
        self.var_morale = tk.StringVar()
        self.entry_morale = self.burn_entry(grid_frame, self.var_morale, width=13)
        self.entry_morale.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        action_frame = tk.Frame(body, bg=BURN_UI["panel"])
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        self.burn_button(action_frame, "Update Data", self.update_selected_unit_data, BURN_UI["green"], BURN_UI["dark_text"], side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.burn_button(action_frame, "Delete Unit", self.delete_selected_unit, BURN_UI["red"], BURN_UI["header_text"], side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    def build_legend_panel(self):
        panel, body = self.make_panel("Map Control", 472, 812, 830, 100, BURN_UI["red"])
        body.configure(padx=8, pady=8)

        def chip(label, color):
            wrap = tk.Frame(body, bg=BURN_UI["panel_2"], highlightbackground=BURN_UI["line"], highlightthickness=1, padx=10, pady=6)
            wrap.pack(side=tk.LEFT, padx=4)
            tk.Canvas(wrap, width=10, height=10, bg=BURN_UI["panel_2"], highlightthickness=0).pack(side=tk.LEFT)
            dot = wrap.winfo_children()[0]
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            self.burn_label(wrap, label, bg=BURN_UI["panel_2"], fg=BURN_UI["text"], font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(6, 0))

        chip("Blue Force", BURN_UI["blue"])
        chip("Red Force", BURN_UI["red"])
        chip("Selected", BURN_UI["teal"])
        chip("Guards On", BURN_UI["teal"])
        self.burn_label(
            body,
            "Left drag moves squads | Ctrl+Click multi-select | Right drag pans the map",
            fg=BURN_UI["muted"],
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT, padx=(14, 0))

    def hostfs_stage_files(self, stage_idx=None):
        stage_idx = self.current_stage_index if stage_idx is None else stage_idx
        stage_dir = STAGE_DIRS[stage_idx]
        return find_stage_side_file(stage_dir, ".ub0"), find_stage_side_file(stage_dir, ".ub1")

    def hostfs_stage_ready(self, stage_idx=None):
        ub0_path, ub1_path = self.hostfs_stage_files(stage_idx)
        return bool(ub0_path and ub1_path)

    def hostfs_status_text(self):
        ub0_path, ub1_path = self.hostfs_stage_files()
        if ub0_path and ub1_path:
            return f"Hostfs Stage Source Ready: {os.path.basename(ub0_path)} + {os.path.basename(ub1_path)}"
        return f"Hostfs Stage Source Missing in {STAGE_DIRS[self.current_stage_index]}"

    def refresh_hud_labels(self):
        if hasattr(self, "lbl_hostfs_status"):
            self.lbl_hostfs_status.config(
                text=self.hostfs_status_text(),
                fg=BURN_UI["green"] if self.hostfs_stage_ready() else BURN_UI["red"],
            )
        if hasattr(self, "lbl_stage_card"):
            self.lbl_stage_card.config(text=STAGE_NAMES[self.current_stage_index])
        if hasattr(self, "lbl_view_card"):
            guards = "On" if self.show_guards_var.get() else "Off"
            morale_var = getattr(self, "show_morale_var", None)
            morale = "On" if morale_var is not None and morale_var.get() else "Off"
            self.lbl_view_card.config(text=f"{int(self.scale * 100)}% zoom\nGuards {guards} | Morale {morale}")

    def on_combo_keyrelease(self, event):
        combo = event.widget
        if event.keysym in ['Up', 'Down', 'Return', 'Enter']:
            return

        value = event.widget.get()
        if value == '':
            combo['values'] = self.all_unit_values
        else:
            data = []
            for item in self.all_unit_values:
                if value.lower() in item.lower():
                    data.append(item)
            combo['values'] = data
    
    def calculate_tcp(self, slots):
        """Calculates Total Combat Power for a list of units"""
        total = 0
        for s in slots:
            if s["leader"] == 255 or (s["x"]==0 and s["y"]==0): continue
            
            life = max(1, s["life"])
            atk = max(1, s["atk"])
            defence = max(1, s["def"])
            ai = max(1, s["ai_lvl"])
            
            total += life * atk * defence * ai
        return total

    def calculate_likely_outcome(self):
        """Estimates the battle outcome by comparing TCP"""
        if not self.slots: return

        c1_name = "Unknown Commander"
        c2_name = "Unknown Commander"
        
        for i in range(256):
            if self.slots[i]["leader"] != 255 and self.slots[i]["type"] == 1:
                c1_name = get_unit_name(self.slots[i]["leader"])
                break
        
        for i in range(256, 512):
            if self.slots[i]["leader"] != 255 and self.slots[i]["type"] == 1:
                c2_name = get_unit_name(self.slots[i]["leader"])
                break
                
        s1 = self.slots[0:256]
        s2 = self.slots[256:512]
        tcp1 = self.calculate_tcp(s1)
        tcp2 = self.calculate_tcp(s2)
        
        if tcp1 == 0 or tcp2 == 0:
            messagebox.showinfo("Outcome", "One side has 0 combat power. Winner is obvious.")
            return

        if tcp1 > tcp2:
            winner = "Side 1 (Blue)"
            w_cmd = c1_name
            l_cmd = c2_name
            ratio = tcp1 / tcp2
        else:
            winner = "Side 2 (Red)"
            w_cmd = c2_name
            l_cmd = c1_name
            ratio = tcp2 / tcp1
        
        if ratio < 1.1:
            outcome = "Stalemate/Phyrric Victory"
            desc = f"The battle will likely be a long, bloody stalemate.\n{l_cmd} may fall but {w_cmd} will suffer heavy losses."
        elif ratio < 1.5:
            outcome = "Decisive Victory"
            desc = f"{w_cmd} has a clear advantage.\n{l_cmd} will likely be defeated after a moderate struggle."
        elif ratio < 2.0:
            outcome = "Crushing Defeat"
            desc = f"{w_cmd} dominates the battlefield.\n{l_cmd} will be routed quickly."
        else:
            outcome = "Instant Wipe"
            desc = f"Total defeat.\n{l_cmd}'s forces will evaporate almost instantly against {w_cmd}."

        adv_pct = int((ratio - 1) * 100)
            
        msg = (f"Battle Prediction \n\n"
               f"Side 1 (Blue): {c1_name}\n"
               f"Side 2 (Red):  {c2_name}\n\n"
               f"TCP Ratio: {tcp1:,} vs {tcp2:,}\n"
               f"Advantage: {winner} (+{adv_pct}%)\n\n"
               f"Likely Outcome: {outcome}\n"
               f"{desc}")
        
        messagebox.showinfo("Likely Outcome", msg)

    def get_deployment_zone(self, side_slots):
        """Finds the centroid of existing units to spawn near friends"""
        xs = [s["x"] for s in side_slots if s["leader"]!=255]
        ys = [s["y"] for s in side_slots if s["leader"]!=255]
        if not xs: return 400, 400
        return sum(xs)//len(xs), sum(ys)//len(ys)

    def get_pixel_variant(self, x, y):
        """Returns (R, G, B, A, Hue) or None if out of bounds"""
        if not self.current_pil_image: return None
        
        w, h = self.current_pil_image.size
        
        ix = int(x)
        iy = int(h - y) 
        
        if ix < 0 or ix >= w or iy < 0 or iy >= h: return None
        
        try:
            r, g, b, a = self.current_pil_image.getpixel((ix, iy))
            h_val, s_val, v_val = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            return (r, g, b, a, h_val, s_val, v_val)
        except:
            return None

    def is_valid_terrain(self, x, y):
        """
        GA Constraint: Check if pixel is valid
        Strict Mode: Rejects semi-transparency and wider blue ranges
        """
        offsets = [(0,0), (0,10), (0,-10), (10,0), (-10,0)]
        
        for ox, oy in offsets:
            data = self.get_pixel_variant(x + ox, y + oy)
            if not data: return False
            
            r, g, b, a, hue, sat, val = data
            
            if a < 250: 
                return False 

            if r < 40 and g < 40 and b < 40: 
                return False

            blue_dominant = (b > r + 15) and (b > g + 15)
            blue_hue = (0.45 < hue < 0.75)
            has_color = (sat > 0.15)

            if (blue_dominant or blue_hue) and has_color:
                return False 
                
        return True

    def is_crowded(self, x, y, all_units):
        """GA Constraint: Check 5 pixel collision rule"""
        for s in all_units:
            if s["leader"] == 255: continue
            if abs(s["x"] - x) < 5 and abs(s["y"] - y) < 5:
                return True
        return False

    def run_auto_balance(self):
        if not self.slots: return
        
        s1 = self.slots[0:256]
        s2 = self.slots[256:512]
        
        tcp1 = self.calculate_tcp(s1)
        tcp2 = self.calculate_tcp(s2)
        
        if tcp1 == tcp2:
            messagebox.showinfo("Balance", "Combat Power is exactly equal!")
            return
            
        weak_side_idx = 1 if tcp1 > tcp2 else 0
        target_gap = abs(tcp1 - tcp2)
        
        weak_slots = s2 if weak_side_idx == 1 else s1
        weak_start_idx = 256 if weak_side_idx == 1 else 0
        
        empty_indices = [i for i, s in enumerate(weak_slots) if s["leader"] == 255]
        if not empty_indices:
            messagebox.showwarning("Full", "Weaker side has no empty slots!")
            return

        center_x, center_y = self.get_deployment_zone(weak_slots)
        
        POPULATION_SIZE = 20
        GENERATIONS = 15
        
        def create_random_unit():
            for _ in range(40): 
                nx = center_x + random.randint(-150, 150)
                ny = center_y + random.randint(-150, 150)
                nx = max(10, min(790, nx))
                ny = max(10, min(790, ny))
                
                if self.is_valid_terrain(nx, ny) and not self.is_crowded(nx, ny, weak_slots):
                    return {
                        "leader": 128, 
                        "x": nx, "y": ny,
                        "life": random.randint(100, 300),
                        "atk": random.randint(5, 20),
                        "def": random.randint(5, 20),
                        "ai_lvl": random.randint(1, 8),
                        "dir": 0, "path": 0, "gate_mode": 0, "guard_id": 0,
                        "guard_cnt": 0, "own_slot": 0, "ai_type": 0, "orders": 0,
                        "hidden": 0, "target": 255, "drop": 0, "delay": 0, "points": 0
                    }
            
            valid_friends = [s for s in weak_slots if s["leader"] != 255]
            
            if valid_friends:
                for attempt in range(30):
                    buddy = random.choice(valid_friends)
                    
                    if attempt < 10:
                        offsets = [-12, -8, -6, 6, 8, 12] # Safe Spacing
                    else:
                        offsets = [-2, -1, 1, 2] # Tight Squeeze
                        
                    fx = buddy["x"] + random.choice(offsets)
                    fy = buddy["y"] + random.choice(offsets)
                    fx = max(10, min(790, fx))
                    fy = max(10, min(790, fy))
                    
                    if self.is_valid_terrain(fx, fy):
                        return {
                            "leader": 128, "x": fx, "y": fy,
                            "life": 100, "atk": 5, "def": 5, "ai_lvl": 1,
                            "dir": 0, "path": 0, "gate_mode": 0, "guard_id": 0,
                            "guard_cnt": 0, "own_slot": 0, "ai_type": 0, "orders": 0,
                            "hidden": 0, "target": 255, "drop": 0, "delay": 0, "points": 0
                        }

                buddy = random.choice(valid_friends)
                fx = buddy["x"] + random.choice([-2, -1, 1, 2])
                fy = buddy["y"] + random.choice([-2, -1, 1, 2])
                fx = max(10, min(790, fx))
                fy = max(10, min(790, fy))
                
                return {
                    "leader": 128, "x": fx, "y": fy,
                    "life": 100, "atk": 5, "def": 5, "ai_lvl": 1,
                    "dir": 0, "path": 0, "gate_mode": 0, "guard_id": 0,
                    "guard_cnt": 0, "own_slot": 0, "ai_type": 0, "orders": 0,
                    "hidden": 0, "target": 255, "drop": 0, "delay": 0, "points": 0
                }

            rx = center_x + random.randint(-50, 50)
            ry = center_y + random.randint(-50, 50)
            return {
                "leader": 128, "x": rx, "y": ry,
                "life": 100, "atk": 5, "def": 5, "ai_lvl": 1,
                "dir": 0, "path": 0, "gate_mode": 0, "guard_id": 0,
                "guard_cnt": 0, "own_slot": 0, "ai_type": 0, "orders": 0,
                "hidden": 0, "target": 255, "drop": 0, "delay": 0, "points": 0
            }

        population = []
        for _ in range(POPULATION_SIZE):
            count = random.randint(1, min(10, len(empty_indices)))
            ind = [create_random_unit() for _ in range(count)]
            population.append(ind)

        best_solution = None
        best_diff = float('inf')

        for gen in range(GENERATIONS):
            scored_pop = []
            for ind in population:
                added_tcp = self.calculate_tcp(ind)
                diff = abs(target_gap - added_tcp)
                scored_pop.append((diff, ind))
                if diff < best_diff:
                    best_diff = diff
                    best_solution = ind
            
            scored_pop.sort(key=lambda x: x[0])
            survivors = [x[1] for x in scored_pop[:POPULATION_SIZE//2]]
            
            new_pop = survivors[:]
            while len(new_pop) < POPULATION_SIZE:
                parent = random.choice(survivors)
                child = copy.deepcopy(parent)
                
                if random.random() < 0.3:
                    if random.random() < 0.5 and len(child) < len(empty_indices):
                        child.append(create_random_unit())
                    elif len(child) > 1:
                        child.pop()
                if random.random() < 0.3:
                    u = random.choice(child)
                    u["life"] = max(1, u["life"] + random.randint(-50, 50))
                
                new_pop.append(child)
            population = new_pop

        self.selected_indices.clear()
        
        final_units = []
        for u in best_solution:
            if not self.is_crowded(u["x"], u["y"], final_units):
                final_units.append(u)

        count_added = 0
        for unit_data in final_units:
            if not empty_indices: break
            slot_idx = empty_indices.pop(0) + weak_start_idx
            unit_data["own_slot"] = slot_idx
            self.slots[slot_idx].update(unit_data)
            self.selected_indices.add(slot_idx) 
            count_added += 1

        self.update_editor_panel()
        self.refresh_markers()
        self.refresh_listbox()
        self.update_caps()
        self.update_global_morale()
        
        side_name = "Side 1 (Blue)" if weak_side_idx == 0 else "Side 2 (Red)"
        msg = (f"Analysis Complete.\n"
               f"{side_name} was weaker by {target_gap:,} TCP.\n"
               f"GA generated {count_added} reinforcements to balance power.\n"
               f"Units placed near deployment zone ({center_x}, {center_y}).")
        messagebox.showinfo("Auto-Balance Complete", msg)

    def generate_procedural_stage(self):
        stage_name = STAGE_NAMES[self.current_stage_index]
        if stage_name not in STAGES_ZONES:
            messagebox.showerror("Error", f"No Zone Data defined for {stage_name} yet.\nPlease contact the developer.")
            return
        
        if not messagebox.askyesno("Confirm", "This will wipe all current units and generate a new battle.\nContinue?"):
            return

        for i in range(512):
            self.slots[i].update({
                "leader": 255, "x": 0, "y": 0, "guard_cnt": 0,
                "life": 0, "atk": 0, "def": 0, "ai_lvl": 0
            })

        zones = STAGES_ZONES[stage_name]
        s1_zone = random.choice(zones["Side 1"])
        self.spawn_unit_in_zone(0, s1_zone, is_commander=True, side=1)
        
        s2_zone = random.choice(zones["Side 2"])
        self.spawn_unit_in_zone(256, s2_zone, is_commander=True, side=2)
        for i in range(1, 101):
            z = random.choice(zones["Side 1"])
            self.spawn_unit_in_zone(i, z, is_commander=False, side=1)
        for i in range(257, 357):
            z = random.choice(zones["Side 2"])
            self.spawn_unit_in_zone(i, z, is_commander=False, side=2)

        self.selected_indices.clear()
        self.update_editor_panel()
        self.refresh_markers()
        self.refresh_listbox()
        self.update_caps()
        self.update_global_morale()
        messagebox.showinfo("Success", f"Generated new scenario for {stage_name}.")

    def spawn_unit_in_zone(self, slot_idx, zone, is_commander, side):
        rect = zone["rect"] # (minx, miny, maxx, maxy)
        def get_rand_spot():
            rx = random.randint(rect[0], rect[2])
            ry = random.randint(rect[1], rect[3])
            return max(0, min(790, rx)), max(0, min(790, ry))
        all_units = [s for s in self.slots if s["leader"] != 255]
        for _ in range(1000):
            rx, ry = get_rand_spot()
            if self.is_valid_terrain(rx, ry) and not self.is_crowded(rx, ry, all_units):
                self.apply_spawn_data(slot_idx, rx, ry, is_commander, side)
                return
        for _ in range(1000):
            rx, ry = get_rand_spot()
            if self.is_valid_terrain(rx, ry):
                self.apply_spawn_data(slot_idx, rx, ry, is_commander, side)
                return
        rx, ry = get_rand_spot()
        self.apply_spawn_data(slot_idx, rx, ry, is_commander, side)

    def apply_spawn_data(self, slot_idx, x, y, is_commander, side):
        leader_id = random.choice([0, 1, 5, 10]) if is_commander else 128
        unit_type = 1 if is_commander else 6
        
        self.slots[slot_idx].update({
            "leader": leader_id,
            "x": x, "y": y,
            "type": unit_type,
            "life": 300 if is_commander else 150,
            "atk": 20 if is_commander else 10,
            "def": 20 if is_commander else 10,
            "guard_cnt": 5 if is_commander else 0,
            "ai_lvl": 8 if is_commander else 2,
            "dir": random.randint(0, 7),
            "own_slot": 0
        })
    
    def load_stage_data(self, stage_idx):
        """
        Read a stage's 512 unit slots from its hostfs loose files
        """
        self.current_stage_index = stage_idx
        self.slots = []
        self.load_image(MAP_FILES[stage_idx])
        self.refresh_hud_labels()

        stage_dir = STAGE_DIRS[stage_idx]
        ub0_path = find_stage_side_file(stage_dir, ".ub0")
        ub1_path = find_stage_side_file(stage_dir, ".ub1")

        if not ub0_path or not ub1_path:
            self.lbl_selected.config(
                text=f"Hostfs stage files (.ub0/.ub1) not found in {stage_dir}", fg=BURN_UI["red"]
            )
            self.refresh_hud_labels()
            self.refresh_markers(); self.refresh_listbox(); return

        try:
            for side_path in (ub0_path, ub1_path):
                with open(side_path, "rb") as f:
                    for _ in range(256):
                        chunk = f.read(32)
                        if len(chunk) != 32: break
                        slot_data = {"raw": bytearray(chunk), "morale": 0}
                        for _, key, offset, size in UNIT_DATA_FIELDS:
                            val = int.from_bytes(chunk[offset:offset+size], "little")
                            slot_data[key] = val
                        self.slots.append(slot_data)

            self.load_morale_data(stage_idx)

            self.selected_indices.clear()
            self.update_editor_panel()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read hostfs stage data:\n{e}")
            return

        self.refresh_markers()
        self.refresh_listbox()
        self.update_caps()
        self.update_global_morale()
        self.root.after_idle(self.update_global_morale)
        self.refresh_hud_labels()

    def load_morale_data(self, stage_idx):
        """Read force leader morale values for a stage from the hostfs ELF into self.slots"""
        stg_name = STAGE_NAMES[stage_idx]
        if stg_name not in STAGE_MORALE_DATA:
            return
        if not os.path.exists(HOSTFS_ELF):
            return

        try:
            with open(HOSTFS_ELF, "rb") as f:
                for side_id in [1, 2]:
                    m_off, m_count = STAGE_MORALE_DATA[stg_name][side_id]
                    f.seek(m_off)
                    morale_list = [int.from_bytes(f.read(2), "little") for _ in range(m_count)]

                    start_slot = 0 if side_id == 1 else 256
                    end_slot = 256 if side_id == 1 else 512

                    m_idx = 0
                    for i in range(start_slot, end_slot):
                        target_val = i if side_id == 1 else (i - 256)
                        if self.slots[i]["own_slot"] == target_val and self.slots[i]["leader"] != 255:
                            if m_idx < len(morale_list):
                                self.slots[i]["morale"] = morale_list[m_idx]
                                m_idx += 1
        except Exception as e:
            messagebox.showwarning("Morale", f"Failed to read morale data from hostfs ELF:\n{e}")

    def create_stage_mod(self):
        """Dump the current stage's slot + morale data to a .DW2StageMod file in DW2_Mods"""
        if not self.slots:
            return

        sep = "."
        base_name = self.modname.get().split(sep, 1)[0] or "DW2Stage"
        usermodname = base_name + DW2_STAGE_MOD_EXT

        try:
            os.makedirs(MODS_DIR, exist_ok=True)
            mod_path = os.path.join(MODS_DIR, usermodname)
            with open(mod_path, "wb") as f:
                for slot in self.slots:
                    b = bytearray(slot["raw"])
                    for _, key, offset, size in UNIT_DATA_FIELDS:
                        val = slot[key]
                        max_val = (2 ** (8 * size)) - 1
                        val = max(0, min(val, max_val))
                        b[offset:offset + size] = val.to_bytes(size, "little")
                    f.write(b)

                f.write(self.current_stage_index.to_bytes(1, "little"))

                stg_name = STAGE_NAMES[self.current_stage_index]
                if stg_name in STAGE_MORALE_DATA:
                    f.write(b"MORALE")
                    for side_id in [1, 2]:
                        morale_values = []
                        start_slot = 0 if side_id == 1 else 256
                        end_slot = 256 if side_id == 1 else 512
                        for i in range(start_slot, end_slot):
                            target_val = i if side_id == 1 else (i - 256)
                            if self.slots[i]["own_slot"] == target_val and self.slots[i]["leader"] != 255:
                                morale_values.append(self.slots[i].get("morale", 0))
                        f.write(len(morale_values).to_bytes(2, "little"))
                        for val in morale_values:
                            f.write(val.to_bytes(2, "little"))
                else:
                    f.write(b"NOMORALE")

            messagebox.showinfo("Success", f"Mod file '{usermodname}' created in DW2_Mods.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create mod file '{usermodname}':\n{e}")

    def generate_pnach(self):
        if not self.slots: return
        
        UNIT_RAM_BASE_S1 = 0x203E4980 
        UNIT_RAM_BASE_S2 = 0x203E6960
        MORALE_RAM_MAP = {
            "Yellow Turban Rebellion": 0x2036EB52,
            "Hu Lao Gate": 0x2036EC62,
            "Guan Du": 0x2036ED72,
            "Chang Ban": 0x2036EE82,
            "Chi Bi": 0x2036EF92,
            "He Fei": 0x2036F0A2,
            "Yi Ling": 0x2036F1B2,
            "Wu Zhang Plains": 0x2036F2C2
        }

        filename = filedialog.asksaveasfilename(
            defaultextension=".pnach",
            initialfile="5B665C0B.pnach",
            title="Save PNACH File",
            filetypes=[("PNACH Files", "*.pnach")]
        )
        if not filename: return

        try:
            with open(filename, "w") as f:
                f.write(f"// Generated by DW2 Visual Guider\n")
                f.write(f"// Stage: {STAGE_NAMES[self.current_stage_index]}\n\n")
                f.write(f"\n// Side 1\n")
                
                base_phys_s1 = UNIT_RAM_BASE_S1 & 0x0FFFFFFF
                count_s1 = 0
                for i in range(256):
                    slot = self.slots[i]
                    is_active = slot["leader"] != 255
                    is_not_zero = not (slot["leader"] == 0 and slot["x"] == 0 and slot["y"] == 0)
                    
                    if is_active and is_not_zero:
                        current_addr = base_phys_s1 + (i * 32)
                        self.write_slot_pnach(f, slot, current_addr)
                        count_s1 += 1

                f.write(f"\n// Side 2\n")

                base_phys_s2 = UNIT_RAM_BASE_S2 & 0x0FFFFFFF
                count_s2 = 0
                for i in range(256, 512):
                    slot = self.slots[i]
                    
                    is_active = slot["leader"] != 255
                    is_not_zero = not (slot["leader"] == 0 and slot["x"] == 0 and slot["y"] == 0)
                    
                    if is_active and is_not_zero:
                        current_addr = base_phys_s2 + ((i - 256) * 32)
                        self.write_slot_pnach(f, slot, current_addr)
                        count_s2 += 1
                
                stg_name = STAGE_NAMES[self.current_stage_index]
                if stg_name in MORALE_RAM_MAP:
                    f.write(f"\n// Morale Data\n")
                    
                    morale_base_virt = MORALE_RAM_MAP[stg_name]
                    morale_base_phys = morale_base_virt & 0x0FFFFFFF
                    
                    s1_values = []
                    for i in range(256):
                         if self.slots[i]["leader"] != 255 and self.slots[i]["own_slot"] == i:
                             s1_values.append(self.slots[i].get("morale", 0))
                    
                    for m_idx, val in enumerate(s1_values):
                        addr = morale_base_phys + (m_idx * 2)
                        f.write(f"patch=1,EE,{addr:08X},short,{val:04X}\n")                   
                    s2_base_phys = morale_base_phys + 0x18
                    
                    s2_values = []
                    for i in range(256, 512):
                        if self.slots[i]["leader"] != 255 and self.slots[i]["own_slot"] == (i - 256):
                            s2_values.append(self.slots[i].get("morale", 0))
                            
                    for m_idx, val in enumerate(s2_values):
                        addr = s2_base_phys + (m_idx * 2)
                        f.write(f"patch=1,EE,{addr:08X},short,{val:04X}\n")

            messagebox.showinfo("Success", f"PNACH generated successfully!\nActive Units: {count_s1} (S1) + {count_s2} (S2)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PNACH:\n{e}")

    def write_slot_pnach(self, f, slot, addr):
        """Helper to write 32 bytes of a slot to PNACH"""
        b = bytearray(32) 
        for _, key, offset, size in UNIT_DATA_FIELDS:
            val = slot[key]
            max_val = (2**(8*size)) - 1
            val = max(0, min(val, max_val))
            b[offset:offset+size] = val.to_bytes(size, "little")

        for x in range(0, 32, 4):
            chunk_val = int.from_bytes(b[x:x+4], "little")
            chunk_addr = addr + x
            f.write(f"patch=1,EE,{chunk_addr:08X},word,{chunk_val:08X}\n")

    def map_to_canvas(self, mx, my):
        cy = (self.original_height - my) * self.scale
        cx = mx * self.scale
        return cx, cy

    def canvas_to_map(self, cx, cy):
        my = self.original_height - (cy / self.scale)
        mx = cx / self.scale
        return int(mx), int(my)

    def map_view_padding(self):
        viewport_w = max(self.canvas.winfo_width(), self.root.winfo_width(), self.view_padding_base)
        viewport_h = max(self.canvas.winfo_height(), self.root.winfo_height(), self.view_padding_base)
        zoom_pad = int(self.view_padding_base * max(1.0, self.zoom_level * 0.75))
        return max(viewport_w, zoom_pad), max(viewport_h, zoom_pad)

    def load_image(self, filename):
        path = os.path.join(self.maps_dir, filename)
        if not os.path.exists(path):
            self.base_image = None
            self.canvas.delete("all")
            return
        try:
            pil_img = Image.open(path).convert("RGBA") # Force RGBA for consistent analysis
            
            # Store original image for Pixel Analysis (GA)
            self.current_pil_image = pil_img
            
            self.base_image = ImageTk.PhotoImage(pil_img)
            self.original_width = pil_img.width
            self.original_height = pil_img.height
            self.zoom_level = 1.0
            self.apply_zoom()
        except Exception as e:
            print(f"Failed to load image: {e}")

    def apply_zoom(self):
        if not self.base_image: return
        try:
            path = os.path.join(self.maps_dir, MAP_FILES[self.current_stage_index])
            pil_img = Image.open(path)
            
            new_w = int(self.original_width * self.zoom_level)
            new_h = int(self.original_height * self.zoom_level)
            
            resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.display_image = ImageTk.PhotoImage(resized)
            
            self.scale = self.zoom_level
            
            self.canvas.delete("all")
            pad_x, pad_y = self.map_view_padding()
            self.canvas.config(scrollregion=(-pad_x, -pad_y, new_w + pad_x, new_h + pad_y))
            self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image)
            self.lbl_zoom.config(text=f"{int(self.scale*100)}%")
            self.refresh_hud_labels()
            self.refresh_markers()
        except:
            pass

    def refresh_markers(self):
        self.refresh_hud_labels()
        self.canvas.delete("marker")
        self.canvas.delete("guard_vis")
        
        if not self.slots: return

        BASE_OFFSETS = [
            (-10, 0), (10, 0),      # Flank
            (-15, -10), (15, -10),  # Row 2
            (-20, -20), (20, -20),  # Row 3
            (-25, -30), (25, -30)   # Row 4
        ]

        for i, slot in enumerate(self.slots):
            if slot["leader"] == 255 or (slot["x"] == 0 and slot["y"] == 0):
                continue

            cx, cy = self.map_to_canvas(slot["x"], slot["y"])
            
            if i in self.selected_indices:
                color = BURN_UI["teal"]
                g_color = "#d6fff5"
            else:
                color = BURN_UI["blue"] if i < 256 else BURN_UI["red"]
                g_color = "#a9c4ff" if i < 256 else "#ff9aa0"

            if self.show_guards_var.get() and slot["guard_cnt"] > 1:
                actual_guards = max(0, slot["guard_cnt"] - 1)
                count = min(8, actual_guards) 

                direction = slot["dir"]
                rad = math.radians(direction * 45)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                for g_idx in range(count):
                    ox, oy = BASE_OFFSETS[g_idx]
                    
                    rx = ox * cos_a - oy * sin_a
                    ry = ox * sin_a + oy * cos_a
                    
                    gx, gy = cx + rx, cy + ry
                    self.canvas.create_oval(gx-2, gy-2, gx+2, gy+2, fill=g_color, outline="", tags="guard_vis")

            if self.show_morale_var.get():
                m_val = self.get_commander_morale(i)

                if m_val > 0:
                    bar_w = 24
                    fill_pct = min(1.0, m_val / 899.0)
                    fill_px = int(bar_w * fill_pct)
                    
                    bar_color = BURN_UI["blue"] if i < 256 else BURN_UI["red"]
                    
                    by = cy - 18
                    bx_start = cx - (bar_w / 2)
                    bx_end = bx_start + bar_w
                    self.canvas.create_line(bx_start, by, bx_end, by, 
                                            width=6, fill="#444", capstyle=tk.ROUND, tags="marker")
                    if fill_px > 0:
                        self.canvas.create_line(bx_start, by, bx_start + fill_px, by, 
                                                width=4, fill=bar_color, capstyle=tk.ROUND, tags="marker")

            tags = ("marker", f"slot_{i}")
            if i in self.selected_indices:
                glow_layers = (
                    (17, BURN_UI["lilac"], 3),
                    (12, BURN_UI["red"], 2),
                    (8, BURN_UI["header_text"], 1),
                )
                for radius, outline, width in glow_layers:
                    self.canvas.create_oval(
                        cx - radius,
                        cy - radius,
                        cx + radius,
                        cy + radius,
                        fill="",
                        outline=outline,
                        width=width,
                        tags=tags,
                    )
            self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=color, outline="white", width=2, tags=tags)
            label_fill = BURN_UI["lilac"] if i in self.selected_indices else "white"
            self.canvas.create_text(cx, cy-10, text=str(slot["leader"]), fill=label_fill, font=("Arial", 8, "bold"), tags=tags)

    def update_global_morale(self):
        """Calculates total morale for both sides and draws the balance bar"""
        if not self.slots: return

        total_s1 = 0
        total_s2 = 0
        
        for i in range(256):
            s = self.slots[i]
            if s["leader"] != 255 and s["own_slot"] == i:
                total_s1 += s.get("morale", 0)
                
        for i in range(256, 512):
            s = self.slots[i]
            if s["leader"] != 255:
                target_self = i - 256
                if s["own_slot"] == target_self:
                    total_s2 += s.get("morale", 0)

        self.morale_canvas.delete("all")
        configured_w = int(float(self.morale_canvas.cget("width")))
        configured_h = int(float(self.morale_canvas.cget("height")))
        w = max(self.morale_canvas.winfo_width(), configured_w, 1)
        h = max(self.morale_canvas.winfo_height(), configured_h, 1)
        
        total = total_s1 + total_s2
        if total == 0:
            self.morale_canvas.create_rectangle(0, 0, w, h, fill=BURN_UI["entry"], width=0)
            self.morale_canvas.create_text(w/2, h/2, text="No Morale Data", fill=BURN_UI["muted"], font=("Segoe UI", 8))
            return

        ratio = total_s1 / total
        mid_x = int(w * ratio)
        
        if mid_x > 0:
            self.morale_canvas.create_rectangle(0, 0, mid_x, h, fill=BURN_UI["blue"], width=0)
            if mid_x > 40:
                self.morale_canvas.create_text(10, h/2, text=f"{total_s1}", anchor="w", fill=BURN_UI["header_text"], font=("Segoe UI", 9, "bold"))

        if mid_x < w:
            self.morale_canvas.create_rectangle(mid_x, 0, w, h, fill=BURN_UI["red"], width=0)
            # Text S2
            if (w - mid_x) > 40:
                self.morale_canvas.create_text(w-10, h/2, text=f"{total_s2}", anchor="e", fill=BURN_UI["header_text"], font=("Segoe UI", 9, "bold"))
        
        self.morale_canvas.create_line(mid_x, 0, mid_x, h, fill=BURN_UI["header_text"], width=2)
        
    def update_caps(self):
        s1 = sum(1 for i in range(0, 256) if self.slots[i]["leader"] != 255 and not (self.slots[i]["x"] == 0 and self.slots[i]["y"] == 0))
        s2 = sum(1 for i in range(256, 512) if self.slots[i]["leader"] != 255 and not (self.slots[i]["x"] == 0 and self.slots[i]["y"] == 0))
        self.lbl_cap_s1.config(text=f"Side 1 (Blue): {s1}/256")
        self.lbl_cap_s2.config(text=f"Side 2 (Red): {s2}/256")
        if hasattr(self, "lbl_roster_card"):
            self.lbl_roster_card.config(text=f"{s1 + s2} active squads\nBlue {s1} | Red {s2}")
        self.refresh_hud_labels()
    
    def get_view_center_in_map_coords(self):
        if not self.base_image: return 400, 400
        x0 = self.canvas.canvasx(0)
        y0 = self.canvas.canvasy(0)
        vw = self.canvas.winfo_width()
        vh = self.canvas.winfo_height()
        cx = x0 + vw / 2
        cy = y0 + vh / 2
        return self.canvas_to_map(cx, cy)

    def center_on_map_coord(self, mx, my):
        if not self.base_image: return
        cx, cy = self.map_to_canvas(mx, my)
        try:
            sx1, sy1, sx2, sy2 = [float(v) for v in self.canvas.cget("scrollregion").split()]
        except ValueError:
            sx1, sy1 = 0, 0
            sx2 = self.original_width * self.scale
            sy2 = self.original_height * self.scale
        scroll_w = sx2 - sx1
        scroll_h = sy2 - sy1
        vw = self.canvas.winfo_width()
        vh = self.canvas.winfo_height()
        target_x = cx - vw / 2
        target_y = cy - vh / 2
        if scroll_w > 0:
            self.canvas.xview_moveto(max(0.0, min(1.0, (target_x - sx1) / scroll_w)))
        if scroll_h > 0:
            self.canvas.yview_moveto(max(0.0, min(1.0, (target_y - sy1) / scroll_h)))

    def zoom_in(self):
        if not self.base_image: return
        mx, my = self.get_view_center_in_map_coords()
        self.zoom_level += 0.5
        self.apply_zoom()
        self.center_on_map_coord(mx, my)

    def zoom_out(self):
        if not self.base_image or self.zoom_level <= 0.5: return
        mx, my = self.get_view_center_in_map_coords()
        self.zoom_level -= 0.5
        self.apply_zoom()
        self.center_on_map_coord(mx, my)

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)
    def do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_stage_changed(self, event):
        self.load_stage_data(self.stage_combo.current())

    def on_left_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        items = self.canvas.find_overlapping(cx-5, cy-5, cx+5, cy+5)
        
        clicked_unit_idx = None
        for item in items:
            for t in self.canvas.gettags(item):
                if t.startswith("slot_"):
                    clicked_unit_idx = int(t.split("_")[1])
                    break
            if clicked_unit_idx is not None: break

        ctrl_pressed = (event.state & 0x4) != 0 # Check ctrl key
        
        if clicked_unit_idx is not None:
            if ctrl_pressed:
                if clicked_unit_idx in self.selected_indices:
                    self.selected_indices.remove(clicked_unit_idx)
                else:
                    self.selected_indices.add(clicked_unit_idx)
            else:
                if clicked_unit_idx not in self.selected_indices:
                    self.selected_indices.clear()
                    self.selected_indices.add(clicked_unit_idx)
            
            self.update_editor_panel()
            self.refresh_markers()
            self.refresh_listbox_selection()
            self.dragging_unit_idx = clicked_unit_idx
        else:
            if not ctrl_pressed:
                self.selected_indices.clear()
            self.drag_start_x = cx
            self.drag_start_y = cy
            self.drag_rect_id = self.canvas.create_rectangle(cx, cy, cx, cy, outline="cyan", width=2)

    def on_left_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if self.dragging_unit_idx is not None:
            mx, my = self.canvas_to_map(cx, cy)
            mx, my = max(0, min(800, mx)), max(0, min(800, my))
            
            main_slot = self.slots[self.dragging_unit_idx]
            dx = mx - main_slot["x"]
            dy = my - main_slot["y"]
            
            for idx in self.selected_indices:
                s = self.slots[idx]
                s["x"] = max(0, min(800, s["x"] + dx))
                s["y"] = max(0, min(800, s["y"] + dy))
            
            self.update_editor_panel()
            self.refresh_markers()
        
        elif self.drag_rect_id:
            self.canvas.coords(self.drag_rect_id, self.drag_start_x, self.drag_start_y, cx, cy)

    def on_left_release(self, event):
        if self.drag_rect_id:
            x1, y1, x2, y2 = self.canvas.coords(self.drag_rect_id)
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None
            
            x_min, x_max = min(x1, x2), max(x1, x2)
            y_min, y_max = min(y1, y2), max(y1, y2)
            
            items = self.canvas.find_enclosed(x_min, y_min, x_max, y_max)
            for i, slot in enumerate(self.slots):
                if slot["leader"] == 255: continue
                cx, cy = self.map_to_canvas(slot["x"], slot["y"])
                if x_min <= cx <= x_max and y_min <= cy <= y_max:
                    self.selected_indices.add(i)
            
            self.update_editor_panel()
            self.refresh_markers()
            self.refresh_listbox_selection()

        self.dragging_unit_idx = None

    def get_commander_morale(self, unit_idx):
        """
        Recursively climbs the chain of command to find the Force Leader's morale
        Prevents infinite loops with a safety counter
        """
        current_idx = unit_idx
        
        for _ in range(5):
            if current_idx < 0 or current_idx >= len(self.slots):
                return 0
                
            slot = self.slots[current_idx]
            serves_rel = slot["own_slot"]
            
            base_offset = 0 if current_idx < 256 else 256
            target_abs = base_offset + serves_rel
            
            if target_abs == current_idx:
                return slot.get("morale", 0)
            
            current_idx = target_abs
            
        return 0
 
    def update_editor_panel(self):
        count = len(self.selected_indices)
        if count == 0:
            self.lbl_selected.config(text="No Selection", fg=BURN_UI["muted"])
            if hasattr(self, "lbl_selection_card"):
                self.lbl_selection_card.config(text="None")
            for var in self.entry_vars.values(): var.set("")
            return
        elif count == 1:
            idx = list(self.selected_indices)[0]
            name = get_unit_name(self.slots[idx]["leader"])
            
            is_s2 = idx >= 256
            display_idx = (idx - 256) if is_s2 else idx
            side_lbl = "Side 2" if is_s2 else "Side 1"
            
            selected_text = f"Slot {display_idx} ({side_lbl}) | {name}"
            self.lbl_selected.config(text=selected_text, fg=BURN_UI["text"])
            if hasattr(self, "lbl_selection_card"):
                self.lbl_selection_card.config(text=selected_text)
        else:
            selected_text = f"Squad Selection: {count} Units"
            self.lbl_selected.config(text=selected_text, fg=BURN_UI["purple"])
            if hasattr(self, "lbl_selection_card"):
                self.lbl_selection_card.config(text=selected_text)

        first_idx = list(self.selected_indices)[0]
        ref_slot = self.slots[first_idx]

        lookup_map = {
            "dir": UNIT_DIR,
            "type": UNIT_TYPES,
            "ai_type": AI_TYPES,
            "orders": ORDER_TYPES
        }

        for _, key, _, _ in UNIT_DATA_FIELDS:
            is_mixed = False
            ref_val = ref_slot[key]
            
            for idx in self.selected_indices:
                if self.slots[idx][key] != ref_val:
                    is_mixed = True
                    break
            
            if is_mixed:
                self.entry_vars[key].set("<Mixed>")
            else:
                final_str = str(ref_val)
                if key in lookup_map:
                    for name, val in lookup_map[key]:
                        if val == ref_val:
                            final_str = f"{name}: {val}"
                            break
                self.entry_vars[key].set(final_str)
                
        idx = list(self.selected_indices)[0]
        s = self.slots[idx]
        serves = s["own_slot"]
        
        target_self = idx if idx < 256 else (idx - 256)
        
        if serves == target_self:
            current_morale = s.get("morale", 0)
            self.entry_morale.config(state="normal")
            self.var_morale.set(str(current_morale))
        else:
            eff_morale = self.get_commander_morale(idx)
            self.var_morale.set(f"{eff_morale} (Linked)")
            self.entry_morale.config(state="disabled")

    def update_selected_unit_data(self):
        if not self.selected_indices: return
        
        try:
            for _, key, _, size in UNIT_DATA_FIELDS:
                if key in self.entry_vars:
                    val_str = self.entry_vars[key].get()
                    
                    if val_str == "<Mixed>" or val_str == "":
                        continue
                    
                    if ":" in val_str:
                        clean_str = val_str.split(":")[-1].strip()
                        val = int(clean_str)
                    elif "(" in val_str and ")" in val_str:
                        clean_str = val_str.split("(")[-1].strip(")")
                        val = int(clean_str)
                    else:
                        val = int(val_str)

                    binary_limit = (2**(8*size)) - 1
                    custom_limit = UNIT_LIMITS.get(key, binary_limit)
                    limit = min(custom_limit, binary_limit)
                    val = max(0, min(val, limit))
                    
                    for idx in self.selected_indices:
                        self.slots[idx][key] = val

            if self.entry_morale["state"] == "normal":
                try:
                    val = int(self.var_morale.get())
                    val = max(0, min(899, val)) 
                    for idx in self.selected_indices:
                        self.slots[idx]["morale"] = val
                except: pass
                    
            self.refresh_markers()
            self.refresh_listbox() 
            self.update_editor_panel() 
            self.update_caps()
            self.update_global_morale()
            messagebox.showinfo("Updated", f"Updated {len(self.selected_indices)} units.")
            
        except ValueError:
            messagebox.showerror("Error", "Could not read value.\nEnsure format is 'Name: Integer' or just 'Integer'.")
    def delete_selected_unit(self):
        if not self.selected_indices: return
        if messagebox.askyesno("Delete", f"Delete {len(self.selected_indices)} units?"):
            for idx in self.selected_indices:
                self.slots[idx]["leader"] = 255
            
            self.selected_indices.clear()
            self.update_editor_panel()
            self.refresh_markers()
            self.refresh_listbox()
            self.update_caps()
            self.update_global_morale()

    def add_unit(self, side):
        if not self.slots: return
        start, end = (0, 256) if side == 1 else (256, 512)
        
        for i in range(start, end):
            if self.slots[i]["leader"] == 255 or (self.slots[i]["x"] == 0 and self.slots[i]["y"] == 0):
                new_data = {
                    "leader": 0, "type": 0, "life": 200, "x": 400, "y": 400,
                    "dir": 0, "path": 0, "gate_mode": 0, "guard_id": 0, "atk": 10, "def": 10,
                    "guard_cnt": 0, "own_slot": i, "ai_type": 0, "orders": 0, "hidden": 0,
                    "target": 255, "drop": 0, "ai_lvl": 0, "delay": 0, "points": 0
                }
                self.slots[i].update(new_data)
                
                self.selected_indices.clear()
                self.selected_indices.add(i)
                self.update_editor_panel()
                self.refresh_markers()
                self.refresh_listbox()
                self.update_caps()
                self.center_on_map_coord(400, 400)
                self.update_global_morale()
                return
        messagebox.showwarning("Full", f"No empty slots available for Side {side}!")

    def filter_list(self, *args):
        self.refresh_listbox()
    
    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        self.list_map = [] 
        if not self.slots: return
        filter_txt = self.var_search.get().lower()
        
        indices_to_select = []
        
        row_idx = 0
        for i, slot in enumerate(self.slots):
            if slot["leader"] == 255 or (slot["x"] == 0 and slot["y"] == 0):
                continue
            
            is_s2 = i >= 256
            side_str = "S2" if is_s2 else "S1"
            display_idx = (i - 256) if is_s2 else i
            
            name = get_unit_name(slot["leader"])
            
            display_text = f"[{side_str} | {display_idx}] {name} ({slot['x']}, {slot['y']})"
            
            if filter_txt and filter_txt not in display_text.lower(): continue
            
            self.listbox.insert(tk.END, display_text)
            self.list_map.append(i)
            
            if i in self.selected_indices:
                indices_to_select.append(row_idx)
            row_idx += 1
            
        for r in indices_to_select:
            self.listbox.selection_set(r)

    def refresh_listbox_selection(self):
        self.listbox.selection_clear(0, tk.END)
        if not self.selected_indices: return
        
        first_view = None
        for i, slot_idx in enumerate(self.list_map):
            if slot_idx in self.selected_indices:
                self.listbox.selection_set(i)
                if first_view is None: first_view = i
        
        if first_view is not None:
            self.listbox.see(first_view)

    def on_listbox_select(self, event):
        sel_rows = self.listbox.curselection()
        if not sel_rows: return
        
        self.selected_indices.clear()
        for row in sel_rows:
            slot_idx = self.list_map[row]
            self.selected_indices.add(slot_idx)
            
        self.update_editor_panel()
        self.refresh_markers()
        
        if self.selected_indices:
            last = list(self.selected_indices)[-1]
            self.center_on_map_coord(self.slots[last]["x"], self.slots[last]["y"])

    def open_stat_randomizer(self):
        if not self.slots: return
        
        top = tk.Toplevel(self.root)
        top.title("Stat Randomizer")
        top.geometry("300x300")
        top.resizable(False, False)
        
        tk.Label(top, text="Set Random Ranges (Min - Max)", font=("Arial", 10, "bold")).pack(pady=10)
        
        input_frame = tk.Frame(top)
        input_frame.pack(pady=5)
        
        entries = {}
        def make_row(row, key, label, def_min, def_max):
            tk.Label(input_frame, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="e")
            e1 = tk.Entry(input_frame, width=6); e1.insert(0, str(def_min)); e1.grid(row=row, column=1)
            tk.Label(input_frame, text="-").grid(row=row, column=2)
            e2 = tk.Entry(input_frame, width=6); e2.insert(0, str(def_max)); e2.grid(row=row, column=3)
            entries[key] = (e1, e2)

        make_row(0, "life", "Life:", 20, 400)
        make_row(1, "atk", "Attack:", 1, 255)
        make_row(2, "def", "Defense:", 1, 255)
        make_row(3, "ai_lvl", "AI Level:", 1, 255)

        def apply_randomization():
            try:
                ranges = {}
                for key, (e_min, e_max) in entries.items():
                    ranges[key] = (int(e_min.get()), int(e_max.get()))
                
                if not messagebox.askyesno("Confirm", "This will randomize stats for all units on the map.\nContinue?"):
                    return
                
                count = 0
                for s in self.slots:
                    if s["leader"] == 255: continue
                    
                    for key, (r_min, r_max) in ranges.items():
                        val = random.randint(min(r_min, r_max), max(r_min, r_max))
                        
                        if key in ["atk", "def", "ai_lvl"]:
                            val = max(0, min(255, val))
                        elif key == "life":
                            val = max(0, min(400, val))
                            
                        s[key] = val
                    
                    count += 1
                
                self.refresh_markers()
                self.update_editor_panel()
                self.refresh_listbox()
                messagebox.showinfo("Success", f"Randomized stats for {count} squads!")
                top.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integers for all ranges.")

        tk.Button(top, text="Randomize Stats", command=apply_randomization, 
                  bg="#FF69B4", font=("Arial", 10, "bold"), width=15).pack(pady=20)
