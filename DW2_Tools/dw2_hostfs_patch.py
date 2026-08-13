"""Patch SLUS_200.79 so DW2 loads LINKDATA files from PCSX2's host filesystem"""

from __future__ import annotations

import argparse, struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GAME_DIR = SCRIPT_DIR.parent


def keystone_import_error(exc):
    try:
        import importlib.util
        spec = importlib.util.find_spec("keystone")
    except Exception:
        spec = None
    if spec is not None:
        return ImportError(
            "the importable 'keystone' isntt the assembler (found at %s). "
            "'pip install keystone' gets OpenStack Identity, the MIPS assembler "
            "is a different project. Fix with:  pip uninstall keystone  then  "
            "python -m pip install keystone-engine" % spec.origin
        )
    return ImportError(
        "keystone-engine isn't installed. Fix with: python -m pip install keystone-engine"
    )


try:
    from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN
except ImportError as exc:
    raise keystone_import_error(exc) from exc

from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN

SECTOR_SIZE = 0x800

ELF_VADDR_BASE = 0x200000
ELF_FILE_BASE = 0x1000

GDATA_SECTOR = 0x3E1C38
SEC_READ_LIST = 0x3E35C0
SEC_READ_LIST_CNT = 0x3E1C4C
SEC_READ_LIST_NOW = 0x3E1C50

FN_PMEMALIGN = 0x201CE8
FN_FLUSHCACHE = 0x329700
FN_SCE_OPEN = 0x32C698
FN_SCE_CLOSE = 0x32C7F0
FN_SCE_LSEEK = 0x32C8A8
FN_SCE_READ = 0x32CA18
FN_CD_DISKREADY = 0x307590
FN_CD_READ = 0x306888
FN_CD_SYNC = 0x307140
FN_CD_GETERROR = 0x307960

PATCH_SEC_READ = 0x20D9F0
PATCH_SEC_READ_BUF = 0x20DB88
PATCH_START_LIST = 0x20DDB0
PATCH_BLOCK_LIST = 0x20D7D8

CRT0_HEAP_LUI = 0x200070
CRT0_HEAP_ADDIU = 0x200078
HEAP_END_SYMBOL = 0x4CED54

BLOB_BASE = 0x01FE0000
BLOB_LIMIT = 0x01FF0000
CODE_BASE = BLOB_BASE + 0x40

HDR_STATE = 0x00
HDR_CHOSEN_PREFIX = 0x04
HDR_ENTRY_COUNT = 0x08
HDR_TABLE_PTR = 0x0C
HDR_NAMES_PTR = 0x10
HDR_PREFIX_COUNT = 0x14
HDR_PREFIX_PTRS = 0x18
HDR_PROBE_NAME = 0x38
MAX_PREFIXES = 8

DEFAULT_PREFIXES = [
    "host:unpacked_linkdata/",
    "host:./unpacked_linkdata/",
    "host:C:/projs/Burn_Engine/game_stuff/unpacked_linkdata/",
    "host:C:\\projs\\Burn_Engine\\game_stuff\\unpacked_linkdata\\",
]


