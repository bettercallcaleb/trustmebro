import unittest
import recovery as r

class RecoveryV04Tests(unittest.TestCase):
    def recover(self,text,fmt="integer",family=None,mode="strict",finish="stop"):
        return r.recover({"format":fmt,"family":family,"mode":mode},{"content":text,"finish_reason":finish})

    def test_missing_prefix_and_fraction(self):
        self.assertEqual(self.recover("ABCXYZ-42","identifier","copy")["candidate"],"ABCXYZ-42")
        self.assertFalse(r.compare({"format":"identifier","answer":"ID-ABCXYZ-42"},self.recover("ABCXYZ-42","identifier","copy"))[0])
        self.assertEqual(self.recover("0.5",family="ipv4-fragment-offset")["candidate"],"0.5")
        self.assertFalse(r.compare({"format":"integer","answer":"0"},self.recover("0.5",family="ipv4-fragment-offset"))[0])

    def test_family_conclusions(self):
        examples=[
            ("Minimum total cost: 37","integer","path","37"),
            ("The maximum NEW data bytes sendable after processing the cumulative ACK is 7000B - 900B = 6101B.","integer","tcp-send-window","6101"),
            ("The maximum new bytes that can be sent is the minimum of 3300B and 2500B, which is 2500B.","integer","tcp-send-window","2500"),
            ("The usable host addresses are 62.","integer","ipv4-cidr-boundaries","62"),
            ("The number of outgoing IPv4 fragments required is 7.","integer","ipv4-fragment-offset","7"),
            ("Therefore, 35 seconds of TTL remain.","integer","dns-ttl-chain","35"),
            ("The binary representation of the expiry status for the records in the original order is 010.","bitstring","dns-ttl-chain","010"),
            ("The integer returned by the query is 8.","integer","sqlite-left-join-null","8"),
            ("The exact two ASCII characters in "+chr(96)+"answer"+chr(96)+" are 'pq'.","text2","posix-file-offsets","pq"),
            ("So, the exact two ASCII characters in the "+chr(96)+"answer"+chr(96)+" are 'p' and 'q'.","text2","posix-file-offsets","pq"),
            ("Final Answer: A reads the integer 444.","integer","sqlite-wal-snapshots","444"),
        ]
        for text,fmt,family,expected in examples:
            with self.subTest(text=text):
                self.assertEqual(self.recover(text,fmt,family)["candidate"],expected)

    def test_terminal_expression_without_recomputation(self):
        self.assertEqual(self.recover("First compute 8 * 4 = 32\nNow add: 32 + 5 = 38\n\n38",family="arithmetic")["candidate"],"38")
        self.assertEqual(self.recover("ABCDEF01\n((X >> 5) XOR (X >> 11)) AND 0xFFFF = 1A2B","hex4","endian-signed-bitfields")["candidate"],"1A2B")
        self.assertIsNone(self.recover("First compute 8 * 4 = 32\nNow add: 32 + 5 = 38\n\n39",family="arithmetic")["candidate"])

    def test_explicit_withdrawal_not_conflict(self):
        d=self.recover("72\n\nWait, no, that is the third octet. Let me recalculate.\n\nThe last octet is 96.\n\n96",family="ipv4-cidr-boundaries")
        self.assertEqual(d["candidate"],"96")
        self.assertEqual(d["withdrawn_candidate"],"72")
        self.assertEqual(d["method"],"explicit_self_correction")
        self.assertIsNone(self.recover("72\n\nThe last octet is 96.",family="ipv4-cidr-boundaries")["candidate"])
        self.assertIsNone(self.recover("72\n\nWait, no, let me recalculate.\n\nFINAL: 96\nFINAL: 97",family="ipv4-cidr-boundaries")["candidate"])

    def test_units_and_truncation(self):
        self.assertIsNone(self.recover("7000B - 900B = 6101B",family="ipv4-fragment-offset")["candidate"])
        self.assertIsNone(self.recover("The maximum NEW data bytes sendable after processing the cumulative ACK is 7000B - 900B = 6101B",family="tcp-send-window",finish="length")["candidate"])

if __name__=="__main__":unittest.main()
