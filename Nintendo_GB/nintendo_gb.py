import idaapi
from idc import *

logo = bytes.fromhex("CE ED 66 66 CC 0D 00 0B 03 73 00 83 00 0C 00 0D 00 08 11 1F 88 89 00 0E DC CC 6E E6 DD DD D9 99 BB BB 67 63 6E 0E EC CC DD DC 99 9F BB B9 33 3E".replace(" ", ""))

registers = {
    0xFF00: "rJOYP",
    0xFF01: "rSB",
    0xFF02: "rSC",
    0xFF04: "rDIV",
    0xFF05: "rTIMA",
    0xFF06: "rTMA",
    0xFF07: "rTAC",
    0xFF0F: "rIF",
    0xFF10: "rNR10",
    0xFF11: "rNR11",
    0xFF12: "rNR12",
    0xFF13: "rNR13",
    0xFF14: "rNR14",
    0xFF16: "rNR21",
    0xFF17: "rNR22",
    0xFF18: "rNR23",
    0xFF19: "rNR24",
    0xFF1A: "rNR30",
    0xFF1B: "rNR31",
    0xFF1C: "rNR32",
    0xFF1D: "rNR33",
    0xFF1E: "rNR34",
    0xFF20: "rNR41",
    0xFF21: "rNR42",
    0xFF22: "rNR43",
    0xFF23: "rNR44",
    0xFF24: "rNR50",
    0xFF25: "rNR51",
    0xFF26: "rNR52",
    0xFF30: "rWAV",
    0xFF40: "rLCDC",
    0xFF41: "rSTAT",
    0xFF42: "rSCY",
    0xFF43: "rSCX",
    0xFF44: "rLY",
    0xFF45: "rLYC",
    0xFF46: "rDMA",
    0xFF47: "rBGP",
    0xFF48: "rOBP0",
    0xFF49: "rOBP1",
    0xFF4A: "rWY",
    0xFF4B: "rWX",
    0xFF4D: "rKEY1",
    0xFF4F: "rVBK",
    0xFF51: "rHDMA1",
    0xFF52: "rHDMA2",
    0xFF53: "rHDMA3",
    0xFF54: "rHDMA4",
    0xFF55: "rHDMA5",
    0xFF56: "rRP",
    0xFF68: "rBGPI",
    0xFF69: "rBGPD",
    0xFF6A: "rOBPI",
    0xFF6B: "rOBPD",
    0xFF70: "rSVBK",
    0xFF76: "rPCM12",
    0xFF77: "rPCM34",
    0xFFFF: "rIE",

}

def accept_file(li, filename):
    li.seek(0x104)
    if li.read(0x30) != logo:
        return 0
    return {'format': "Game Boy ROM", 'processor':'gb'}


def add_seg(startea, endea, bank, name):
    s = idaapi.segment_t()
    s.start_ea = startea + bank * 0x10000
    s.end_ea   = endea + bank * 0x10000
    s.sel      = idaapi.setup_selector(bank * 0x1000)
    s.bitness  = 0
    s.align    = idaapi.saRelPara
    s.comb     = idaapi.scPub
    idaapi.add_segm_ex(s, name, "", idaapi.ADDSEG_NOSREG|idaapi.ADDSEG_OR_DIE)



def load_file(li, neflags, format):
    size = li.size()
    size = (size + 0x3FFF) & ~0x3FFF

    idaapi.set_processor_type("gb", idaapi.SETPROC_LOADER)

    add_seg(0, 0x4000, 0, "ROM0")
    li.file2base(0, 0, 0x4000, 1)
    
    for bank in range(1, int(size / 0x4000)):
        add_seg(0x4000, 0x8000, bank, "ROM%02X" % bank)
        li.file2base(0x4000 * bank, 0x4000 + bank * 0x10000, 0x8000 + bank * 0x10000, 1)
    
    li.seek(0x149)
    sram_size_code = ord(li.read(1))
    sram_size = 0
    if sram_size_code < 6:
        sram_size = [0, 1, 1, 4, 16, 8][sram_size_code]
    
    add_seg(0x8000, 0xA000, 0, "VRAM")

    
    for bank in range(0, sram_size):
        add_seg(0xA000, 0xC000, bank, "SRAM%X" % bank)

    li.seek(0x143)
    is_cgb = ord(li.read(1)) & 0x80
    
    if is_cgb:
        add_seg(0xC000, 0xD000, 0, "WRAM0")
        for bank in range(1, 8):
            add_seg(0xD000, 0xE000, bank, "WRAM%X" % bank)
    else:
        add_seg(0xC000, 0xE000, 0, "WRAM")
    
    add_seg(0xFE00, 0xFEA0, 0, "OAM")
    
    add_seg(0xFF00, 0xFF80, 0, "MMIO")
    add_seg(0xFF80, 0xFFFF, 0, "HRAM")
    add_seg(0xFFFF, 0x10000, 0, "IE")
    
    for addr, name in registers.items():
        set_name(addr, name)
        if name == "IO_WAV":
            create_data(addr, 0, 16, 0)
        else:
            create_data(addr, 0, 1, 0)
    
    add_func(0x100)
    set_name(0x100, "Start")
    for i in range(13 - 1, 0 - 1, -1):
        entry = i * 8
        li.seek(entry)
        if li.read(1) in b"\x00\xff":
            continue
        add_func(entry)
        set_name(entry, ["Rst00", "Rst08", "Rst10", "Rst18",
                         "Rst20", "Rst28", "Rst30", "Rst38",
                         "VBlankInterrupt", "StatInterrupt", "TimerInterrupt", "SerialInterrupt",
                         "JoypadInterrupt"][i])
        
    create_data(0x104, 0, 0x30, 0)
    set_name(0x104, "NintendoLogo")
    
    if is_cgb:
        create_strlit(0x134, 0x143)
        set_name(0x134, "Title")
        create_data(0x143, 0, 1, 0)
        set_name(0x143, "CgbFlag")
    else:
        create_strlit(0x134, 0x144)
        set_name(0x134, "Title")
    
    li.seek(0x14B)
    has_new_licensee_code = li.read(1) == '\x33'
    
    create_strlit(0x144, 0x146)
    if has_new_licensee_code:
        set_name(0x144, "LicenseeCode")
    
    create_data(0x146, 0, 1, 0)
    set_name(0x146, "SgbFlag")
    
    create_data(0x147, 0, 1, 0)
    set_name(0x147, "CartridgeType")
    
    create_data(0x148, 0, 1, 0)
    set_name(0x148, "RomSize")
    
    create_data(0x149, 0, 1, 0)
    set_name(0x149, "RamSize")
    
    create_data(0x14A, 0, 1, 0)
    set_name(0x14A, "DestinationCode")
    
    create_data(0x14B, 0, 1, 0)
    set_name(0x14B, "OldLicenseeCode" if has_new_licensee_code else "LicenseeCode")
    
    create_data(0x14C, 0, 1, 0)
    set_name(0x14C, "Version")
    
    create_data(0x14D, 0, 1, 0)
    set_name(0x14D, "HeaderChecksum")
    
    create_data(0x14E, 0, 2, 0)
    set_name(0x14E, "GlobalChecksum")
    
    return 1 