def parse_toc(toc_path: Path, unpack_dir: Path):
    """Return sorted list"""
    entries = {}
    problems = []
    with open(toc_path, "r", encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        col = {name: idx for idx, name in enumerate(header)}
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(header):
                continue
            name = parts[col["name"]]
            start = int(parts[col["offset_units"]], 16)
            byte_size = int(parts[col["linkdata_size"]], 16)
            sectors = (byte_size + SECTOR_SIZE - 1) // SECTOR_SIZE
            rel = name.replace("$(", "").replace(")", "").replace("\\", "/")
            disk_path = unpack_dir / rel
            if not disk_path.is_file():
                problems.append("missing on disk: %s (%s)" % (rel, name))
                continue
            actual = disk_path.stat().st_size
            if actual != byte_size:
                problems.append("size mismatch %s: toc 0x%X disk 0x%X"
                                % (rel, byte_size, actual))
            key = start
            if key in entries:
                prev = entries[key]
                if prev[0] != start + sectors:
                    problems.append("conflicting range at sector 0x%X: %s vs %s"
                                    % (start, prev[1], rel))
                continue
            entries[key] = (start + sectors, rel)
    table = sorted((start, end, rel) for start, (end, rel) in entries.items())
    prev_end = 0
    for start, end, rel in table:
        if start < prev_end:
            problems.append("overlap at sector 0x%X (%s)" % (start, rel))
        prev_end = end
    return table, problems


def build_data(table, prefixes):
    """Build the table/name/prefix data that follows the code"""
    names = bytearray()
    packed = bytearray()
    name_offsets = {}
    for start, end, rel in table:
        if rel not in name_offsets:
            name_offsets[rel] = len(names)
            names += rel.encode("ascii") + b"\0"
        packed += struct.pack("<3I", start, end, name_offsets[rel])
    prefix_blob = bytearray()
    prefix_offsets = []
    for prefix in prefixes:
        prefix_offsets.append(len(prefix_blob))
        prefix_blob += prefix.encode("ascii") + b"\0"
    probe_name_off = name_offsets[table[0][2]]
    return bytes(packed), bytes(names), bytes(prefix_blob), prefix_offsets, probe_name_off

LABEL_MARKERS = {
    "core": 0xB001,
    "new_sec_read": 0xB002,
    "new_sec_read_buf": 0xB003,
    "new_list_run": 0xB004,
    "select_loader": 0xB005,
}


def hook_assembly():
    """Replacement code, written sequentially"""
    hi = lambda addr: (addr >> 16) & 0xFFFF
    lo = lambda addr: addr & 0xFFFF
    return f"""
append:
    lbu     $v1, 0($a1)
    sb      $v1, 0($a0)
    beqz    $v1, append_done
    addiu   $a0, $a0, 1
    addiu   $a1, $a1, 1
    b       append
append_done:
    move    $v0, $a0
    jr      $ra

cd_fallback:
    addiu   $sp, $sp, -0x40
    sw      $ra, 0x38($sp)
    sw      $s0, 0x28($sp)
    sw      $s1, 0x2C($sp)
    sw      $s2, 0x30($sp)
    move    $s0, $a0
    move    $s1, $a1
    move    $s2, $a2
    addiu   $v0, $zero, 0xA
    sb      $v0, 0x10($sp)
    addiu   $v0, $zero, 1
    sb      $v0, 0x11($sp)
    sb      $zero, 0x12($sp)
cdf_retry:
    addiu   $a0, $zero, 1
    jal     {FN_CD_DISKREADY:#x}
    addiu   $v1, $zero, 2
    bne     $v0, $v1, cdf_retry
    lui     $v1, {hi(GDATA_SECTOR):#x}
    ori     $v1, $v1, {lo(GDATA_SECTOR):#x}
    lw      $v1, 0($v1)
    addu    $a0, $v1, $s0
    move    $a1, $s1
    move    $a2, $s2
    addiu   $a3, $sp, 0x10
    jal     {FN_CD_READ:#x}
    beqz    $v0, cdf_retry
    move    $a0, $zero
    jal     {FN_CD_SYNC:#x}
    jal     {FN_CD_GETERROR:#x}
    bnez    $v0, cdf_retry
    lw      $ra, 0x38($sp)
    lw      $s0, 0x28($sp)
    lw      $s1, 0x2C($sp)
    lw      $s2, 0x30($sp)
    addiu   $sp, $sp, 0x40
    jr      $ra

probe:
    addiu   $sp, $sp, -0x140
    sw      $ra, 0x138($sp)
    sw      $s0, 0x128($sp)
    sw      $s1, 0x12C($sp)
    sw      $s2, 0x130($sp)
    lui     $s0, {hi(BLOB_BASE):#x}
    ori     $s0, $s0, {lo(BLOB_BASE):#x}
    lw      $s1, {HDR_PREFIX_COUNT}($s0)
    move    $s2, $zero
probe_loop:
    beq     $s2, $s1, probe_fail
    sll     $v0, $s2, 2
    addiu   $v1, $s0, {HDR_PREFIX_PTRS}
    addu    $v0, $v0, $v1
    lw      $a1, 0($v0)
    addiu   $a0, $sp, 0x20
    jal     append
    move    $a0, $v0
    lw      $a1, {HDR_PROBE_NAME}($s0)
    lw      $v1, {HDR_NAMES_PTR}($s0)
    addu    $a1, $a1, $v1
    jal     append
    addiu   $a0, $sp, 0x20
    addiu   $a1, $zero, 1
    jal     {FN_SCE_OPEN:#x}
    bltz    $v0, probe_next
    move    $a0, $v0
    jal     {FN_SCE_CLOSE:#x}
    sll     $v0, $s2, 2
    addiu   $v1, $s0, {HDR_PREFIX_PTRS}
    addu    $v0, $v0, $v1
    lw      $v0, 0($v0)
    sw      $v0, {HDR_CHOSEN_PREFIX}($s0)
    addiu   $v0, $zero, 1
    sw      $v0, {HDR_STATE}($s0)
    b       probe_done
probe_next:
    addiu   $s2, $s2, 1
    b       probe_loop
probe_fail:
    addiu   $v0, $zero, -1
    sw      $v0, {HDR_STATE}($s0)
probe_done:
    lw      $ra, 0x138($sp)
    lw      $s0, 0x128($sp)
    lw      $s1, 0x12C($sp)
    lw      $s2, 0x130($sp)
    addiu   $sp, $sp, 0x140
    jr      $ra

core:
    ori     $zero, $zero, {LABEL_MARKERS['core']:#x}
    addiu   $sp, $sp, -0x180
    sw      $ra, 0x170($sp)
    sw      $s0, 0x150($sp)
    sw      $s1, 0x154($sp)
    sw      $s2, 0x158($sp)
    sw      $s3, 0x15C($sp)
    sw      $s4, 0x160($sp)
    sw      $s5, 0x164($sp)
    move    $s0, $a0
    move    $s1, $a1
    move    $s2, $a2
    beqz    $s1, epilogue
    lui     $s5, {hi(BLOB_BASE):#x}
    ori     $s5, $s5, {lo(BLOB_BASE):#x}
    lw      $v0, {HDR_STATE}($s5)
    bnez    $v0, state_done
    jal     probe
state_done:
    lw      $v0, {HDR_STATE}($s5)
    addiu   $v1, $zero, 1
    beq     $v0, $v1, loop
    move    $a0, $s0
    move    $a1, $s1
    move    $a2, $s2
    jal     cd_fallback
    b       epilogue

loop:
    beqz    $s1, epilogue
    lw      $t0, {HDR_TABLE_PTR}($s5)
    lw      $t1, {HDR_ENTRY_COUNT}($s5)
    move    $t2, $zero
search:
    beq     $t2, $t1, notfound
    lw      $t3, 0($t0)
    lw      $t5, 4($t0)
    sltu    $t6, $s0, $t3
    bnez    $t6, notfound
    sltu    $t6, $s0, $t5
    bnez    $t6, found
    addiu   $t2, $t2, 1
    addiu   $t0, $t0, 12
    b       search
found:
    move    $s4, $t0
    subu    $t6, $t5, $s0
    sltu    $t7, $t6, $s1
    beqz    $t7, take_count
    move    $s3, $t6
    b       have_n
take_count:
    move    $s3, $s1
have_n:
    addiu   $a0, $sp, 0x40
    lw      $a1, {HDR_CHOSEN_PREFIX}($s5)
    jal     append
    move    $a0, $v0
    lw      $a1, 8($s4)
    lw      $v1, {HDR_NAMES_PTR}($s5)
    addu    $a1, $a1, $v1
    jal     append
    addiu   $a0, $sp, 0x40
    addiu   $a1, $zero, 1
    jal     {FN_SCE_OPEN:#x}
    bltz    $v0, chunk_fallback
    sw      $v0, 0x30($sp)
    move    $a0, $v0
    lw      $v1, 0($s4)
    subu    $a1, $s0, $v1
    sll     $a1, $a1, 0xb
    move    $a2, $zero
    jal     {FN_SCE_LSEEK:#x}
    lw      $a0, 0x30($sp)
    move    $a1, $s2
    sll     $a2, $s3, 0xb
    jal     {FN_SCE_READ:#x}
    sw      $v0, 0x34($sp)
    lw      $a0, 0x30($sp)
    jal     {FN_SCE_CLOSE:#x}
    lw      $v0, 0x34($sp)
    bgez    $v0, zero_fill
    move    $v0, $zero
zero_fill:
    sll     $v1, $s3, 0xb
    sltu    $t6, $v0, $v1
    beqz    $t6, advance
    addu    $t0, $s2, $v0
    addu    $t1, $s2, $v1
zfill_loop:
    beq     $t0, $t1, advance
    sb      $zero, 0($t0)
    addiu   $t0, $t0, 1
    b       zfill_loop
chunk_fallback:
    move    $a0, $s0
    move    $a1, $s3
    move    $a2, $s2
    jal     cd_fallback
advance:
    addu    $s0, $s0, $s3
    subu    $s1, $s1, $s3
    sll     $v0, $s3, 0xb
    addu    $s2, $s2, $v0
    b       loop

notfound:
    move    $a0, $s0
    move    $a1, $s1
    move    $a2, $s2
    jal     cd_fallback
epilogue:
    move    $a0, $zero
    jal     {FN_FLUSHCACHE:#x}
    lw      $ra, 0x170($sp)
    lw      $s0, 0x150($sp)
    lw      $s1, 0x154($sp)
    lw      $s2, 0x158($sp)
    lw      $s3, 0x15C($sp)
    lw      $s4, 0x160($sp)
    lw      $s5, 0x164($sp)
    addiu   $sp, $sp, 0x180
    jr      $ra
new_sec_read:
    ori     $zero, $zero, {LABEL_MARKERS['new_sec_read']:#x}
    lui     $v0, {hi(GDATA_SECTOR):#x}
    ori     $v0, $v0, {lo(GDATA_SECTOR):#x}
    lw      $v0, 0($v0)
    bnez    $v0, nsr_go
    move    $v0, $zero
    jr      $ra
nsr_go:
    addiu   $sp, $sp, -0x20
    sw      $ra, 0x18($sp)
    sw      $s0, 0x08($sp)
    sw      $s1, 0x0C($sp)
    sw      $s2, 0x10($sp)
    move    $s0, $a0
    move    $s1, $a1
    addiu   $a0, $zero, 0x40
    sll     $a1, $s1, 0xb
    jal     {FN_PMEMALIGN:#x}
    beqz    $v0, nsr_out
    move    $s2, $v0
    move    $a0, $s0
    move    $a1, $s1
    move    $a2, $s2
    jal     core
    move    $v0, $s2
nsr_out:
    lw      $ra, 0x18($sp)
    lw      $s0, 0x08($sp)
    lw      $s1, 0x0C($sp)
    lw      $s2, 0x10($sp)
    addiu   $sp, $sp, 0x20
    jr      $ra

new_sec_read_buf:
    ori     $zero, $zero, {LABEL_MARKERS['new_sec_read_buf']:#x}
    lui     $v0, {hi(GDATA_SECTOR):#x}
    ori     $v0, $v0, {lo(GDATA_SECTOR):#x}
    lw      $v0, 0($v0)
    beqz    $v0, nsrb_skip
    j       core
nsrb_skip:
    jr      $ra
new_list_run:
    ori     $zero, $zero, {LABEL_MARKERS['new_list_run']:#x}
    addiu   $sp, $sp, -0x30
    sw      $ra, 0x28($sp)
    sw      $s0, 0x10($sp)
    sw      $s1, 0x14($sp)
    sw      $s2, 0x18($sp)
    lui     $v1, {hi(SEC_READ_LIST_NOW):#x}
    ori     $v1, $v1, {lo(SEC_READ_LIST_NOW):#x}
    lw      $s0, 0($v1)
    lui     $v1, {hi(SEC_READ_LIST_CNT):#x}
    ori     $v1, $v1, {lo(SEC_READ_LIST_CNT):#x}
    lw      $s1, 0($v1)
nlr_loop:
    slt     $v0, $s0, $s1
    beqz    $v0, nlr_done
    sll     $v0, $s0, 4
    lui     $v1, {hi(SEC_READ_LIST):#x}
    ori     $v1, $v1, {lo(SEC_READ_LIST):#x}
    addu    $s2, $v0, $v1
    lw      $v0, 8($s2)
    lw      $a2, 0($v0)
    lw      $a0, 0($s2)
    lui     $v1, {hi(GDATA_SECTOR):#x}
    ori     $v1, $v1, {lo(GDATA_SECTOR):#x}
    lw      $v1, 0($v1)
    subu    $a0, $a0, $v1
    lw      $a1, 4($s2)
    jal     core
    addiu   $v0, $zero, 4
    sw      $v0, 0xC($s2)
    addiu   $s0, $s0, 1
    b       nlr_loop
nlr_done:
    lui     $v1, {hi(SEC_READ_LIST_NOW):#x}
    ori     $v1, $v1, {lo(SEC_READ_LIST_NOW):#x}
    sw      $zero, 0($v1)
    lui     $v1, {hi(SEC_READ_LIST_CNT):#x}
    ori     $v1, $v1, {lo(SEC_READ_LIST_CNT):#x}
    sw      $zero, 0($v1)
    addiu   $v0, $zero, 1
    lw      $ra, 0x28($sp)
    lw      $s0, 0x10($sp)
    lw      $s1, 0x14($sp)
    lw      $s2, 0x18($sp)
    addiu   $sp, $sp, 0x30
    jr      $ra
"""


def assemble(asm_text, base):
    ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 | KS_MODE_LITTLE_ENDIAN)
    encoding, count = ks.asm(".option pic0\n" + asm_text, base)
    code = bytes(encoding)
    reject_pic_calls(code, base)
    return code, count


