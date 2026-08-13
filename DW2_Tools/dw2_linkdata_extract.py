"""
Extract DW2 assets from LINKDATA.BNS using sector tables in SLUS_200.79
"""

from __future__ import annotations

import argparse, re, struct
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Mapping

from elftools.elf.elffile import ELFFile

PAYLOAD_SECTOR_SHIFT = 11
PAYLOAD_SECTOR_SIZE = 1 << PAYLOAD_SECTOR_SHIFT
ENTRY_STRUCT = struct.Struct("<4I")
PAIR_STRUCT = struct.Struct("<2I")

SIZE_SECTORS = "sectors"
SIZE_BYTES_ALIGNED = "bytes-aligned"
EXPECTED_FILENAME_COUNT = 823
DEFAULT_UNPACK_SUMMARY_NAME = "unpack_summary.txt"
DEFAULT_TOC_REPORT_NAME = "toc_entries.txt"
SCRIPT_DIR = Path(__file__).resolve().parent
GAME_DIR = SCRIPT_DIR.parent
ELF_NAME = "SLUS_200.79"
LINKDATA_NAME = "LINKDATA.BNS"
UNPACK_DIR_NAME = "unpacked_linkdata"
DEFAULT_FILENAMES = SCRIPT_DIR / "dw2_filenames.txt"
MAKEFILE_LINKDATA_VARIABLES = (
    "DATA_OBJ",
    "STAGE_DT",
    "SND_DATA",
    "ALGO_DATA",
    "MAP_DATA",
    "ETC_DATA",
    "ITEM_DATA",
    "MARK_DATA",
    "CSEL_DATA",
    "EFFECT_DATA",
    "EVENT_DATA",
    "OPTION_DATA",
    "MCARD_DATA",
    "ENDING_DATA",
)
MAKEFILE_ASSIGNMENT_RE = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*(.*)$")
MAKEFILE_FILENAME_RE = re.compile(r"\$\([A-Za-z0-9_]+\)\\[^\s\\#]+\.[A-Za-z0-9_]+")

CHARACTER_MODEL_NAMES = (
    "CHOUUN",
    "KANU",
    "CHOUHI",
    "KAKOUTON",
    "TENI",
    "KYOCHO",
    "SHUUYU",
    "RIKUSON",
    "TAISHIJI",
    "CHOUSEN",
    "KOUMEI",
    "SOUSOU",
    "RYOFU",
    "SHOUKOU",
    "RYUUBI",
    "SONKEN1",
    "SONKEN2",
    "TOUTAKU",
    "ENSHOU",
    "BACHOU",
    "KOUCHUU",
    "KAKOUEN",
    "CHOURYOU",
    "SHIBAI",
    "RYOMOU",
    "KANNEI",
    "KYOUI",
    "CHOUKAKU",
    "SOLD1",
    "SOLD2",
    "SOLD3",
    "SOLD4",
    "ARCHER1",
    "ARCHER2",
    "YELLOW1",
    "YELLOW2",
    "BOSS1",
    "BOSS2",
    "BOSS3",
)

CHARACTER_TIM_NAMES = CHARACTER_MODEL_NAMES
HORSE_NAMES = ("HORSE0", "HORSE1")
POSE_MOTION_NAMES = CHARACTER_MODEL_NAMES[:28]
MOTION_NAMES = (
    "CHOUUN",
    "KANU",
    "CHOUHI",
    "KAKOUTO",
    "TENI",
    "KYOCHO",
    "SHUUYU",
    "RIKUSON",
    "TAISHIJ",
    "CHOUSEN",
    "KOUMEI",
    "SOUSOU",
    "RYOFU",
    "SHOUKOU",
    "ARCHER",
    "GUNNER",
    "SWORD1",
    "SWORD2",
    "SWORD3",
    "SWORD4",
    "SPEAR1",
    "SPEAR2",
    "HAL1",
    "HAL2",
    "HORSE",
)
WEAPON_NAMES = (
    "RINDOU",
    "SEIRYUU",
    "DABOU",
    "KIRINGA",
    "GOZU",
    "SHIYUU",
    "KOTEI",
    "R_HIEN",
    "OUROU",
    "R_SUI",
    "USEN",
    "ITEN",
    "GAGEKI",
    "KENKONKEN",
    "BOW",
    "BOWGUN",
    "SWORD1",
    "SWORD2",
    "SWORD3",
    "SWORD4",
    "SPEAR1",
    "SPEAR2",
    "HALBERD1",
    "HALBERD2",
    "ARROW",
)
STAGE_INDEX_NAMES = (
    "KOUKIN",
    "KOROUKAN",
    "KANTO",
    "CHOUHAN",
    "SEKIHEKI",
    "GAPPI",
    "IRYOU",
    "GOJOUGEN",
)
STAGE_FILE_SPECS = (
    ("ST_KKN", "koukin", "sky1"),
    ("ST_KRK", "koroukan", "sky2"),
    ("ST_KNT", "kanto", "sky3"),
    ("ST_CHN", "chouhan", "sky4"),
    ("ST_SKK", "sekiheki", "sky5"),
    ("ST_GPI", "gappi", "sky6"),
    ("ST_IRY", "iryou", "sky7"),
    ("ST_GJN", "gojougen", "sky8"),
)
MAP_NAMES = ("KOUKIN", "KOROUKAN", "KANTO", "CHOUHAN", "SEKIHEKI", "GAPPI", "IRYOU", "GOJOUGEN", "IRYOU2")
STILL_NAMES = tuple(f"STILL{index:02d}" for index in range(8))
FOG_NAMES = ("FOG01", "FOG02", "FOG03")
EVENT_MOTION_NAMES = tuple(f"ST{stage}{letter}" for letter in ("A", "B") for stage in range(1, 9))
ALGO_NAMES = tuple(
    f"{stage}.{suffix}"
    for stage in ("KOUKIN", "KOROUKAN", "KANTO", "CHOUHAN", "SEKIHEKI", "GAPPI", "IRYOU", "GOJOUGEN")
    for suffix in ("BB", "SB", "UB0", "UB1", "PB")
)
SOUND_ENV_STEMS = (
    "es_koukin",
    "es_koroukan",
    "es_kanto",
    "es_chouhan",
    "es_sekiheki",
    "es_gappi",
    "es_iryou",
    "es_gojougen",
)
SOUND_PLAYER_STEMS = tuple(name.lower() for name in POSE_MOTION_NAMES)
SOUND_FA_STEMS = (
    "fv_koukin",
    "fv_koroukan",
    "fv_kanto",
    "fv_chouhan",
    "fv_sekiheki",
    "fv_gappi",
    "fv_iryou",
    "fv_gojougen",
)
SOUND_PR_STEMS = (
    "pr_koukin",
    "pr_koroukan",
    "pr_kanto",
    "pr_chouhan",
    "pr_sekiheki_gi",
    "pr_sekiheki_go",
    "pr_gappi",
    "pr_iryou_go",
    "pr_iryou_shoku",
    "pr_gojougen_gi",
    "pr_gojougen_shoku",
)


@dataclass(frozen=True)
class LinkDataSymbolSpec:
    symbol: str
    names: tuple[str | None, ...] = ()
    extension: str = ".BIN"
    stride: int = ENTRY_STRUCT.size
    size_mode: str = SIZE_SECTORS
    include_zero_offset: bool = False
    index_base: int = 0
    address: int | None = None
    byte_size: int | None = None


@dataclass(frozen=True)
class LinkDataFixedSpec:
    symbol: str
    records: tuple[tuple[str | None, int, int], ...]
    extension: str = ".BIN"
    size_mode: str = SIZE_SECTORS
    index_base: int = 0


@dataclass(frozen=True)
class LinkDataSequenceSpec:
    symbol: str
    sources: tuple[LinkDataSymbolSpec, ...]
    names: tuple[str | None, ...] = ()
    extension: str = ".BIN"
    index_base: int = 0


@dataclass(frozen=True)
class LinkDataTable:
    key: str
    description: str
    symbols: tuple[LinkDataSymbolSpec, ...]
    fixed: tuple[LinkDataFixedSpec, ...] = ()
    sequences: tuple[LinkDataSequenceSpec, ...] = ()


