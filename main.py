from dataclasses import dataclass, field
from enum import Enum
from threading import Thread
from typing import Optional

import serial

import graphing

s = serial.Serial("COM3")

SYNC_BYTE = 0xAA
EXCODE_BYTE = 0x55
MAX_PACKET_SIZE = 170

# As per https://developer.neurosky.com/docs/doku.php?id=thinkgear_communications_protocol#step-by-step_guide_to_parsing_a_packet


class Code(Enum):
    POOR_SIGNAL = 0x02
    HEART_RATE = 0x03
    ATTENTION = 0x04
    MEDITATION = 0x05
    RAW_8BIT = 0x06
    RAW_MARKER = 0x07

    # Multibyte
    RAW_WAVE = 0x80
    EEG_POWER = 0x81
    ASIC_EEG_POWER = 0x83
    RRINTERVAL = 0x86


@dataclass
class DataRow:
    excode_byte_count: int = 0
    code: Optional[Code] = None
    v_length: Optional[int] = None
    v_length_remaining: Optional[int] = None
    data: list[int] = field(default_factory=list)


def big_endian_smush(byte_list: list[int]) -> int:
    out = 0x00
    for i, b in enumerate(reversed(byte_list)):
        out |= b << 8 * i
    return out


class ASICEEGPower:
    def __init__(self, packet_data: list[int]) -> None:
        # eight big-endian 3-byte unsigned integer values representing delta, theta, low-alpha high-alpha, low-beta, high-beta, low-gamma, and mid-gamma EEG band power values
        # The eight EEG powers are output in the following order: delta (0.5 - 2.75Hz), theta (3.5 - 6.75Hz), low-alpha (7.5 - 9.25Hz), high-alpha (10 - 11.75Hz), low-beta (13 - 16.75Hz),
        # high-beta (18 - 29.75Hz), low-gamma (31 - 39.75Hz), and mid-gamma (41 - 49.75Hz). These values have no units and therefore are only meaningful compared to each other and to
        # themselves, to consider relative quantity and temporal fluctuations.
        # print([hex(x) for x in packet_data])
        self.waves = dict(
            zip(
                [
                    "delta",
                    "theta",
                    "low_alpha",
                    "high_alpha",
                    "low_beta",
                    "high_beta",
                    "low_gamma",
                    "mid_gamma",
                ],
                [
                    big_endian_smush(packet_data[i : i + 3])
                    for i in range(0, len(packet_data), 3)
                ],
            )
        )


class PacketBuffer:
    byte_buffer = []
    p_length_counter = None
    payload = []

    @staticmethod
    def reset():
        PacketBuffer.byte_buffer.clear()
        PacketBuffer.p_length_counter = None
        PacketBuffer.payload.clear()

    @staticmethod
    def parse_payload():
        payload = list(PacketBuffer.payload)
        datarows = [DataRow()]

        while payload:
            b = payload.pop(0)
            current_datarow = datarows[-1]

            if current_datarow.code is None:
                if b == EXCODE_BYTE:
                    current_datarow.excode_byte_count += 1
                    continue
                # Otherwise, its the code
                current_datarow.code = Code(b)
                continue

            if current_datarow.v_length is None:
                #  If [CODE] >= 0x80, parse the next byte as the [VLENGTH] byte for the current DataRow.
                if current_datarow.code.value >= 0x80:
                    current_datarow.v_length = b
                    continue

                current_datarow.v_length = 1

            if current_datarow.v_length_remaining is None:
                current_datarow.v_length_remaining = current_datarow.v_length

            if current_datarow.v_length_remaining > 0:
                current_datarow.data.append(b)
                current_datarow.v_length_remaining -= 1

                if current_datarow.v_length_remaining == 0:
                    datarows.append(DataRow())
                continue

        return datarows


def packet_thread():
    while True:
        b = s.read(1)[0]

        if not PacketBuffer.byte_buffer:
            # Buffer empty, look for sync packet
            if b != SYNC_BYTE:
                print(f"[{b}] not sync")
                continue
            # Now we wait for another. Very good that protocol calls for two sync bytes because my
            # solderless duct tape hack job doesn't give a great connection
        elif len(PacketBuffer.byte_buffer) == 1:
            # We have one sync byte
            if b != SYNC_BYTE:
                # Go back to step one
                print(f"[{b}] bad second byte")
                PacketBuffer.reset()
                continue
        elif PacketBuffer.p_length_counter is None:
            if b > MAX_PACKET_SIZE:
                print(f"size {b} exceeds max packet size!")
                PacketBuffer.reset()
                continue
            elif b != SYNC_BYTE:
                PacketBuffer.p_length_counter = b
            # otherwise just add it to buffer and ignore
        elif PacketBuffer.p_length_counter > 0:
            # Read the next PLENGTH bytes
            PacketBuffer.p_length_counter -= 1
            PacketBuffer.payload.append(b)
        else:
            # This is the checksum byte. It's the last one!

            # invert lowest bits of accumulated checksum
            checksum = sum(PacketBuffer.payload) & 0xFF
            checksum = ~checksum & 0xFF

            if checksum != b:
                print(f"checksum mismatch: got {b}, expected {checksum}")
                PacketBuffer.reset()
                continue

            datarows = PacketBuffer.parse_payload()
            print("\nOk!\n")
            for row in datarows:
                print(f"{row.code}\t{row.data}")
                if row.code == Code.ASIC_EEG_POWER:
                    graphing.update_eeg_data(ASICEEGPower(row.data))
                elif row.code == Code.ATTENTION:
                    graphing.set_special("attention", row.data[0])
                elif row.code == Code.MEDITATION:
                    graphing.set_special("meditation", row.data[0])
            PacketBuffer.reset()
            continue

        PacketBuffer.byte_buffer.append(b)

Thread(target=packet_thread, daemon=True).start()
graphing.ui_thread()
print("Bye-bye now!")