def reject_pic_calls(code, base):
    """Refuse code that contains a PIC indirect call"""
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
    saw_gp_load_to_t9 = False
    for insn in md.disasm(code, base):
        if insn.mnemonic == "lw" and "$t9," in insn.op_str and "($gp)" in insn.op_str:
            saw_gp_load_to_t9 = True
        elif insn.mnemonic == "jalr" and "$t9" in insn.op_str and saw_gp_load_to_t9:
            raise BuildError(
                "assembler produced a position independent (PIC) call "
                "(lw $t9,($gp); jalr $t9) at 0x%X , this keystone defaults to "
                "PIC and the injected blob has no GOT, so the ELF would crash "
                "on boot. Nothing was written. Try a different keystone-engine "
                "build; '.option pic0' should already prevent this." % insn.address
            )
        elif insn.mnemonic not in ("nop", "addiu"):
            saw_gp_load_to_t9 = False


def find_label_addresses(code, base):
    """Locate the marker no-ops planted after each label the entry stubs target"""
    labels = {}
    for label, imm in LABEL_MARKERS.items():
        pattern = struct.pack("<I", 0x34000000 | imm)
        off = code.find(pattern)
        if off < 0 or off % 4:
            raise SystemExit("marker for %s not found in assembled code" % label)
        if code.find(pattern, off + 4) >= 0:
            raise SystemExit("marker for %s is not unique" % label)
        labels[label] = base + off
    return labels