@dataclass(frozen=True)
class LinkDataEntry:
    table: str
    symbol: str
    index: int
    name: str
    offset_units: int
    size_units: int
    offset: int
    size: int
    raw_size: int
    aux0: int = 0
    aux1: int = 0
    toc_file_offset: int | None = None
    toc_vaddr: int | None = None
    toc_bytes: bytes = b""

    @property
    def end_offset(self) -> int:
        return self.offset + self.size

def names(items: tuple[str, ...], extension: str) -> tuple[str, ...]:
    return tuple(item + extension for item in items)


def stage_names(extension: str) -> tuple[str, ...]:
    return tuple(stage + extension for stage in STAGE_INDEX_NAMES)


def stage_paths(extension: str) -> tuple[str, ...]:
    return tuple(f"$({variable})\\{base}{extension}" for variable, base, sky in STAGE_FILE_SPECS)


def stage_sky_paths() -> tuple[str, ...]:
    return tuple(f"$({variable})\\{sky}.tis" for variable, base, sky in STAGE_FILE_SPECS)


def stage_minimap_paths() -> tuple[str, ...]:
    return tuple(f"$({variable})\\{base}_minimap.obj" for variable, base, sky in STAGE_FILE_SPECS)


def stage_optional_paths(extension: str, included: tuple[bool, ...]) -> tuple[str | None, ...]:
    if len(included) != len(STAGE_FILE_SPECS):
        raise LinkDataError("Stage optional path mask does not match stage count")
    return tuple(
        f"$({variable})\\{base}{extension}" if include else None
        for include, (variable, base, sky) in zip(included, STAGE_FILE_SPECS)
    )


def sound_paths(stems: tuple[str, ...], extension: str) -> tuple[str, ...]:
    return tuple(f"$(SND)\\{stem}{extension}" for stem in stems)


def sound_menu_paths(extension: str) -> tuple[str | None, ...]:
    return (
        None,
        f"$(SND)\\stage_title{extension}",
        f"$(SND)\\gameover{extension}",
        f"$(SND)\\chrsele_1{extension}",
        f"$(SND)\\chrsele_2{extension}",
        f"$(SND)\\chrsele_3{extension}",
    )


def sound_briefing_paths(extension: str) -> tuple[str | None, ...]:
    return (
        None,
        *sound_paths(SOUND_PR_STEMS, extension),
        None,
        None,
        None,
        None,
        None,
        f"$(SND)\\pr_sekiheki_gi2{extension}",
        f"$(SND)\\pr_sekiheki_go2{extension}",
        f"$(SND)\\pr_gappi2{extension}",
        f"$(SND)\\pr_iryou_go2{extension}",
        f"$(SND)\\pr_iryou_shoku2{extension}",
        None,
        f"$(SND)\\pr_gojougen_shoku2{extension}",
    )


def filename_key(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).name.upper()


def filename_stem_key(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).stem.upper()


def filename_identity(name: str) -> str:
    return name.replace("\\", "/").upper()


def fallback_symbol_name(symbol: str) -> str:
    return symbol.lstrip("_") or "entry"

def read_text_with_fallback(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="cp932", errors="replace")


def parse_makefile_filenames(text: str) -> tuple[str, ...]:
    filenames_by_variable: dict[str, list[str]] = {variable: [] for variable in MAKEFILE_LINKDATA_VARIABLES}
    active_variable: str | None = None
    linkdata_variables = set(MAKEFILE_LINKDATA_VARIABLES)

    for line in text.splitlines():
        assignment_match = MAKEFILE_ASSIGNMENT_RE.match(line)
        if assignment_match:
            variable, remainder = assignment_match.groups()
            active_variable = variable if variable in linkdata_variables else None
        elif active_variable:
            remainder = line
        else:
            continue

        if active_variable:
            filenames_by_variable[active_variable].extend(MAKEFILE_FILENAME_RE.findall(remainder))
            stripped = remainder.strip()
            if stripped and not stripped.startswith("#") and not stripped.endswith("\\"):
                active_variable = None

    return tuple(
        filename
        for variable in MAKEFILE_LINKDATA_VARIABLES
        for filename in filenames_by_variable[variable]
    )


