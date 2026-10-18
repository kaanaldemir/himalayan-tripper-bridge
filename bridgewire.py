"""Original, desktop-testable pieces of the stock dash wire path.

This is not an Android Auto receiver or a dash session implementation. Packet
constants are protocol observations; no proprietary application code is included.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class Segment:
    kind: int
    sub: int
    value: bytes


def _segments(segments):
    result = bytearray()
    for segment in segments:
        if not 0 <= segment.kind <= 255 or not 0 <= segment.sub <= 255:
            raise ValueError("TLV identifiers must be bytes")
        if len(segment.value) > 65535:
            raise ValueError("TLV exceeds its 16-bit length")
        result.extend(struct.pack('>BBH', segment.kind, segment.sub, len(segment.value)))
        result.extend(segment.value)
    return bytes(result)


def control_packet(sequence, segments):
    """Encode a phone-to-dash K1G packet; wrap the rolling sequence to a byte."""
    segments = tuple(segments)
    body = b'\x00\x00\x00\x00\x02\x01\x00\x05K1G ' + bytes([sequence & 255]) + _segments(segments)
    if len(body) + 4 > 65535 or len(segments) + 1 > 65535:
        raise ValueError("K1G packet exceeds its 16-bit fields")
    return struct.pack('>HH', len(body) + 4, len(segments) + 1) + body


def dash_event_packet(segments):
    """Build the short incoming header for the local virtual peer only."""
    segments = tuple(segments)
    body = b'\x00' * 4 + _segments(segments)
    if len(body) + 4 > 65535 or len(segments) > 65535:
        raise ValueError("Dash event packet exceeds its 16-bit fields")
    return struct.pack('>HH', len(body) + 4, len(segments)) + body


def parse_dash_events(packet):
    """Reject truncated/mismatched datagrams instead of acknowledging partial events."""
    if len(packet) < 8:
        raise ValueError("Missing dash header")
    size, count = struct.unpack_from('>HH', packet)
    if size != len(packet):
        raise ValueError("Datagram length differs from declared packet length")
    result = []
    pos = 8
    for _ in range(count):
        if pos + 4 > len(packet):
            raise ValueError("Truncated TLV header")
        kind, sub, length = struct.unpack_from('>BBH', packet, pos)
        pos += 4
        if pos + length > len(packet):
            raise ValueError("Truncated TLV value")
        result.append(Segment(kind, sub, packet[pos:pos+length]))
        pos += length
    if pos != len(packet):
        raise ValueError("Trailing bytes beyond declared segments")
    return result


def event_reply(event):
    """Return only the supported mandatory ACK TLV, or None for an unknown event."""
    if event.kind == 9 and event.value == b'\x55' and event.sub in (4, 6):
        return Segment(6, 0x11 if event.sub == 6 else 0x12, b'\x55')
    if event.kind == 9 and event.sub == 0 and event.value:
        return Segment(6, 0x80, event.value[-1:])
    return None


class RtpPacketizer:
    """AVC RTP framing with the conservative sizes observed in RE 10.1.23.

    The APK's a78.c/h use 1358-byte data chunks; FU-A packets are at most
    1372 bytes including 12 RTP and 2 FU bytes. No STAP aggregation is added.
    Input can include a caller-prepared SPS/PPS/IDR bundle; codec conversion,
    frame-boundary detection and decoder parameter handling belong upstream.
    """
    def __init__(self, sequence=0, ssrc=1):
        self.sequence = sequence & 65535
        self.ssrc = ssrc & 0xffffffff

    def packetize(self, access_unit, timestamp_90khz):
        nals = tuple(access_unit)
        if not nals or any(not nal for nal in nals):
            raise ValueError("An access unit must contain nonempty NAL units")
        plan = []
        for nal in nals:
            if len(nal) <= 1358:
                plan.append(nal)
                continue
            indicator = (nal[0] & 0xe0) | 28
            for offset in range(1, len(nal), 1358):
                end = min(offset + 1358, len(nal))
                flags = (0x80 if offset == 1 else 0) | (0x40 if end == len(nal) else 0)
                plan.append(bytes([indicator, flags | (nal[0] & 31)]) + nal[offset:end])
        packets = []
        for index, payload in enumerate(plan):
            marker = 0x80 if index == len(plan) - 1 else 0
            header = struct.pack('>BBHII', 0x80, marker | 96, self.sequence,
                                 timestamp_90khz & 0xffffffff, self.ssrc)
            packets.append(header + payload)
            self.sequence = (self.sequence + 1) & 65535
        return packets
