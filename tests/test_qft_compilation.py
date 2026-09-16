# Copyright IBM 2026

"""Test QFT compilation through the default Gross code pass manager."""

import unittest
from ddt import ddt, data
from qiskit.synthesis.qft import synth_qft_full

from qiskit_resource_estimation.error_models.bicycle.compiler import default_pm


@ddt
class TestQFTCompilation(unittest.TestCase):
    @data(2, 4, 10)
    def test_qft_gate_counts(self, n):
        circuit = synth_qft_full(n, do_swaps=False)
        tqc = default_pm().run(circuit)

        rz_count = 2 * n - 2
        rx_count = n
        ry_count = n
        rzz_count = int(n * (n - 1) / 2)

        expected = rx_count + ry_count + rz_count + rzz_count
        self.assertEqual(expected, sum(tqc.count_ops().values()))


if __name__ == "__main__":
    unittest.main()