def encode_j(target):
    return struct.pack("<I", 0x08000000 | ((target >> 2) & 0x03FFFFFF))


def encode_lui(reg, imm):
    return struct.pack("<I", (0x0F << 26) | (reg << 16) | (imm & 0xFFFF))


def encode_addiu(rt, rs, imm):
    return struct.pack("<I", (0x09 << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF))


NOP = b"\x00\x00\x00\x00"

ADDR_READ_SELECT_MODELS = 0x230170
SIZE_READ_SELECT_MODELS = 0x128
FN_SET_SECTOR_READ_LIST = 0x20DD08
SYM_GMODEL_TABLE = 0x3590C0
SYM_GMODEL_DATA = 0x358A50
SYM_MODEL_FILE_SEC = 0x3579D0
SYM_FACE_MOT_SEC = 0x3788C0
SYM_GMOTION_TABLE = 0x359160
SYM_GMOTION_DATA = 0x358F30
OFFICER_COUNT = 28
SELECT_MOTION_SECTOR = 0x38BA
SELECT_MOTION_COUNT = 0x164
SELECT_MOTION_SPLIT = 0xB1800

SD_OP, LD_OP = 0x3F, 0x37
REG_SP, REG_RA = 29, 31


def hi16(addr):
    return ((addr + 0x8000) >> 16) & 0xFFFF


def lo16(addr):
    value = addr & 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def itype(op, base, rt, off):
    return (op << 26) | (base << 21) | (rt << 16) | (off & 0xFFFF)


