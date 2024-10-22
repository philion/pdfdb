"""test_pdfdb"""
import unittest

from pdfdb import Range, in_page_range

class TestRange(unittest.TestCase):
    """TestRange"""

    def test_range_from_args(self):
        """test_range_from_args"""
        # [0] = arg value, [1] = expected range results
        values = [
            # range, value, in-range, out-range
            ("3-7", [(3,7)], 3, 8),
            ("4",   [(4,4)], 4, 2),
            ("-4",  [(1,4)], 1, 5),
            ("4-",  [(4,0)], 9, 3),
            ("-11,13,37-", [(1,11),(13,13),(37,0)], 13, 12),
        ]

        for t in values:
            arg = t[0]
            result = t[1]
            in_range = t[2]
            out_range = t[3]
            r:Range = Range.from_args(arg)
            # check length
            self.assertEqual(len(r), len(result), "length of results mismatch")
            # check start and end
            for i, expected in enumerate(result):
                self.assertEqual(r[i].start, expected[0])
                self.assertEqual(r[i].end, expected[1])
            # check in and out of range
            self.assertTrue(in_page_range(in_range, r), f"{in_range} not in-range of {r}")
            self.assertFalse(in_page_range(out_range, r))
