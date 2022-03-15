import unittest
from dftoolkit.fieldbase import reformat_numeric, multibox_numeric
from dftoolkit.rect import Rect

class NumericFormats(unittest.TestCase):
    def setUp(self):
        self.nn = [Rect(25, 25, 50, 50), Rect(50, 25, 25, 50)]
        self.nnnn = [Rect(25, 25, 50, 50), Rect(50, 25, 75, 50),
                     Rect(75, 25, 100, 50), Rect(100, 25, 125, 50)]
        self.nn_nn = [Rect(25, 25, 50, 50), Rect(50, 25, 75, 50),
                      Rect(80, 25, 105, 50), Rect(105, 25, 130, 50)]

    def test_simple(self):
        self.assertEqual(reformat_numeric('n', '1'), ('1', None))
        self.assertEqual(reformat_numeric('nn', '1'), ('01', None))
        self.assertEqual(reformat_numeric('nn', '01'), ('01', None))
        self.assertEqual(reformat_numeric('nn', '12'), ('12', None))

    def test_sign(self):
        self.assertEqual(reformat_numeric('sn', '1'), ('01', None))
        self.assertEqual(reformat_numeric('Sn', '1'), ('+1', None))
        self.assertEqual(reformat_numeric('snnn', '-123'), ('-123', None))
        self.assertEqual(reformat_numeric('Snnn', '-23'), ('-023', None))
        self.assertEqual(reformat_numeric('sn', '-1'), ('-1', None))
        self.assertEqual(reformat_numeric('Sn', '-1'), ('-1', None))

    def test_decimal(self):
        self.assertEqual(reformat_numeric('nn.n', '1'), ('01.0', None))
        self.assertEqual(reformat_numeric('nn.n', '1.0'), ('01.0', None))
        self.assertEqual(reformat_numeric('nn.n', '1.'), ('01.0', None))
        self.assertEqual(reformat_numeric('nn.nn', '1.12'), ('01.12', None))
        self.assertEqual(reformat_numeric('Snn.nn', '1.12'), ('+01.12', None))
        self.assertEqual(reformat_numeric('Snn.nn', '-1.12'), ('-01.12', None))
        self.assertEqual(reformat_numeric('snn.nn', '1.12'), ('001.12', None))
        self.assertEqual(reformat_numeric('snn.nn', '-1.12'), ('-01.12', None))
        self.assertEqual(reformat_numeric('nn.nn', '.12'), ('00.12', None))

    def test_contants(self):
        self.assertEqual(reformat_numeric('12nn', '1200'),
                         ('1200', None))
        self.assertEqual(reformat_numeric('ABnn', '12'),
                         ('AB12', None))

    def test_truncation(self):
        self.assertEqual(reformat_numeric('n', '12'),
                         ('2', 'value truncated'))
        self.assertEqual(reformat_numeric('nn', '1234'),
                         ('34', 'value truncated'))
        self.assertEqual(reformat_numeric('nn.nn', '1234'),
                         ('34.00', 'value truncated'))
        self.assertEqual(reformat_numeric('nn.nn', '12.345'),
                         ('12.34', 'value truncated'))
        self.assertEqual(reformat_numeric('nn.nn', '12.3400'),
                         ('12.34', None))

    def test_mismatched_format(self):
        self.assertEqual(reformat_numeric('nn', '12.34'),
                         ('12', 'mismatched format and value'))
        self.assertEqual(reformat_numeric('nn.nn', '12.34.56'),
                         ('12.34', 'mismatched format and value'))

    def test_negative_format(self):
        self.assertEqual(reformat_numeric('nn', '-1'),
                         ('01', 'negative value and mismatched format'))
        self.assertEqual(reformat_numeric('nn', '+1'),
                         ('01', None))

    def test_no_format(self):
        self.assertEqual(reformat_numeric('', '1'),
                         ('1', None))
        self.assertEqual(reformat_numeric('', '-1'),
                         ('-1', None))
        self.assertEqual(reformat_numeric('nn', ''),
                         ('', None))

    def test_multibox_format(self):
        self.assertEqual(multibox_numeric('nn', '1', self.nn),
                         ('01', None))
        self.assertEqual(multibox_numeric('nn.nn', '1.2', self.nn_nn),
                         ('0120', None))
        self.assertEqual(multibox_numeric('nn.nn', '1.2', self.nnnn),
                         ('1.20', 'value truncated'))
        self.assertEqual(multibox_numeric('nnnn', '1234', self.nn_nn),
                         ('1234', None))
        self.assertEqual(multibox_numeric('nnn.nn', '123.45', self.nn_nn),
                         ('2345', 'value truncated'))
        self.assertEqual(multibox_numeric('nnnn', '12345', self.nn_nn),
                         ('2345', 'value truncated'))
        self.assertEqual(multibox_numeric('', '12345', self.nn_nn),
                         ('2345', 'value truncated'))
        self.assertEqual(multibox_numeric('', '12.34', self.nn_nn),
                         ('1234', None))
        self.assertEqual(multibox_numeric('', '12.3', self.nn_nn),
                         ('123', None))
        self.assertEqual(multibox_numeric('', '1.23', self.nn_nn),
                         (' 123', None))
        self.assertEqual(multibox_numeric('nn', '', self.nn),
                         ('', None))
        self.assertEqual(multibox_numeric('', '', self.nn_nn),
                         ('', None))

if __name__ == '__main__':
    unittest.main()
