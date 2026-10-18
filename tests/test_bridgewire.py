import sys
import struct
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridgewire import Segment, RtpPacketizer, control_packet, dash_event_packet, event_reply, parse_dash_events


class WireTest(unittest.TestCase):
    def test_auth_request_matches_observed_packet(self):
        actual = control_packet(0, [Segment(8, 4, b'\x01')])
        self.assertEqual(actual.hex(), '0016000200000000020100054b314720000804000101')

    def test_frame_ack_matches_observed_packet(self):
        reply = event_reply(Segment(9, 6, b'\x55'))
        self.assertEqual(control_packet(0, [reply]).hex(), '0016000200000000020100054b314720000611000155')
        self.assertIsNone(event_reply(Segment(9, 6, b'\xaa')))

    def test_control_sequence_wrap(self):
        self.assertEqual(control_packet(256, [Segment(8, 4, b'\x01')])[16], 0)

    def test_malformed_dash_event_is_not_partially_accepted(self):
        packet = dash_event_packet([Segment(9, 6, b'\x55')])
        for length in range(len(packet)):
            with self.assertRaises(ValueError):
                parse_dash_events(packet[:length])
        malformed = bytearray(packet)
        malformed[10:12] = b'\x00\x02'
        with self.assertRaises(ValueError):
            parse_dash_events(malformed)

    def test_multiple_events_and_unknown_event(self):
        events = [Segment(9, 6, b'\x55'), Segment(9, 0, b'\x01\x14'), Segment(0x77, 1, b'')]
        self.assertEqual(parse_dash_events(dash_event_packet(events)), events)
        self.assertEqual(event_reply(events[1]), Segment(6, 0x80, b'\x14'))
        self.assertIsNone(event_reply(events[2]))

    def test_rtp_fragment_boundaries_and_marker(self):
        nal = b'\x65' + b'x' * 3000
        packets = RtpPacketizer(sequence=65535, ssrc=9).packetize([b'\x61hi', nal], 0x100000001)
        self.assertEqual([struct.unpack_from('>H', p, 2)[0] for p in packets], [65535, 0, 1, 2])
        self.assertTrue(all(len(p) <= 1372 for p in packets))
        self.assertEqual([p[1] >> 7 for p in packets], [0, 0, 0, 1])
        self.assertTrue(packets[1][13] & 128)
        self.assertTrue(packets[-1][13] & 64)
        self.assertTrue(all(struct.unpack_from('>I', p, 4)[0] == 1 for p in packets))
        rebuilt = bytes([(packets[1][12] & 224) | (packets[1][13] & 31)]) + b''.join(p[14:] for p in packets[1:])
        self.assertEqual(rebuilt, nal)

    def test_empty_access_units_are_rejected(self):
        for nals in ([], [b'']):
            with self.assertRaises(ValueError):
                RtpPacketizer().packetize(nals, 0)


if __name__ == '__main__':
    unittest.main()
