from unittest import TestCase
import numpy as np
from pya import *
import logging
logging.basicConfig(level=logging.DEBUG)


class TestRoutePan(TestCase):
    """Test route, rewire, mono, stereo, pan2 methods"""

    def setUp(self):
        self.sig = np.sin(2 * np.pi * 100 * np.linspace(0, 1, 44100))
        self.asine = Asig(self.sig, sr=44100, label="test_sine")
        self.asineWithName = Asig(self.sig, sr=44100, label="test_sine", cn=['sine'])
        self.sig2ch = np.repeat(self.sig, 2).reshape((44100, 2))
        self.astereo = Asig(self.sig2ch, sr=44100, label="sterep", cn=['l', 'r'])
        # self.astereo = Asig("/examples/samples/stereoTest.wav", label='stereo', cn=['l','r'])
        self.sig16ch = np.repeat(self.sig, 16).reshape((44100, 16))
        self.asine16ch = Asig(self.sig16ch, sr=44100, label="test_sine_16ch")

    def tearDown(self):
        pass

    def test_shift_channel(self):
        """Shift a mono signal to chan 4 should result in a 4 channels signals"""
        result = self.asine.shift_channel(3)
        self.assertEqual(4, result.channels)

        result = self.asineWithName.shift_channel(3)
        self.assertEqual(4, result.channels)

    def test_mono(self):
        """Convert any signal dimension to mono"""
        result = self.astereo.mono([0.5, 0.5])
        self.assertEqual(result.channels, 1)
        result = self.asine16ch.mono(np.ones(16) * 0.1)
        self.assertEqual(result.channels, 1)

    def test_stereo(self):
        """Convert any signal dimension to stereo"""
        result = self.asine.stereo([0.5, 0.5])
        self.assertEqual(result.channels, 2)

        # result = self.asine16ch.stereo([np.ones(16), np.zeros(16)])
        # self.assertEqual(result.channels, 2)

    def test_rewire(self):
        """Rewire channels, e.g. move 0 to 1 with a gain of 0.5"""
        result = self.astereo.rewire({(0, 1): 0.5,
                                      (1, 0): 0.5})
        temp = self.astereo.sig
        expect = temp.copy()
        expect[:, 0] = temp[:, 1] * 0.5
        expect[:, 1] = temp[:, 0] * 0.5
        self.assertTrue(np.allclose(expect[1000:10010, 1], result.sig[1000:10010, 1]))

    def test_pan2(self):
        result = self.astereo.pan2(-1.)
        self.assertAlmostEqual(0, result.sig[:, 1].sum())
        result = self.astereo.pan2(1.)
        self.assertAlmostEqual(0, result.sig[:, 0].sum())