def select_loader_assembly():
    def sd(rt, off):
        return ".word 0x%08x" % itype(SD_OP, REG_SP, rt, off)

    def ld(rt, off):
        return ".word 0x%08x" % itype(LD_OP, REG_SP, rt, off)

    return """
select_loader:
    ori   $zero, $zero, {marker:#x}
    addiu $sp, $sp, -0x30
    {sd_ra}
    {sd_s0}
    {sd_s1}
    {sd_s2}

    lui   $a0, 0x{mt_hi:x}
    addiu $a0, $a0, {mt_lo}
    move  $v1, $zero
mt_loop:
    sw    $v1, 0($a0)
    addiu $v1, $v1, 1
    addiu $a0, $a0, 4
    slti  $v0, $v1, {count}
    bnez  $v0, mt_loop
    addiu $v0, $zero, -1
    sw    $v0, 0($a0)

    lui   $s0, 0x{md_hi:x}
    addiu $s0, $s0, {md_lo}
    lui   $s1, 0x{ms_hi:x}
    addiu $s1, $s1, {ms_lo}
    lui   $s2, 0x{fs_hi:x}
    addiu $s2, $s2, {fs_lo}

    move  $v0, $zero
    move  $v1, $zero
    move  $t1, $s1
    move  $t0, $s2
sum_loop:
    lw    $t2, 4($t1)
    lw    $t3, 4($t0)
    addu  $v0, $v0, $t2
    addiu $t1, $t1, 0x10
    addu  $v0, $v0, $t3
    addiu $t0, $t0, 0x10
    addiu $v1, $v1, 1
    slti  $t2, $v1, {count}
    bnez  $t2, sum_loop

    lw    $a0, 0($s1)
    move  $a1, $v0
    addiu $a2, $s0, 8
    jal   0x{setlist:x}

    lw    $a0, 8($s0)
    lw    $v0, 4($s1)
    sll   $v0, $v0, 0xb
    addu  $a0, $a0, $v0
    sw    $a0, 0x14($s0)

    addiu $t1, $s1, 0x14
    addiu $t0, $s2, 0x14
    lw    $v0, 4($s1)
    lw    $a1, 4($s2)
    addu  $a0, $v0, $a1
    addiu $s0, $s0, 0x20
    addiu $a3, $zero, {chain}
chain_loop:
    lw    $a2, 0($t1)
    sll   $a0, $a0, 0xb
    lw    $v0, -0x18($s0)
    addiu $t1, $t1, 0x10
    sll   $v1, $a2, 0xb
    lw    $a1, 0($t0)
    addu  $v0, $v0, $a0
    addiu $t0, $t0, 0x10
    addu  $v1, $v0, $v1
    sw    $v0, 8($s0)
    sw    $v1, 0x14($s0)
    addu  $a0, $a2, $a1
    addiu $a3, $a3, -1

    addiu $s0, $s0, 0x20
    bgez  $a3, chain_loop

    lui   $a0, 0x{gt_hi:x}
    addiu $a0, $a0, {gt_lo}
    sw    $zero, 0($a0)
    addiu $v0, $zero, -1
    sw    $v0, 4($a0)
    lui   $s0, 0x{gd_hi:x}
    addiu $s0, $s0, {gd_lo}
    addiu $a2, $s0, 4
    addiu $a0, $zero, 0x{msec:x}
    addiu $a1, $zero, 0x{mcnt:x}
    jal   0x{setlist:x}
    lw    $v1, 4($s0)
    lui   $v0, 0x{split_hi:x}
    ori   $v0, $v0, 0x{split_lo:x}
    sw    $zero, 0xc($s0)
    addu  $v1, $v1, $v0
    sw    $v1, 8($s0)

    {ld_ra}
    {ld_s0}
    {ld_s1}
    {ld_s2}
    addiu $sp, $sp, 0x30
    jr    $ra
""".format(
        sd_ra=sd(REG_RA, 0x20), sd_s0=sd(16, 0x00), sd_s1=sd(17, 0x08),
        sd_s2=sd(18, 0x10),
        ld_ra=ld(REG_RA, 0x20), ld_s0=ld(16, 0x00), ld_s1=ld(17, 0x08),
        ld_s2=ld(18, 0x10),
        mt_hi=hi16(SYM_GMODEL_TABLE), mt_lo=lo16(SYM_GMODEL_TABLE),
        md_hi=hi16(SYM_GMODEL_DATA), md_lo=lo16(SYM_GMODEL_DATA),
        ms_hi=hi16(SYM_MODEL_FILE_SEC), ms_lo=lo16(SYM_MODEL_FILE_SEC),
        fs_hi=hi16(SYM_FACE_MOT_SEC), fs_lo=lo16(SYM_FACE_MOT_SEC),
        gt_hi=hi16(SYM_GMOTION_TABLE), gt_lo=lo16(SYM_GMOTION_TABLE),
        gd_hi=hi16(SYM_GMOTION_DATA), gd_lo=lo16(SYM_GMOTION_DATA),
        marker=LABEL_MARKERS['select_loader'],
        count=OFFICER_COUNT, chain=OFFICER_COUNT - 2,
        setlist=FN_SET_SECTOR_READ_LIST,
        msec=SELECT_MOTION_SECTOR, mcnt=SELECT_MOTION_COUNT,
        split_hi=SELECT_MOTION_SPLIT >> 16, split_lo=SELECT_MOTION_SPLIT & 0xFFFF,
    )


def vaddr_to_off(vaddr):
    return vaddr - ELF_VADDR_BASE + ELF_FILE_BASE

IOP_SOUND_SYMBOLS = frozenset({
    "msCommonHdFile", "msEnvHdFile", "msPlHdFile", "msFaHdFile",
    "msMenuHdFile", "msBriefingHdFile",
    "msCommonBdFile", "msEnvBdFile", "msPlBdFile", "msFaBdFile",
    "msMenuBdFile", "msBriefingBdFile",
})

ARENA_MIN_BASE = 0x20000


class BuildError(Exception):
    pass


def toc_relpath(name):
    return name.replace("$(", "").replace(")", "").replace("\\", "/")


