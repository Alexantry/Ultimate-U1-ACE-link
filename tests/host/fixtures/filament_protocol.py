"""Test-only constant excerpts from paxx12-24 filament_protocol.py.

SPDX-License-Identifier: GPL-3.0-only
Original source: Snapmaker U1 Klipper plus Paxx12 RFID patches.
Excerpted 2026-10-30 for metadata tests; no readers, cryptographic keys, or parser
implementation are distributed in this fixture. Never installed on a printer.
See ../../../THIRD_PARTY.md and ../../../SOURCES.json for provenance.
"""

FILAMENT_INFO_STRUCT = {
    'VERSION': 0,
    'VENDOR': 'NONE', # Brand Owner
    'MANUFACTURER': 'NONE',
    'MAIN_TYPE': 'NONE',
    'SUB_TYPE': 'NONE',
    'TRAY': 0,
    'ALPHA': 0xFF,
    'MULTI_MODE': 0,
    'COLOR_NUMS': 1,
    'ARGB_COLOR': 0xFFFFFFFF, # Old version
    'RGB_1': 0xFFFFFF,
    'RGB_2': 0xFFFFFF,
    'RGB_3': 0xFFFFFF,
    'RGB_4': 0xFFFFFF,
    'RGB_5': 0xFFFFFF,
    'DIAMETER': 0,
    'WEIGHT': 0,
    'LENGTH': 0,
    'DRYING_TEMP': 0,
    'DRYING_TIME': 0,
    'HOTEND_MAX_TEMP': 0,
    'HOTEND_MIN_TEMP': 0,
    'BED_TYPE': 0,
    'BED_TEMP': 0,
    'FIRST_LAYER_TEMP': 0,
    'OTHER_LAYER_TEMP': 0,
    'SKU': 0,
    'MF_DATE': '19700101',
    'RSA_KEY_VERSION': 0,
    'OFFICIAL': False,
    'CARD_UID': 0,
    'CARD_TYPE': '',
    'CARD_EVENT_TIME': 0,
}

M1_PROTO_UID_LEN                                = (4)

FILAMENT_PROTO_OK                               = 0
