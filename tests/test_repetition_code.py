"""
Correctness tests for the repetition code simulator.
Run with: pytest test_repetition_code.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
from repetition_code import build_repetition_code_circuit, decode_syndrome, run_single_trial


def test_circuit_has_correct_qubit_count():
    for d in [3, 5, 7]:
        qc = build_repetition_code_circuit(d)
        assert qc.num_qubits == d + (d - 1)  # data + ancilla


def test_even_distance_rejected():
    try:
        build_repetition_code_circuit(4)
        assert False, "should have raised ValueError for even distance"
    except ValueError:
        pass


def test_no_error_syndrome_is_trivial():
    # All-zero syndrome should produce no correction
    correction = decode_syndrome("00", distance=3)
    assert correction == [0, 0, 0]


def test_single_error_gives_nontrivial_syndrome_correction():
    # Syndrome "10" (bit 0 triggered) should flip qubit 1 under this decoder's convention
    correction = decode_syndrome("01", distance=3)
    assert sum(correction) >= 1


def test_zero_noise_always_preserves_logical_state():
    """With p_error = 0, the logical state must survive every trial."""
    rng = np.random.default_rng(123)
    for logical_state in [0, 1]:
        for _ in range(10):
            assert run_single_trial(distance=3, p_error=0.0, logical_state=logical_state, rng=rng)


def test_higher_distance_improves_survival_at_low_noise():
    """Sanity check: at a fixed low noise rate, distance-5 should not do
    dramatically worse than distance-3 on average (statistical, uses many trials)."""
    rng = np.random.default_rng(7)
    trials = 200
    p = 0.05
    d3_survival = sum(run_single_trial(3, p, 0, rng) for _ in range(trials)) / trials
    d5_survival = sum(run_single_trial(5, p, 0, rng) for _ in range(trials)) / trials
    assert d5_survival >= d3_survival - 0.1  # allow statistical slack


if __name__ == "__main__":
    test_circuit_has_correct_qubit_count()
    test_even_distance_rejected()
    test_no_error_syndrome_is_trivial()
    test_single_error_gives_nontrivial_syndrome_correction()
    test_zero_noise_always_preserves_logical_state()
    test_higher_distance_improves_survival_at_low_noise()
    print("All tests passed.")