def load_toc_rows(toc_path):
    """Parse toc_entries.txt into per-record dicts, preserving everything the writeback needs"""
    def hexval(text):
        text = text.strip()
        if not text or text == "-":
            return None
        return int(text, 16)

    rows = []
    with open(toc_path, "r", encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        col = {name: idx for idx, name in enumerate(header)}
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(header):
                continue
            toc_bytes = parts[col["toc_bytes"]].strip()
            rows.append({
                "name": parts[col["name"]],
                "rel": toc_relpath(parts[col["name"]]),
                "symbol": parts[col["symbol"]],
                "toc_file_offset": hexval(parts[col["toc_file_offset"]]),
                "record_len": len(toc_bytes) // 2 if toc_bytes not in ("", "-") else 0,
                "orig_offset": hexval(parts[col["offset_units"]]),
                "orig_count": hexval(parts[col["size_units"]]),
                "linkdata_size": hexval(parts[col["linkdata_size"]]),
            })
    return rows

CONTIGUITY_SETS = (
    frozenset({"model_file_sec", "face_mot_sec"}),
    frozenset({"motion_file_sec", "mov_file_sec", "atk_file_sec"}),
)


def contiguity_set(symbols):
    for cset in CONTIGUITY_SETS:
        if symbols & cset:
            return cset
    return None


def build_runs(groups):
    """Chain offset groups that a loader reads as one contiguous request"""
    ordered = sorted(groups.items())
    runs = []
    consumed = set()
    for offset, group in ordered:
        if offset in consumed:
            continue
        cset = contiguity_set({r["symbol"] for r in group})
        run = [(offset, group)]
        consumed.add(offset)
        if cset:
            cursor = offset + group[0]["orig_count"]
            while cursor in groups and cursor not in consumed:
                nxt = groups[cursor]
                if not ({r["symbol"] for r in nxt} & cset):
                    break
                run.append((cursor, nxt))
                consumed.add(cursor)
                cursor += nxt[0]["orig_count"]
        runs.append(run)
    return runs


def row_category(row):
    if row["symbol"] in IOP_SOUND_SYMBOLS:
        return "sound"
    if row["record_len"] in (8, 16):
        return "table"
    return "direct"


def plan_build(rows, unpack_dir):
    """Decide the served sector layout from the current on disk file sizes"""
    unpack_dir = Path(unpack_dir)
    groups = {}
    for row in rows:
        groups.setdefault(row["orig_offset"], []).append(row)

    non_sound_end = [r["orig_offset"] + r["orig_count"]
                     for r in rows if row_category(r) != "sound"]
    max_end = max(non_sound_end) if non_sound_end else 0
    arena_base = max(ARENA_MIN_BASE, (max_end + 0xFFF) & ~0xFFF)
    arena_cursor = arena_base

    redirect = []
    writebacks = []
    report = {key: [] for key in
              ("unchanged", "shrunk", "relocated", "direct_grown",
               "sound_changed", "missing", "overlaps")}

    def inspect(group):
        if "sound" in {row_category(r) for r in group}:
            present = next((r for r in group if (unpack_dir / r["rel"]).is_file()), None)
            return "sound", present, 0
        present = next((r for r in group if (unpack_dir / r["rel"]).is_file()), None)
        if present is None:
            return "missing", None, 0
        size = (unpack_dir / present["rel"]).stat().st_size
        return "file", present, (size + SECTOR_SIZE - 1) // SECTOR_SIZE

    for run in build_runs(groups):
        members = [(off, grp) + inspect(grp) for off, grp in run]

        for _, grp, kind, present, _ in members:
            if kind == "sound":
                if present is not None:
                    size = (unpack_dir / present["rel"]).stat().st_size
                    if size != present["linkdata_size"]:
                        report["sound_changed"].append(present["rel"])
            elif kind == "missing":
                report["missing"].append(grp[0]["rel"])

        live = [m for m in members if m[2] == "file"]
        if not live:
            continue

        grew = any(nc > pr["orig_count"] for _, _, _, pr, nc in live)
        movable = (len(live) == len(run)
                   and all(all(row_category(r) == "table" for r in grp)
                           for _, grp, _, _, _ in live))

        if grew and movable:
            for _, grp, _, present, new_count in live:
                new_offset = arena_cursor
                arena_cursor += new_count
                for r in grp:
                    writebacks.append((r["toc_file_offset"], r["orig_offset"],
                                       r["orig_count"], new_offset, new_count))
                redirect.append((new_offset, new_offset + new_count, present["rel"]))
                report["relocated"].append(
                    (present["rel"], present["orig_count"], new_count))
            arena_cursor = (arena_cursor + 0xF) & ~0xF
        else:
            for orig_offset, _, _, present, new_count in live:
                orig_count = present["orig_count"]
                redirect.append((orig_offset, orig_offset + orig_count, present["rel"]))
                if new_count > orig_count:
                    report["direct_grown"].append(present["rel"])
                elif new_count < orig_count:
                    report["shrunk"].append(present["rel"])
                else:
                    report["unchanged"].append(present["rel"])

    redirect.sort()
    prev_end = -1
    for start, end, rel in redirect:
        if start < prev_end:
            report["overlaps"].append(rel)
        prev_end = end
    return redirect, writebacks, report, arena_base


def build_hostfs_elf(elf_path, toc_path, unpack_dir, out_path,
                     prefixes=None, progress=None):
    """Rebuild the hostfs ELF from the pristine original"""
    prefixes = list(prefixes) if prefixes else list(DEFAULT_PREFIXES)
    if len(prefixes) > MAX_PREFIXES:
        raise BuildError("at most %d host prefixes" % MAX_PREFIXES)

    def emit(message, frac=None):
        if progress:
            progress(message, frac)

    emit("Reading TOC records", 0.05)
    rows = load_toc_rows(Path(toc_path))
    if not rows:
        raise BuildError("no rows parsed from %s" % toc_path)

    emit("Scanning unpacked files and planning sector layout", 0.15)
    redirect, writebacks, report, arena_base = plan_build(rows, Path(unpack_dir))
    if not redirect:
        raise BuildError("no serveable files found under %s" % unpack_dir)
    if report["overlaps"]:
        raise BuildError("sector ranges overlap after planning: %s"
                         % ", ".join(report["overlaps"][:5]))

    emit("Assembling hook code", 0.40)
    table_bytes, names_bytes, prefix_blob, prefix_offsets, probe_name_off = \
        build_data(redirect, prefixes)
    asm_text = hook_assembly() + select_loader_assembly()
    code, _ = assemble(asm_text, CODE_BASE)

    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
    if sum(i.size for i in md.disasm(code, CODE_BASE)) != len(code):
        raise BuildError("assembled hook code failed capstone")
    labels = find_label_addresses(code, CODE_BASE)

    emit("Laying out injected blob", 0.60)
    code_end = CODE_BASE + len(code)
    table_addr = (code_end + 0xF) & ~0xF
    names_addr = table_addr + len(table_bytes)
    prefix_addr = (names_addr + len(names_bytes) + 3) & ~3

    header = bytearray(0x40)
    struct.pack_into("<i", header, HDR_STATE, 0)
    struct.pack_into("<I", header, HDR_CHOSEN_PREFIX, 0)
    struct.pack_into("<I", header, HDR_ENTRY_COUNT, len(redirect))
    struct.pack_into("<I", header, HDR_TABLE_PTR, table_addr)
    struct.pack_into("<I", header, HDR_NAMES_PTR, names_addr)
    struct.pack_into("<I", header, HDR_PREFIX_COUNT, len(prefixes))
    for i, off in enumerate(prefix_offsets):
        struct.pack_into("<I", header, HDR_PREFIX_PTRS + i * 4, prefix_addr + off)
    struct.pack_into("<I", header, HDR_PROBE_NAME, probe_name_off)

    blob = bytearray(header)
    blob += code
    blob += b"\0" * (table_addr - code_end)
    blob += table_bytes
    blob += names_bytes
    blob += b"\0" * (prefix_addr - names_addr - len(names_bytes))
    blob += prefix_blob
    if BLOB_BASE + len(blob) > BLOB_LIMIT:
        raise BuildError("blob 0x%X exceeds reserved region 0x%X"
                         % (len(blob), BLOB_LIMIT - BLOB_BASE))

    emit("Patching ELF and applying TOC writebacks", 0.80)
    data = bytearray(Path(elf_path).read_bytes())
    e_phoff, = struct.unpack_from("<I", data, 0x1C)
    e_phentsize, e_phnum = struct.unpack_from("<2H", data, 0x2A)
    if e_phnum != 1:
        raise BuildError("expected 1 program header in the original ELF, found %d "
                         "(point this at the untouched SLUS_200.79)" % e_phnum)
    new_ph_off = e_phoff + e_phentsize
    if any(data[new_ph_off:new_ph_off + e_phentsize]):
        raise BuildError("no room for a second program header")

    blob_file_off = (len(data) + 0xF) & ~0xF
    data += b"\0" * (blob_file_off - len(data))
    data += blob
    struct.pack_into("<8I", data, new_ph_off,
                     1, blob_file_off, BLOB_BASE, BLOB_BASE,
                     len(blob), len(blob), 7, 0x10)
    struct.pack_into("<H", data, 0x2C, 2)

    def write_stub(vaddr, target):
        off = vaddr_to_off(vaddr)
        data[off:off + 4] = encode_j(target)
        data[off + 4:off + 8] = NOP

    write_stub(PATCH_SEC_READ, labels["new_sec_read"])
    write_stub(PATCH_SEC_READ_BUF, labels["new_sec_read_buf"])
    write_stub(PATCH_START_LIST, labels["new_list_run"])
    write_stub(PATCH_BLOCK_LIST, labels["new_list_run"])

    write_stub(ADDR_READ_SELECT_MODELS, labels["select_loader"])
    report["select_loader_addr"] = labels["select_loader"]

    heap_size = BLOB_BASE - HEAP_END_SYMBOL
    if heap_size & 0x8000:
        raise BuildError("heap size low half would sign extend,  pick another BLOB_BASE")
    data[vaddr_to_off(CRT0_HEAP_LUI):vaddr_to_off(CRT0_HEAP_LUI) + 4] = \
        encode_lui(5, heap_size >> 16)
    data[vaddr_to_off(CRT0_HEAP_ADDIU):vaddr_to_off(CRT0_HEAP_ADDIU) + 4] = \
        encode_addiu(5, 5, heap_size & 0xFFFF)

    for file_off, orig_off, orig_count, new_off, new_count in writebacks:
        cur_off, cur_count = struct.unpack_from("<2I", data, file_off)
        if (cur_off, cur_count) != (orig_off, orig_count):
            raise BuildError("TOC record at file 0x%X holds (0x%X,0x%X), expected "
                             "(0x%X,0x%X) , stale toc_entries.txt or wrong ELF"
                             % (file_off, cur_off, cur_count, orig_off, orig_count))
        struct.pack_into("<2I", data, file_off, new_off, new_count)

    lwm_off = vaddr_to_off(0x2106F0)
    lwm_orig = bytes.fromhex("15006214") + bytes(4)
    lwm_patch = struct.pack("<I", 0x10000074) + struct.pack("<I", 0x86220022)
    cur_lwm = bytes(data[lwm_off:lwm_off + 8])
    if cur_lwm == lwm_orig:
        data[lwm_off:lwm_off + 8] = lwm_patch
    elif cur_lwm != lwm_patch:
        raise BuildError("calc_lwm site at file 0x%X holds %s, expected stock %s "
                         ", wrong ELF or already modified differently"
                         % (lwm_off, cur_lwm.hex(), lwm_orig.hex()))

    Path(out_path).write_bytes(data)
    emit("Done", 1.0)
    report["out"] = str(out_path)
    report["blob_size"] = len(blob)
    report["arena_base"] = arena_base
    report["served"] = len(redirect)
    report["relocated_count"] = len(report["relocated"])
    return report


UNPACK_DIR_NAME = "unpacked_linkdata"
TOC_NAME = "toc_entries.txt"
HOSTFS_SUFFIX = ".hostfs.elf"


def paths_for_elf(elf_path):
    """Derive every other path this patch needs from the ELF the user picked"""
    elf_path = Path(elf_path)
    folder = elf_path.parent
    unpack_dir = folder / UNPACK_DIR_NAME
    return unpack_dir / TOC_NAME, unpack_dir, folder / (elf_path.name + HOSTFS_SUFFIX)


def launch(parent=None, status=None):
    """Burn Engine hub entry point"""
    from tkinter import filedialog, messagebox

    def say(message):
        if status:
            status(message)

    picked = filedialog.askopenfilename(
        parent=parent,
        title="Pick the original SLUS_200.79 to patch for host-FS loading",
        initialdir=str(GAME_DIR),
        filetypes=[("DW2 ELF", "SLUS_200.79"), ("ELF", "*.elf"), ("All files", "*.*")],
    )
    if not picked:
        say("HostFS patch cancelled.")
        return None

    elf_path = Path(picked)
    toc_path, unpack_dir, out_path = paths_for_elf(elf_path)
    if not toc_path.is_file():
        messagebox.showerror(
            "HostFS Patcher",
            f"No {TOC_NAME} under {unpack_dir}.\n\n"
            "Run the LINKDATA Unpacker on this folder first, the patch needs "
            "the unpacked tree and its TOC.",
            parent=parent,
        )
        say(f"HostFS patch aborted: {TOC_NAME} not found.")
        return None
    if elf_path.name.upper().endswith(HOSTFS_SUFFIX.upper()):
        messagebox.showerror(
            "Host-FS Patcher",
            "That is already a patched hostFS ELF.\n\n"
            "Pick the pristine SLUS_200.79, the build always starts from the "
            "original.",
            parent=parent,
        )
        say("HostFS patch aborted: pick the pristine ELF, not a patched one.")
        return None

    say(f"Patching {elf_path.name} for hostFS loading")
    try:
        report = build_hostfs_elf(elf_path, toc_path, unpack_dir, out_path,
                                  progress=lambda m, f=None: say(m))
    except Exception as exc:
        messagebox.showerror("Host-FS Patcher", f"Patch failed:\n\n{exc}", parent=parent)
        say(f"Host-FS patch failed: {exc}")
        return None

    unsupported = len(report["direct_grown"]) + len(report["sound_changed"])
    say(f"HostFS ELF written: {out_path.name} ({report['served']} files served)")
    messagebox.showinfo(
        "HostFS Patcher",
        f"Wrote {out_path}\n\n"
        f"served:      {report['served']}\n"
        f"relocated:   {report['relocated_count']}\n"
        f"shrunk:      {len(report['shrunk'])}\n"
        f"unchanged:   {len(report['unchanged'])}\n"
        f"unsupported: {unsupported}\n"
        f"missing:     {len(report['missing'])}",
        parent=parent,
    )
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Patch SLUS_200.79 for PCSX2 host file loading of unpacked LINKDATA.")
    parser.add_argument("--elf", default=str(GAME_DIR / "SLUS_200.79"))
    parser.add_argument("--toc", default=str(GAME_DIR / UNPACK_DIR_NAME / TOC_NAME))
    parser.add_argument("--unpack-dir", default=str(GAME_DIR / UNPACK_DIR_NAME))
    parser.add_argument("--out", default=str(GAME_DIR / ("SLUS_200.79" + HOSTFS_SUFFIX)))
    parser.add_argument("--prefix", action="append", default=None,
                        help="host path prefix candidate (repeatable), default probes relative and absolute forms")
    args = parser.parse_args()

    def show(message, frac=None):
        print(("[%3d%%] " % round(frac * 100)) if frac is not None else "       ", end="")
        print(message)

    report = build_hostfs_elf(args.elf, args.toc, args.unpack_dir, args.out,
                              prefixes=args.prefix, progress=show)

    print("\nserved files:        %d" % report["served"])
    print("relocated to arena:  %d (a grown file drags its whole "
          "contiguous run along)" % report["relocated_count"])
    for rel, orig, new in report["relocated"]:
        print("    %-40s %d -> %d sectors" % (rel, orig, new))
    print("shrunk (in place):   %d" % len(report["shrunk"]))
    print("unchanged:           %d" % len(report["unchanged"]))
    if report["direct_grown"]:
        print("UNSUPPORTED growth (code-immediate offset, tail ignored):")
        for rel in report["direct_grown"]:
            print("    %s" % rel)
    if report["sound_changed"]:
        print("UNSUPPORTED sound change (IOP-side .bd/.hd, rebuild ISO to apply):")
        for rel in report["sound_changed"]:
            print("    %s" % rel)
    if report["missing"]:
        print("missing on disk (served from mounted disc): %d" % len(report["missing"]))
    print("\nselect-model loader: table-driven, relocated to 0x%08X -- officer "
          "models may grow freely" % report["select_loader_addr"])
    print("wrote %s (blob 0x%X, arena base sector 0x%X)"
          % (report["out"], report["blob_size"], report["arena_base"]))


if __name__ == "__main__":
    main()
