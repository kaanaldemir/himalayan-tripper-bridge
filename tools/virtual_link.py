"""Exercise wire encoding across loopback UDP; never connects to a bike or phone."""
import hashlib
import json
import socket
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridgewire import Segment, RtpPacketizer, control_packet, dash_event_packet, event_reply, parse_dash_events


def run():
    # This sample is synthetic NAL data, not a decodable map or Android Auto video.
    original = b'\x65' + bytes(range(256)) * 24
    packets = RtpPacketizer(sequence=65534, ssrc=7).packetize([original], 90000)
    received = bytearray()
    ack_count = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as phone, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as dash:
        phone.bind(('127.0.0.1', 0))
        dash.bind(('127.0.0.1', 0))
        phone.settimeout(2)
        dash.settimeout(2)
        sequence = 65534
        for packet in packets:
            phone.sendto(packet, dash.getsockname())
            data, _ = dash.recvfrom(1500)
            version, flags, seq, timestamp, ssrc = struct.unpack_from('>BBHII', data)
            if (version, flags & 127, seq, timestamp, ssrc) != (128, 96, sequence & 65535, 90000, 7):
                raise AssertionError('RTP header mismatch')
            sequence += 1
            payload = data[12:]
            if payload[0] & 31 != 28:
                raise AssertionError('Expected FU-A for this sample')
            if payload[1] & 128:
                received.append((payload[0] & 224) | (payload[1] & 31))
            received.extend(payload[2:])
        if bytes(received) != original:
            raise AssertionError('Reassembled transport bytes differ')
        for index, sub in enumerate((6, 4)):
            dash.sendto(dash_event_packet([Segment(9, sub, b'\x55')]), phone.getsockname())
            data, _ = phone.recvfrom(1500)
            reply = event_reply(parse_dash_events(data)[0])
            phone.sendto(control_packet(index, [reply]), dash.getsockname())
            ack, _ = dash.recvfrom(1500)
            expected = bytes.fromhex('0611000155' if sub == 6 else '0612000155')
            if ack[17:] != expected:
                raise AssertionError('Incorrect decoded-frame ACK')
            ack_count += 1
    return {
        'scope': 'Local synthetic wire-path exercise; no phone, bike, authentication or H.264 decoding',
        'rtp_datagrams': len(packets),
        'maximum_datagram_bytes': max(map(len, packets)),
        'reassembled_bytes': len(received),
        'payload_sha256': hashlib.sha256(received).hexdigest(),
        'decoded_frame_acks': ack_count,
        'sequence_wrap_exercised': True,
        'roundtrip_matches': True,
    }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