def read_linkdata_filenames(path: Path, *, expected_count: int | None = EXPECTED_FILENAME_COUNT) -> tuple[str, ...]:
    text = read_text_with_fallback(path)
    filenames = parse_makefile_filenames(text)
    if not filenames:
        filenames = tuple(
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if expected_count is not None and len(filenames) != expected_count:
        raise LinkDataError(f"{path} has {len(filenames)} filenames; expected {expected_count}.")
    seen_keys: set[str] = set()
    duplicate_keys: set[str] = set()
    for name in filenames:
        key = filename_key(name)
        if key in seen_keys:
            duplicate_keys.add(key)
        seen_keys.add(key)
    if duplicate_keys:
        raise LinkDataError(f"{path} has duplicate basenames: {', '.join(sorted(duplicate_keys)[:8])}")
    return filenames


def filename_lookup(filenames: tuple[str, ...]) -> dict[str, str]:
    return {filename_key(name): name for name in filenames}


def apply_filename_lookup(table: LinkDataTable, filename_lookup: Mapping[str, str]) -> LinkDataTable:
    symbols: list[LinkDataSymbolSpec] = []
    for spec in table.symbols:
        missing = tuple(name for name in spec.names if name is not None and filename_key(name) not in filename_lookup)
        if missing:
            raise LinkDataError(
                f"dw2_filenames.txt is missing names needed by {spec.symbol}: "
                f"{', '.join(missing[:8])}"
            )
        names = tuple(filename_lookup[filename_key(name)] if name is not None else None for name in spec.names)
        symbols.append(replace(spec, names=names))
    fixed: list[LinkDataFixedSpec] = []
    for spec in table.fixed:
        missing = tuple(name for name, offset, size in spec.records if name is not None and filename_key(name) not in filename_lookup)
        if missing:
            raise LinkDataError(
                f"dw2_filenames.txt is missing names needed by {spec.symbol}: "
                f"{', '.join(missing[:8])}"
            )
        records = tuple(
            (filename_lookup[filename_key(name)] if name is not None else None, offset, size)
            for name, offset, size in spec.records
        )
        fixed.append(replace(spec, records=records))
    sequences: list[LinkDataSequenceSpec] = []
    for spec in table.sequences:
        missing = tuple(name for name in spec.names if name is not None and filename_key(name) not in filename_lookup)
        if missing:
            raise LinkDataError(
                f"dw2_filenames.txt is missing names needed by {spec.symbol}: "
                f"{', '.join(missing[:8])}"
            )
        names = tuple(filename_lookup[filename_key(name)] if name is not None else None for name in spec.names)
        sequences.append(replace(spec, names=names))
    return replace(table, symbols=tuple(symbols), fixed=tuple(fixed), sequences=tuple(sequences))


EVENT_DIRECT_BASENAMES = {
    "MESSAGE.BIN",
    "MOUTH.BIN",
    "EVCHKPOS.BIN",
    "WONCAM0.BIN",
    "WONCAM1.BIN",
    "WONCAM2.BIN",
    "WONCAM3.BIN",
    "WONCAM4.BIN",
}


def event_sequence_names_from_filenames(filenames: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        name
        for name in filenames
        if name.upper().startswith("$(EVENT)\\")
        and filename_key(name) not in EVENT_DIRECT_BASENAMES
    )


def tables_with_makefile_sequences(filenames: tuple[str, ...]) -> dict[str, LinkDataTable]:
    tables = dict(TABLES)
    event_names = event_sequence_names_from_filenames(filenames)
    event_sequences = tuple(replace(spec, names=event_names) for spec in TABLES["event-data"].sequences)
    tables["event-data"] = replace(TABLES["event-data"], sequences=event_sequences)
    return tables


def linkdata_tables_from_filenames(filename_path: Path) -> dict[str, LinkDataTable]:
    filenames = read_linkdata_filenames(filename_path)
    lookup = filename_lookup(filenames)
    return {key: apply_filename_lookup(table, lookup) for key, table in tables_with_makefile_sequences(filenames).items()}


DIRECT_ETC_RECORDS = (
    ("$(ETC)\\title.tim", 0xE50C, 0x8D),
    ("$(ETC)\\tlfont0.tim", 0xE599, 0x07),
    ("$(ETC)\\tlfont1.tim", 0xE5A0, 0x13),
    ("$(ETC)\\tlfont2.tim", 0xE5B3, 0x0D),
    ("$(ETC)\\tlfont3.tim", 0xE5C0, 0x07),
    ("$(ETC)\\tlfont4.tim", 0xE5C7, 0x0D),
    ("$(STAGE)\\briefing.ob2", 0xE5D4, 0x05),
    ("$(ETC)\\gameover.tim", 0xE5D9, 0x8D),
)
DIRECT_ITEM_RECORDS = (
    ("$(ITEM)\\item.ob2", 0xE666, 0x9E),
    ("$(ITEM)\\item.tis", 0xE704, 0x11),
)
DIRECT_CHARA_EXTRA_RECORDS = (
    ("$(CHARA)\\KAKOUTON0.PS2", 0x1DCD, 0xA2),
    ("$(CHARA)\\CMNMOT.MOT", 0x3871, 0x49),
    ("$(CHARA)\\STARTMOT.MOT", 0x38BA, 0x163),
    ("$(CHARA)\\STARTMOT.MOV", 0x3A1D, 0x01),
    ("$(CHARA)\\controller.ps2", 0x47D0, 0xE0),
    ("$(CHARA)\\cont_map.tim", 0x48B0, 0x21),
)
DIRECT_MARK_RECORDS = (
    ("$(MARK)\\marker.tim", 0xE715, 0x32),
    ("$(MARK)\\smesdead.dat", 0xE747, 0x118),
    ("$(MARK)\\smeswin.dat", 0xE85F, 0x5A),
    ("$(MARK)\\smeslose.dat", 0xE8B9, 0x5A),
    ("$(MARK)\\smesbtl.dat", 0xE913, 0x40),
    ("$(MARK)\\stgtitle.dat", 0xE953, 0xD0),
    ("$(MARK)\\stgtlbg.tim", 0xEA23, 0x21),
)
DIRECT_CSEL_RECORDS = (
    ("$(CSEL)\\flag.tim", 0xEA44, 0x11),
    ("$(CSEL)\\stname.tim", 0xEA55, 0x11),
    ("$(CSEL)\\chinamap.tim", 0xEA66, 0x61),
    ("$(CSEL)\\fog_c01.clt", 0xEB5E, 0x01),
    ("$(CSEL)\\fog_c02.clt", 0xEB5F, 0x01),
    ("$(CSEL)\\fog_c03.clt", 0xEB60, 0x01),
)
DIRECT_STAGE_TAN_RECORDS = (
    ("$(ST_GPI)\\gappi.tan", 0x6423, 0x01),
    ("$(ST_GJN)\\gojougen.tan", 0x7D75, 0x01),
)
DIRECT_EFFECT_RECORDS = (
    ("$(EFF_TEX)\\fire.tm2", 0xEB61, 0x11),
    ("$(EFF_TEX)\\smo.tm2", 0xEB72, 0x11),
    ("$(EFF_TEX)\\sibuki.tm2", 0xEB83, 0x09),
    ("$(EFF_TEX)\\hit.tim", 0xEB8C, 0x05),
    ("$(EFF_TEX)\\particle.tim", 0xEB91, 0x01),
    ("$(EFF_TEX)\\cha.tim", 0xEB92, 0x09),
    ("$(EFF_TEX)\\piyo.tim", 0xEB9B, 0x01),
    ("$(EFF_TEX)\\gurd.tim", 0xEB9C, 0x03),
    ("$(EFF_TEX)\\hajiki.tim", 0xEB9F, 0x03),
    ("$(EFF_TEX)\\zeri.tim", 0xEBA2, 0x03),
    ("$(EFF_TEX)\\ram3.tim", 0xEBA5, 0x03),
    ("$(EFF_TEX)\\ram1.tim", 0xEBA8, 0x03),
    ("$(EFF_TEX)\\ram1b.clt", 0xEBAB, 0x01),
    ("$(EFF_TEX)\\ram1r.clt", 0xEBAC, 0x01),
    ("$(EFF_TEX)\\ram1g.clt", 0xEBAD, 0x01),
    ("$(EFF_TEX)\\ram1p.clt", 0xEBAE, 0x01),
    ("$(EFF_TEX)\\ram1c.clt", 0xEBAF, 0x01),
    ("$(EFF_TEX)\\ram2b.clt", 0xEBB0, 0x01),
    ("$(EFF_TEX)\\ram2r.clt", 0xEBB1, 0x01),
    ("$(EFF_TEX)\\ram2g.clt", 0xEBB2, 0x01),
    ("$(EFF_TEX)\\ram2p.clt", 0xEBB3, 0x01),
    ("$(EFF_TEX)\\ram2c.clt", 0xEBB4, 0x01),
    ("$(EFF_TEX)\\hei_tex.tim", 0xEBB5, 0x03),
    ("$(EFF_TEX)\\star01.tim", 0xEBB8, 0x02),
    ("$(EFF_TEX)\\snow.tim", 0xEBBA, 0x01),
    ("$(EFF_TEX)\\sun00.tim", 0xEBBB, 0x03),
)
DIRECT_EVENT_RECORDS = (
    ("$(EVENT)\\message.bin", 0xEC6B, 0x07),
    ("$(EVENT)\\mouth.bin", 0xEC72, 0x04),
    ("$(EVENT)\\evchkpos.bin", 0xEC76, 0x02),
    ("$(EVENT)\\woncam0.bin", 0xEC78, 0x01),
    ("$(EVENT)\\woncam1.bin", 0xEC79, 0x01),
    ("$(EVENT)\\woncam2.bin", 0xEC7A, 0x01),
    ("$(EVENT)\\woncam3.bin", 0xEC7B, 0x01),
    ("$(EVENT)\\woncam4.bin", 0xEC7C, 0x01),
)
DIRECT_OPTION_RECORDS = (
    ("$(OPTION)\\option.bin", 0xEC7D, 0xF0),
    ("$(OPTION)\\koei_end00.tim", 0xED6D, 0xD3),
    ("$(OPTION)\\koei_end01.tim", 0xEE40, 0xD3),
    ("$(OPTION)\\test.tm2", 0xEF13, 0x97),
    ("$(OPTION)\\tgs_end0.tim", 0xEFAA, 0x8D),
    ("$(OPTION)\\tgs_end1.tim", 0xF037, 0x8D),
    ("$(OPTION)\\kanji.tim", 0xF0C4, 0x41),
)
DIRECT_MCARD_RECORDS = (
    ("$(MCARD)\\kessen.ico", 0xF105, 0x31),
    ("$(MCARD)\\gi.ico", 0xF136, 0x31),
    ("$(MCARD)\\go.ico", 0xF167, 0x31),
    ("$(MCARD)\\shoku.ico", 0xF198, 0x31),
)
DIRECT_ENDING_RECORDS = (
    ("$(OPTION)\\ending.bin", 0xF1C9, 0x97),
    ("$(OPTION)\\end_000.tm2", 0xF260, 0x97),
    ("$(OPTION)\\end_001.tm2", 0xF2F7, 0x97),
    ("$(OPTION)\\end_002.tm2", 0xF38E, 0x97),
    ("$(OPTION)\\end_003.tm2", 0xF425, 0x97),
    ("$(OPTION)\\end_004.tm2", 0xF4BC, 0x97),
    ("$(OPTION)\\end_005.tm2", 0xF553, 0x97),
    ("$(OPTION)\\end_006.tm2", 0xF5EA, 0x97),
    ("$(OPTION)\\end_007.tm2", 0xF681, 0x97),
)


TABLES = {
    "tim": LinkDataTable(
        "tim",
        "character TIM textures",
        (LinkDataSymbolSpec("tim_file_sec", names(CHARACTER_TIM_NAMES, ".TIM"), ".TIM", include_zero_offset=True),),
    ),
    "model": LinkDataTable(
        "model",
        "character PS2 models",
        (LinkDataSymbolSpec("model_file_sec", names(CHARACTER_MODEL_NAMES, ".PS2"), ".PS2"),),
    ),
    "face": LinkDataTable(
        "face",
        "character face animation files",
        (LinkDataSymbolSpec("face_mot_sec", names(CHARACTER_MODEL_NAMES, ".FA"), ".FA"),),
    ),
    "pm": LinkDataTable(
        "pm",
        "character pose motion files",
        (LinkDataSymbolSpec("player_motion_file", names(POSE_MOTION_NAMES, ".PM"), ".PM"),),
    ),
    "motion": LinkDataTable(
        "motion",
        "character motion files",
        (LinkDataSymbolSpec("motion_file_sec", names(MOTION_NAMES, ".MOT"), ".MOT"),),
    ),
    "mov": LinkDataTable(
        "mov",
        "character motion-vector files",
        (LinkDataSymbolSpec("mov_file_sec", names(MOTION_NAMES, ".MOV"), ".MOV"),),
    ),
    "atk": LinkDataTable(
        "atk",
        "character attack metadata",
        (LinkDataSymbolSpec("atk_file_sec", names(MOTION_NAMES, ".ATK"), ".ATK"),),
    ),
    "horse-model": LinkDataTable(
        "horse-model",
        "horse PS2 models",
        (LinkDataSymbolSpec("horse_model", names(HORSE_NAMES, ".PS2"), ".PS2"),),
    ),
    "horse-tim": LinkDataTable(
        "horse-tim",
        "horse TIM textures",
        (LinkDataSymbolSpec("horse_tim", names(HORSE_NAMES, ".TIM"), ".TIM"),),
    ),
    "weapon": LinkDataTable(
        "weapon",
        "weapon PS2 models",
        (LinkDataSymbolSpec("weapon_mdl_sec", names(WEAPON_NAMES, ".PS2"), ".PS2"),),
    ),
    "weapon-tim": LinkDataTable(
        "weapon-tim",
        "weapon TIM texture",
        (LinkDataSymbolSpec("weapon_tim", ("WEAPON.TIM",), ".TIM"),),
    ),
    "locus-tim": LinkDataTable(
        "locus-tim",
        "weapon locus TIM texture",
        (LinkDataSymbolSpec("locus_tim", ("RAM2.TIM",), ".TIM"),),
    ),
    "event-motion": LinkDataTable(
        "event-motion",
        "event MOT files",
        (LinkDataSymbolSpec("event_motion_sec", names(EVENT_MOTION_NAMES, ".MOT"), ".MOT"),),
    ),
    "event-mov": LinkDataTable(
        "event-mov",
        "event MOV files",
        (LinkDataSymbolSpec("event_mov_sec", names(EVENT_MOTION_NAMES, ".MOV"), ".MOV"),),
    ),
    "algo": LinkDataTable(
        "algo",
        "battle algorithm data",
        (LinkDataSymbolSpec("algo_file_sec", ALGO_NAMES, ".BIN"),),
    ),
    "map": LinkDataTable(
        "map",
        "small map TIM files",
        (LinkDataSymbolSpec("map_file_sec", names(MAP_NAMES, ".TIM"), ".TIM"),),
    ),
    "direct-etc": LinkDataTable(
        "direct-etc",
        "literal sector reads for title/font/briefing/gameover files",
        (),
        (LinkDataFixedSpec("mips_direct_etc", DIRECT_ETC_RECORDS),),
    ),
    "direct-item": LinkDataTable(
        "direct-item",
        "literal sector reads for item files",
        (),
        (LinkDataFixedSpec("mips_direct_item", DIRECT_ITEM_RECORDS),),
    ),
    "direct-chara": LinkDataTable(
        "direct-chara",
        "literal and sequential character/support files",
        (),
        (LinkDataFixedSpec("mips_direct_chara", DIRECT_CHARA_EXTRA_RECORDS),),
    ),
    "direct-mark": LinkDataTable(
        "direct-mark",
        "literal and sequential marker/stage-title files",
        (),
        (LinkDataFixedSpec("mips_direct_mark", DIRECT_MARK_RECORDS),),
    ),
    "direct-csel": LinkDataTable(
        "direct-csel",
        "literal sector reads for character/stage-select files",
        (),
        (LinkDataFixedSpec("mips_direct_csel", DIRECT_CSEL_RECORDS),),
    ),
    "direct-effect": LinkDataTable(
        "direct-effect",
        "literal and sequential effect texture sector reads",
        (),
        (LinkDataFixedSpec("mips_direct_effect", DIRECT_EFFECT_RECORDS),),
    ),
    "direct-event": LinkDataTable(
        "direct-event",
        "literal sector reads for common event support files",
        (),
        (LinkDataFixedSpec("mips_direct_event", DIRECT_EVENT_RECORDS),),
    ),
    "direct-option": LinkDataTable(
        "direct-option",
        "literal sector reads for option/ending textures",
        (),
        (LinkDataFixedSpec("mips_direct_option", DIRECT_OPTION_RECORDS),),
    ),
    "direct-mcard": LinkDataTable(
        "direct-mcard",
        "sequential memory-card icon files",
        (),
        (LinkDataFixedSpec("inferred_mcard_sequence", DIRECT_MCARD_RECORDS),),
    ),
    "direct-ending": LinkDataTable(
        "direct-ending",
        "ending still files from still_load's sector base",
        (),
        (LinkDataFixedSpec("mips_direct_ending", DIRECT_ENDING_RECORDS),),
    ),
    "stage-gob": LinkDataTable(
        "stage-gob",
        "stage GOB files",
        (LinkDataSymbolSpec("gobjFile", stage_names(".GOB"), ".GOB"),),
    ),
    "stage-fob": LinkDataTable(
        "stage-fob",
        "stage FOB files",
        (LinkDataSymbolSpec("fobjFile", stage_names(".FOB"), ".FOB"),),
    ),
    "stage-lb": LinkDataTable(
        "stage-lb",
        "stage line files",
        (LinkDataSymbolSpec("lineFile", stage_names(".LB"), ".LB"),),
    ),
    "stage-ulb": LinkDataTable(
        "stage-ulb",
        "stage unit-line files",
        (LinkDataSymbolSpec("unitLineFile", stage_names(".ULB"), ".ULB"),),
    ),
    "stage-cob": LinkDataTable(
        "stage-cob",
        "stage collision/object files",
        (LinkDataSymbolSpec("cobjFile", stage_names(".COB"), ".COB"),),
    ),
    "stage-seb": LinkDataTable(
        "stage-seb",
        "stage SEB files",
        (LinkDataSymbolSpec("sebFile", stage_names(".SEB"), ".SEB"),),
    ),
    "stage-ab": LinkDataTable(
        "stage-ab",
        "stage weather/area files",
        (LinkDataSymbolSpec("weatherFile", stage_names(".AB"), ".AB"),),
    ),
    "stage-stg": LinkDataTable(
        "stage-stg",
        "stage STG files from the load_stage_data table",
        (LinkDataSymbolSpec("rodata_3D91C0_stage_stg", stage_paths(".stg"), ".stg", address=0x3D91C0),),
    ),
    "stage-obj": LinkDataTable(
        "stage-obj",
        "stage OBJ files from the load_stage_data table",
        (LinkDataSymbolSpec("rodata_3D9240_stage_obj", stage_paths(".obj"), ".obj", address=0x3D9240),),
    ),
    "stage-tis": LinkDataTable(
        "stage-tis",
        "stage TIS texture files from load_stage_texture",
        (LinkDataSymbolSpec("rodata_3D90C0_stage_tis", stage_paths(".tis"), ".tis", address=0x3D90C0),),
    ),
    "stage-ob2": LinkDataTable(
        "stage-ob2",
        "stage OB2 files from the load_stage_data table",
        (LinkDataSymbolSpec("rodata_3D92C0_stage_ob2", stage_paths(".ob2"), ".ob2", address=0x3D92C0),),
    ),
    "stage-sky": LinkDataTable(
        "stage-sky",
        "stage sky TIS files from the sky texture table",
        (LinkDataSymbolSpec("rodata_3D2980_stage_sky", stage_sky_paths(), ".tis", address=0x3D2980),),
    ),
    "stage-tan": LinkDataTable(
        "stage-tan",
        "stage TAN files inferred from adjacent stage table gaps",
        (),
        (LinkDataFixedSpec("inferred_stage_tan", DIRECT_STAGE_TAN_RECORDS),),
    ),
    "stage-lgt": LinkDataTable(
        "stage-lgt",
        "stage LGT files from load_stage_light",
        (LinkDataSymbolSpec("rodata_3CC210_stage_lgt", stage_paths(".lgt"), ".lgt", address=0x3CC210),),
    ),
    "stage-van": LinkDataTable(
        "stage-van",
        "stage VAN files from the stage optional-data table",
        (
            LinkDataSymbolSpec(
                "rodata_3D9340_stage_van",
                stage_optional_paths(".van", (True, True, False, True, True, True, True, False)),
                ".van",
                address=0x3D9340,
            ),
        ),
    ),
    "stage-minimap": LinkDataTable(
        "stage-minimap",
        "stage minimap OBJ files from load_briefing_stage",
        (LinkDataSymbolSpec("rodata_3D9140_stage_minimap", stage_minimap_paths(), ".obj", address=0x3D9140),),
    ),
    "stage-ob3": LinkDataTable(
        "stage-ob3",
        "stage OB3 files from the stage optional-data table",
        (
            LinkDataSymbolSpec(
                "rodata_3D93C0_stage_ob3",
                stage_optional_paths(".ob3", (True, False, True, True, True, True, True, True)),
                ".ob3",
                address=0x3D93C0,
            ),
        ),
    ),
    "select-still": LinkDataTable(
        "select-still",
        "character/stage-select still TIM files",
        (LinkDataSymbolSpec("ststill_file_sec", names(STILL_NAMES, ".TIM"), ".TIM"),),
    ),
    "select-fog": LinkDataTable(
        "select-fog",
        "character/stage-select fog TIM files",
        (LinkDataSymbolSpec("stfog_file_sec", names(FOG_NAMES, ".TIM"), ".TIM"),),
    ),
    "sound-hd": LinkDataTable(
        "sound-hd",
        "sound header files; size word is byte length",
        (
            LinkDataSymbolSpec("msCommonHdFile", sound_paths(("system", "attack", "move", "generalv"), ".hd"), ".HD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msEnvHdFile", sound_paths(SOUND_ENV_STEMS, ".hd"), ".HD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msPlHdFile", sound_paths(SOUND_PLAYER_STEMS, ".hd"), ".HD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msFaHdFile", sound_paths(SOUND_FA_STEMS, ".hd"), ".HD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msMenuHdFile", sound_menu_paths(".hd"), ".HD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msBriefingHdFile", sound_briefing_paths(".hd"), ".HD", size_mode=SIZE_BYTES_ALIGNED),
        ),
    ),
    "sound-bd": LinkDataTable(
        "sound-bd",
        "sound body files; size word is byte length",
        (
            LinkDataSymbolSpec("msCommonBdFile", sound_paths(("system", "attack", "move", "generalv"), ".bd"), ".BD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msEnvBdFile", sound_paths(SOUND_ENV_STEMS, ".bd"), ".BD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msPlBdFile", sound_paths(SOUND_PLAYER_STEMS, ".bd"), ".BD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msFaBdFile", sound_paths(SOUND_FA_STEMS, ".bd"), ".BD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msMenuBdFile", sound_menu_paths(".bd"), ".BD", size_mode=SIZE_BYTES_ALIGNED),
            LinkDataSymbolSpec("msBriefingBdFile", sound_briefing_paths(".bd"), ".BD", size_mode=SIZE_BYTES_ALIGNED),
        ),
    ),
    "event-data": LinkDataTable(
        "event-data",
        "event binary/camera sequence from compact 8 byte tables",
        (),
        sequences=(
            LinkDataSequenceSpec(
                "event_sequence",
                (
                    LinkDataSymbolSpec("_nCmnEveCsv", extension=".bin", stride=PAIR_STRUCT.size),
                    LinkDataSymbolSpec("_nCmnEveCam", extension=".bin", stride=PAIR_STRUCT.size),
                    LinkDataSymbolSpec("_nStgEve", extension=".bin", stride=PAIR_STRUCT.size),
                    LinkDataSymbolSpec("_nGateEve", extension=".bin", stride=PAIR_STRUCT.size),
                ),
                extension=".bin",
            ),
        ),
    ),
    "win-cam": LinkDataTable(
        "win-cam",
        "victory camera/event snippets; compact 8 byte records with reused entries",
        (LinkDataSymbolSpec("_nWinCam", extension=".BIN", stride=PAIR_STRUCT.size),),
    ),
}


FULL_TABLE_KEYS = (
    "tim",
    "horse-tim",
    "model",
    "face",
    "horse-model",
    "pm",
    "motion",
    "mov",
    "atk",
    "event-motion",
    "event-mov",
    "weapon-tim",
    "locus-tim",
    "weapon",
    "algo",
    "map",
    "direct-etc",
    "direct-item",
    "direct-chara",
    "direct-mark",
    "direct-csel",
    "direct-effect",
    "direct-event",
    "direct-option",
    "direct-mcard",
    "direct-ending",
    "stage-gob",
    "stage-fob",
    "stage-lb",
    "stage-ulb",
    "stage-cob",
    "stage-seb",
    "stage-ab",
    "stage-stg",
    "stage-obj",
    "stage-tis",
    "stage-ob2",
    "stage-sky",
    "stage-tan",
    "stage-lgt",
    "stage-van",
    "stage-minimap",
    "stage-ob3",
    "select-still",
    "select-fog",
    "sound-hd",
    "sound-bd",
    "event-data",
    "win-cam",
)


class LinkDataError(ValueError):
    """Raised when LINKDATA or ELF contents dont match the known tables"""


def align(value: int, alignment: int = PAYLOAD_SECTOR_SIZE) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def entry_size(size_units: int, mode: str) -> int:
    if mode == SIZE_SECTORS:
        return size_units << PAYLOAD_SECTOR_SHIFT
    if mode == SIZE_BYTES_ALIGNED:
        return align(size_units)
    raise LinkDataError(f"Unknown size mode {mode!r}")


def symbol_bytes(elf_path: Path, symbol_name: str) -> bytes:
    with elf_path.open("rb") as handle:
        elf = ELFFile(handle)
        symbol_table = elf.get_section_by_name(".symtab")
        if symbol_table is None:
            raise LinkDataError(f"{elf_path} has no .symtab")
        symbol = next((item for item in symbol_table.iter_symbols() if item.name == symbol_name), None)
        if symbol is None:
            raise LinkDataError(f"Couldn't find ELF symbol {symbol_name!r}")

        address = symbol["st_value"]
        size = symbol["st_size"]
        for section in elf.iter_sections():
            start = section["sh_addr"]
            end = start + section["sh_size"]
            if not (section["sh_flags"] & 2):
                continue
            if start <= address and address + size <= end:
                data = section.data()
                return data[address - start : address - start + size]
    raise LinkDataError(f"Couldn't read ELF symbol bytes for {symbol_name!r}")


def address_bytes(elf_path: Path, address: int, size: int, label: str) -> bytes:
    with elf_path.open("rb") as handle:
        elf = ELFFile(handle)
        for section in elf.iter_sections():
            start = section["sh_addr"]
            end = start + section["sh_size"]
            if not (section["sh_flags"] & 2):
                continue
            if start <= address and address + size <= end:
                data = section.data()
                return data[address - start : address - start + size]
    raise LinkDataError(f"Couldn't read ELF bytes for {label!r} at 0x{address:X}")


def symbol_location(elf_path: Path, symbol_name: str) -> tuple[int, int, int]:
    with elf_path.open("rb") as handle:
        elf = ELFFile(handle)
        symbol_table = elf.get_section_by_name(".symtab")
        if symbol_table is None:
            raise LinkDataError(f"{elf_path} has no .symtab")
        symbol = next((item for item in symbol_table.iter_symbols() if item.name == symbol_name), None)
        if symbol is None:
            raise LinkDataError(f"Couldn't find ELF symbol {symbol_name!r}")

        address = symbol["st_value"]
        size = symbol["st_size"]
        for section in elf.iter_sections():
            start = section["sh_addr"]
            end = start + section["sh_size"]
            if not (section["sh_flags"] & 2):
                continue
            if start <= address and address + size <= end:
                return section["sh_offset"] + (address - start), address, size
    raise LinkDataError(f"Couldn't locate ELF symbol {symbol_name!r}")


def address_location(elf_path: Path, address: int, size: int, label: str) -> tuple[int, int, int]:
    with elf_path.open("rb") as handle:
        elf = ELFFile(handle)
        for section in elf.iter_sections():
            start = section["sh_addr"]
            end = start + section["sh_size"]
            if not (section["sh_flags"] & 2):
                continue
            if start <= address and address + size <= end:
                return section["sh_offset"] + (address - start), address, size
    raise LinkDataError(f"Couldn't locate ELF bytes for {label!r} at 0x{address:X}")


def spec_location(elf_path: Path, spec: LinkDataSymbolSpec) -> tuple[int, int, int]:
    if spec.address is None:
        return symbol_location(elf_path, spec.symbol)
    size = spec.byte_size if spec.byte_size is not None else len(spec.names) * spec.stride
    if size <= 0:
        raise LinkDataError(f"{spec.symbol} needs byte_size or names when using an absolute address")
    return address_location(elf_path, spec.address, size, spec.symbol)


def spec_bytes(elf_path: Path, spec: LinkDataSymbolSpec) -> bytes:
    if spec.address is None:
        return symbol_bytes(elf_path, spec.symbol)
    size = spec.byte_size if spec.byte_size is not None else len(spec.names) * spec.stride
    if size <= 0:
        raise LinkDataError(f"{spec.symbol} needs byte_size or names when using an absolute address")
    return address_bytes(elf_path, spec.address, size, spec.symbol)


def read_table(
    elf_path: Path,
    table: LinkDataTable,
    *,
    linkdata_size: int | None = None,
    include_unnamed: bool = False,
) -> tuple[LinkDataEntry, ...]:
    entries: list[LinkDataEntry] = []
    for spec in table.symbols:
        data = spec_bytes(elf_path, spec)
        spec_file_offset, spec_vaddr, spec_size = spec_location(elf_path, spec)
        if spec.stride not in (PAIR_STRUCT.size, ENTRY_STRUCT.size):
            raise LinkDataError(f"Unsupported stride {spec.stride} for {spec.symbol}")
        if len(data) % spec.stride:
            raise LinkDataError(f"{spec.symbol} size 0x{len(data):X} is not aligned to stride {spec.stride}")

        for raw_index in range(len(data) // spec.stride):
            entry_offset = raw_index * spec.stride
            if spec.stride == ENTRY_STRUCT.size:
                offset_units, size_units, aux0, aux1 = ENTRY_STRUCT.unpack_from(data, entry_offset)
            else:
                offset_units, size_units = PAIR_STRUCT.unpack_from(data, entry_offset)
                aux0 = aux1 = 0

            if size_units == 0 and offset_units == 0:
                continue
            if offset_units == 0 and not spec.include_zero_offset:
                continue

            offset = offset_units << PAYLOAD_SECTOR_SHIFT
            size = entry_size(size_units, spec.size_mode)
            if linkdata_size is not None and offset + size > linkdata_size:
                continue

            public_index = raw_index + spec.index_base
            name = spec.names[raw_index] if raw_index < len(spec.names) else None
            if name is None:
                if not include_unnamed:
                    continue
                name = f"{fallback_symbol_name(spec.symbol)}_{public_index:03d}{spec.extension}"
            entries.append(
                LinkDataEntry(
                    table=table.key,
                    symbol=spec.symbol,
                    index=public_index,
                    name=name,
                    offset_units=offset_units,
                    size_units=size_units,
                    offset=offset,
                    size=size,
                    raw_size=size_units,
                    aux0=aux0,
                    aux1=aux1,
                    toc_file_offset=spec_file_offset + entry_offset,
                    toc_vaddr=spec_vaddr + entry_offset,
                    toc_bytes=data[entry_offset : entry_offset + spec.stride],
                )
            )
    for spec in table.sequences:
        unique_records: dict[tuple[int, int], tuple[int, int, int, int, int, int | None, int | None, bytes]] = {}
        for source in spec.sources:
            data = spec_bytes(elf_path, source)
            source_file_offset, source_vaddr, source_size = spec_location(elf_path, source)
            if source.stride not in (PAIR_STRUCT.size, ENTRY_STRUCT.size):
                raise LinkDataError(f"Unsupported stride {source.stride} for {source.symbol}")
            if len(data) % source.stride:
                raise LinkDataError(f"{source.symbol} size 0x{len(data):X} is not aligned to stride {source.stride}")

            for raw_index in range(len(data) // source.stride):
                entry_offset = raw_index * source.stride
                if source.stride == ENTRY_STRUCT.size:
                    offset_units, size_units, aux0, aux1 = ENTRY_STRUCT.unpack_from(data, entry_offset)
                else:
                    offset_units, size_units = PAIR_STRUCT.unpack_from(data, entry_offset)

                if size_units == 0 and offset_units == 0:
                    continue
                if offset_units == 0 and not source.include_zero_offset:
                    continue

                offset = offset_units << PAYLOAD_SECTOR_SHIFT
                size = entry_size(size_units, source.size_mode)
                if linkdata_size is not None and offset + size > linkdata_size:
                    continue
                unique_records.setdefault(
                    (offset, size),
                    (
                        offset_units,
                        size_units,
                        offset,
                        size,
                        size_units,
                        source_file_offset + entry_offset,
                        source_vaddr + entry_offset,
                        data[entry_offset : entry_offset + source.stride],
                    ),
                )

        sorted_records = tuple(record for key, record in sorted(unique_records.items()))
        if len(spec.names) > len(sorted_records):
            raise LinkDataError(
                f"{spec.symbol} has {len(spec.names)} names but only {len(sorted_records)} unique sector ranges"
            )
        for raw_index, (
            offset_units,
            size_units,
            offset,
            size,
            raw_size,
            toc_file_offset,
            toc_vaddr,
            toc_bytes,
        ) in enumerate(sorted_records):
            public_index = raw_index + spec.index_base
            name = spec.names[raw_index] if raw_index < len(spec.names) else None
            if name is None:
                if not include_unnamed:
                    continue
                name = f"{fallback_symbol_name(spec.symbol)}_{public_index:03d}{spec.extension}"
            entries.append(
                LinkDataEntry(
                    table=table.key,
                    symbol=spec.symbol,
                    index=public_index,
                    name=name,
                    offset_units=offset_units,
                    size_units=size_units,
                    offset=offset,
                    size=size,
                    raw_size=raw_size,
                    toc_file_offset=toc_file_offset,
                    toc_vaddr=toc_vaddr,
                    toc_bytes=toc_bytes,
                )
            )
    for spec in table.fixed:
        for raw_index, (record_name, offset_units, size_units) in enumerate(spec.records):
            if size_units == 0 and offset_units == 0:
                continue

            offset = offset_units << PAYLOAD_SECTOR_SHIFT
            size = entry_size(size_units, spec.size_mode)
            if linkdata_size is not None and offset + size > linkdata_size:
                continue

            public_index = raw_index + spec.index_base
            name = record_name
            if name is None:
                if not include_unnamed:
                    continue
                name = f"{fallback_symbol_name(spec.symbol)}_{public_index:03d}{spec.extension}"
            entries.append(
                LinkDataEntry(
                    table=table.key,
                    symbol=spec.symbol,
                    index=public_index,
                    name=name,
                    offset_units=offset_units,
                    size_units=size_units,
                    offset=offset,
                    size=size,
                    raw_size=size_units,
                )
            )
    return tuple(entries)


def read_full_manifest(
    elf_path: Path,
    linkdata_size: int | None = None,
    *,
    tables: Mapping[str, LinkDataTable] | None = None,
    include_unnamed: bool = False,
) -> tuple[LinkDataEntry, ...]:
    table_lookup = tables or TABLES
    entries: list[LinkDataEntry] = []
    for key in FULL_TABLE_KEYS:
        entries.extend(
            read_table(
                elf_path,
                table_lookup[key],
                linkdata_size=linkdata_size,
                include_unnamed=include_unnamed,
            )
        )
    return tuple(sorted(entries, key=lambda entry: (entry.offset, entry.table, entry.symbol, entry.index)))


def entry_by_request(entries: tuple[LinkDataEntry, ...], *, index: int | None, name: str | None) -> LinkDataEntry:
    if name:
        wanted = name.upper()
        for entry in entries:
            if (
                entry.name.upper() == wanted
                or filename_key(entry.name) == wanted
                or filename_stem_key(entry.name) == wanted
            ):
                return entry
        raise LinkDataError(f"Couldn't find entry named {name!r}")
    if index is None:
        raise LinkDataError("Provide --index or --name, or use --list/--unpack-all.")
    for entry in entries:
        if entry.index == index:
            return entry
    raise LinkDataError(f"Couldn't find entry index {index}")


def safe_output_name(entry: LinkDataEntry) -> Path:
    cleaned_parts: list[str] = []
    has_filename_folder = False
    for part in PurePosixPath(entry.name.replace("\\", "/")).parts:
        if part in ("", ".", ".."):
            continue
        variable_match = re.fullmatch(r"\$\(([^)]+)\)", part)
        if variable_match:
            part = variable_match.group(1)
            has_filename_folder = True
        cleaned = re.sub(r"[^A-Za-z0-9._+-]+", "_", part)
        cleaned_parts.append(cleaned or "_")
    if not cleaned_parts:
        cleaned_parts.append(f"{entry.symbol}_{entry.index:03d}.bin")
    if not has_filename_folder:
        cleaned_parts.insert(0, "misc")
    return Path(*cleaned_parts)


def has_filename_folder(entry: LinkDataEntry) -> bool:
    first_part = next(iter(PurePosixPath(entry.name.replace("\\", "/")).parts), "")
    return re.fullmatch(r"\$\([^)]+\)", first_part) is not None


def write_unpack_summary(path: Path, filenames: tuple[str, ...], entries: tuple[LinkDataEntry, ...]) -> None:
    extracted_txt_names = {filename_identity(entry.name) for entry in entries}
    skipped_filenames = tuple(name for name in filenames if filename_identity(name) not in extracted_txt_names)
    unique_ranges = {(entry.offset, entry.size) for entry in entries}
    sector_counts: dict[tuple[str, str], int] = {}
    for entry in entries:
        key = (entry.table, entry.symbol)
        sector_counts[key] = sector_counts.get(key, 0) + 1

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("DW2 LINKDATA unpack summary\n")
        handle.write(f"txt_filenames={len(filenames)}\n")
        handle.write(f"extracted_entries={len(entries)}\n")
        handle.write(f"unique_extracted_ranges={len(unique_ranges)}\n")
        handle.write(f"duplicate_alias_entries={len(entries) - len(unique_ranges)}\n")
        handle.write(f"txt_named_extracted_entries={len(extracted_txt_names)}\n")
        handle.write(f"txt_filenames_not_extracted={len(skipped_filenames)}\n")
        handle.write("\n")
        handle.write(
            "Only entries with a dw2_filenames.txt name were unpacked. "
            "Fallback sector-table names are intentionally skipped.\n"
        )
        handle.write("\n")
        handle.write("[sector_tables]\n")
        for (table, symbol), count in sorted(sector_counts.items()):
            handle.write(f"{table}\t{symbol}\t{count}\n")
        handle.write("\n")
        handle.write("[txt_filenames_not_extracted]\n")
        for name in skipped_filenames:
            handle.write(f"{name}\n")


def unique_path(path: Path, used: set[Path]) -> Path:
    if path not in used:
        used.add(path)
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter:02d}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def write_entry(linkdata: bytes, entry: LinkDataEntry, output_path: Path, *, dry_run: bool = False) -> None:
    if entry.end_offset > len(linkdata):
        raise LinkDataError(f"{entry.name} extends past EOF of LINKDATA.BNS")
    if dry_run:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(linkdata[entry.offset : entry.end_offset])


def iter_gaps(entries: tuple[LinkDataEntry, ...], linkdata_size: int) -> tuple[tuple[int, int], ...]:
    gaps: list[tuple[int, int]] = []
    cursor = 0
    for entry in sorted(entries, key=lambda item: item.offset):
        if entry.offset > cursor:
            gaps.append((cursor, entry.offset))
        cursor = max(cursor, entry.end_offset)
    if cursor < linkdata_size:
        gaps.append((cursor, linkdata_size))
    return tuple((start, end) for start, end in gaps if end > start)


def print_entries(entries: tuple[LinkDataEntry, ...], linkdata: bytes | None = None) -> None:
    for entry in entries:
        magic = b""
        if linkdata is not None and entry.offset + 4 <= len(linkdata):
            magic = linkdata[entry.offset : entry.offset + 4]
        print(
            f"{entry.index:03d} {entry.name:24s} "
            f"table={entry.table:12s} symbol={entry.symbol:18s} "
            f"offset=0x{entry.offset:X} size=0x{entry.size:X} raw_size=0x{entry.raw_size:X} magic={magic!r}"
        )


def write_manifest(path: Path, entries: tuple[LinkDataEntry, ...], *, gaps: tuple[tuple[int, int], ...] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("table\tsymbol\tindex\tname\toffset\tsize\tend\traw_size\taux0\taux1\n")
        for entry in entries:
            handle.write(
                f"{entry.table}\t{entry.symbol}\t{entry.index}\t{entry.name}\t"
                f"0x{entry.offset:X}\t0x{entry.size:X}\t0x{entry.end_offset:X}\t"
                f"0x{entry.raw_size:X}\t0x{entry.aux0:X}\t0x{entry.aux1:X}\n"
            )
        for index, (start, end) in enumerate(gaps):
            handle.write(
                f"__gap__\t__gap__\t{index}\tgap_{start:08X}_{end:08X}.bin\t"
                f"0x{start:X}\t0x{end - start:X}\t0x{end:X}\t0x{end - start:X}\t0x0\t0x0\n"
            )


def tocValue(value: int | None) -> str:
    return "-" if value is None else f"0x{value:X}"


def write_toc_report(path: Path, entries: tuple[LinkDataEntry, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "name\ttable\tsymbol\tindex\ttoc_file_offset\ttoc_vaddr\ttoc_bytes\t"
            "offset_units\tsize_units\taux0\taux1\tlinkdata_offset\tlinkdata_size\tlinkdata_end\n"
        )
        for entry in entries:
            handle.write(
                f"{entry.name}\t{entry.table}\t{entry.symbol}\t{entry.index}\t"
                f"{tocValue(entry.toc_file_offset)}\t{tocValue(entry.toc_vaddr)}\t{entry.toc_bytes.hex() or '-'}\t"
                f"0x{entry.offset_units:X}\t0x{entry.size_units:X}\t0x{entry.aux0:X}\t0x{entry.aux1:X}\t"
                f"0x{entry.offset:X}\t0x{entry.size:X}\t0x{entry.end_offset:X}\n"
            )


def discover_tables(elf_path: Path, *, linkdata_size: int) -> tuple[tuple[str, int, int, int, int], ...]:
    """Return plausible ELF object symbols that look like LINKDATA tables"""
    results: list[tuple[str, int, int, int, int]] = []
    with elf_path.open("rb") as handle:
        elf = ELFFile(handle)
        symbol_table = elf.get_section_by_name(".symtab")
        if symbol_table is None:
            return ()
        for symbol in symbol_table.iter_symbols():
            if symbol["st_info"]["type"] != "STT_OBJECT" or symbol["st_size"] < PAIR_STRUCT.size:
                continue
            data = read_symbol_bytes_from_elf(elf, symbol)
            if not data:
                continue
            for stride in (PAIR_STRUCT.size, ENTRY_STRUCT.size):
                if len(data) % stride:
                    continue
                valid = 0
                invalid = 0
                for index in range(len(data) // stride):
                    offset_units, size_units = PAIR_STRUCT.unpack_from(data, index * stride)
                    if offset_units == 0 and size_units == 0:
                        continue
                    offset = offset_units << PAYLOAD_SECTOR_SHIFT
                    size = size_units << PAYLOAD_SECTOR_SHIFT
                    if size > 0 and offset + size <= linkdata_size:
                        valid += 1
                    else:
                        invalid += 1
                if valid >= 2 and invalid == 0:
                    results.append((symbol.name, symbol["st_value"], symbol["st_size"], stride, valid))
    return tuple(sorted(results, key=lambda item: (item[1], item[3])))

def read_symbol_bytes_from_elf(elf: ELFFile, symbol) -> bytes:
    address = symbol["st_value"]
    size = symbol["st_size"]
    for section in elf.iter_sections():
        start = section["sh_addr"]
        end = start + section["sh_size"]
        if not (section["sh_flags"] & 2):
            continue
        if start <= address and address + size <= end:
            data = section.data()
            return data[address - start : address - start + size]
    return b""


def unpack_all(
    elf_path,
    linkdata_path,
    outdir,
    filenames_path=None,
    *,
    include_gaps: bool = False,
    manifest_path=None,
    toc_report=None,
    dry_run: bool = False,
):
    """Unpack every filename-matched LINKDATA entry into outdir"""
    elf_path = Path(elf_path)
    linkdata_path = Path(linkdata_path)
    outdir = Path(outdir)
    filenames_path = Path(filenames_path) if filenames_path else DEFAULT_FILENAMES

    tables = linkdata_tables_from_filenames(filenames_path)
    linkdata = linkdata_path.read_bytes()
    entries = read_full_manifest(elf_path, linkdata_size=len(linkdata), tables=tables)
    gaps = iter_gaps(entries, len(linkdata)) if include_gaps else ()

    used_paths: set[Path] = set()
    for entry in entries:
        output_path = unique_path(outdir / safe_output_name(entry), used_paths)
        write_entry(linkdata, entry, output_path, dry_run=dry_run)
    if include_gaps:
        for index, (start, end) in enumerate(gaps):
            gap_path = outdir / "__gaps" / f"gap_{index:03d}_0x{start:X}_0x{end:X}.bin"
            if not dry_run:
                gap_path.parent.mkdir(parents=True, exist_ok=True)
                gap_path.write_bytes(linkdata[start:end])
    if manifest_path:
        write_manifest(Path(manifest_path), entries, gaps=gaps)
    toc_report_path = Path(toc_report) if toc_report else outdir / DEFAULT_TOC_REPORT_NAME
    if toc_report or not dry_run:
        write_toc_report(toc_report_path, entries)
    summary_path = outdir / DEFAULT_UNPACK_SUMMARY_NAME
    if not dry_run:
        write_unpack_summary(summary_path, read_linkdata_filenames(filenames_path), entries)
    return entries, gaps, outdir, summary_path


def find_game_files(folder: Path) -> tuple[Path | None, Path | None]:
    """Locate the ELF and LINKDATA.BNS inside a user-picked folder"""
    elf = linkdata = None
    for child in sorted(folder.iterdir()):
        if not child.is_file():
            continue
        name = child.name.upper()
        if linkdata is None and name == LINKDATA_NAME:
            linkdata = child
        elif elf is None and name == ELF_NAME:
            elf = child
    if elf is None:
        for child in sorted(folder.iterdir()):
            if child.is_file() and child.name.upper().startswith("SLUS_") \
                    and "HOSTFS" not in child.name.upper():
                elf = child
                break
    return elf, linkdata


def launch(parent=None, status=None):
    """Burn Engine hub entry point"""
    from tkinter import filedialog, messagebox

    def say(message):
        if status:
            status(message)

    folder = filedialog.askdirectory(
        parent=parent,
        title="Pick the folder holding SLUS_200.79 and LINKDATA.BNS",
        initialdir=str(GAME_DIR),
    )
    if not folder:
        say("LINKDATA unpack cancelled.")
        return None

    folder = Path(folder)
    elf, linkdata = find_game_files(folder)
    missing = [n for n, p in ((ELF_NAME, elf), (LINKDATA_NAME, linkdata)) if p is None]
    if missing:
        messagebox.showerror(
            "LINKDATA Unpacker",
            f"{folder} is missing: {', '.join(missing)}\n\n"
            "Pick the folder that holds both the game ELF and LINKDATA.BNS.",
            parent=parent,
        )
        say(f"Unpack aborted: no {', '.join(missing)} in {folder.name}.")
        return None
    if not DEFAULT_FILENAMES.is_file():
        messagebox.showerror(
            "LINKDATA Unpacker",
            f"dw2_filenames.txt is missing from {SCRIPT_DIR}.\n\n"
            "That list is the extraction allow-list, the unpacker needs it.",
            parent=parent,
        )
        say("Unpack aborted: dw2_filenames.txt missing.")
        return None

    outdir = folder / UNPACK_DIR_NAME
    say(f"Unpacking {linkdata.name} -> {outdir.name} ...")
    try:
        entries, gaps, outdir, summary_path = unpack_all(elf, linkdata, outdir)
    except Exception as exc:
        messagebox.showerror("LINKDATA Unpacker", f"Unpack failed:\n\n{exc}", parent=parent)
        say(f"Unpack failed: {exc}")
        return None

    say(f"Unpacked {len(entries)} entries -> {outdir}")
    messagebox.showinfo(
        "LINKDATA Unpacker",
        f"Extracted {len(entries)} entries from {linkdata.name}.\n\n"
        f"Output: {outdir}\nSummary: {summary_path.name}",
        parent=parent,
    )
    return outdir


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract DW2 LINKDATA.BNS assets using SLUS_200.79 sector tables.")
    parser.add_argument("--elf", default=str(GAME_DIR / ELF_NAME), help="DW2 ELF containing LINKDATA tables.")
    parser.add_argument("--linkdata", default=str(GAME_DIR / LINKDATA_NAME), help="Non-sectorized LINKDATA.BNS.")
    parser.add_argument(
        "--filenames",
        default=str(DEFAULT_FILENAMES),
        help="Makefile-style LINKDATA filename list, used as the extraction allow list.",
    )
    parser.add_argument("--table", choices=sorted(TABLES), default="model", help="Asset table to use.")
    parser.add_argument("--index", type=int, help="Table index to extract.")
    parser.add_argument("--name", help="Named table entry to extract, such as KANU.")
    parser.add_argument("--output", help="Output path for single file extraction.")
    parser.add_argument("--outdir", default=str(GAME_DIR / UNPACK_DIR_NAME), help="Output directory for --unpack-all.")
    parser.add_argument("--list", action="store_true", help="List table entries instead of extracting.")
    parser.add_argument("--tables", action="store_true", help="List curated table keys.")
    parser.add_argument("--unpack-all", action="store_true", help="Extract every curated LINKDATA table entry.")
    parser.add_argument("--include-gaps", action="store_true", help="Also write uncovered LINKDATA ranges as __gaps/*.bin.")
    parser.add_argument("--manifest", help="Write a TSV manifest for listed or unpacked entries.")
    parser.add_argument("--toc-report", help="Write filename to ELF TOC entry TSV report.")
    parser.add_argument("--dry-run", action="store_true", help="Show/list planned work without writing extracted files.")
    parser.add_argument("--discover", action="store_true", help="List broad ELF symbols that look table-like, diagnostic only.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    elf_path = Path(args.elf)
    linkdata_path = Path(args.linkdata)

    if args.tables:
        for key in sorted(TABLES):
            print(f"{key:14s} {TABLES[key].description}")
        return 0

    linkdata_size = linkdata_path.stat().st_size if linkdata_path.exists() else 0
    if args.discover:
        for name, address, size, stride, valid in discover_tables(elf_path, linkdata_size=linkdata_size):
            print(f"0x{address:08X} size=0x{size:X} stride={stride:2d} valid={valid:3d} {name}")
        return 0

    if args.unpack_all:
        entries, gaps, outdir, summary_path = unpack_all(
            elf_path, linkdata_path, args.outdir, args.filenames,
            include_gaps=args.include_gaps, manifest_path=args.manifest,
            toc_report=args.toc_report, dry_run=args.dry_run,
        )
        print(
            f"{'Planned' if args.dry_run else 'Extracted'} {len(entries)} filename-matched table entries"
            f"{' plus ' + str(len(gaps)) + ' gap ranges' if gaps else ''} -> {outdir}"
            f"{'' if args.dry_run else ' (summary: ' + str(summary_path) + ')'}"
        )
        return 0

    tables = linkdata_tables_from_filenames(Path(args.filenames))
    table = tables[args.table]
    entries = read_table(elf_path, table, linkdata_size=linkdata_size or None)

    if args.list:
        linkdata = linkdata_path.read_bytes() if linkdata_path.exists() else None
        print_entries(entries, linkdata)
        if args.manifest:
            write_manifest(Path(args.manifest), entries)
        if args.toc_report:
            write_toc_report(Path(args.toc_report), entries)
        return 0

    entry = entry_by_request(entries, index=args.index, name=args.name)
    linkdata = linkdata_path.read_bytes()

    if args.output:
        out = Path(args.output)
    elif args.table in {"model", "horse-model", "weapon"}:
        out = Path(__file__).resolve().parent / "models" / safe_output_name(entry)
    else:
        out = Path(__file__).resolve().parent / "extracted" / args.table / safe_output_name(entry)
    write_entry(linkdata, entry, out, dry_run=args.dry_run)
    print(
        f"{'Planned' if args.dry_run else 'Extracted'} {entry.name}: "
        f"offset=0x{entry.offset:X} size=0x{entry.size:X} symbol={entry.symbol} -> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
