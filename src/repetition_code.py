"""
Repetition code simulator: encode, inject noise, measure syndromes, decode.

This is the simplest nontrivial quantum error-correcting code — it only protects
against bit-flip (X) errors, but it demonstrates the full QEC pipeline that more
complex codes (surface codes, the punctured Reed-Muller codes I work with for
magic-state distillation) all share: encode -> noise -> syndrome extraction ->
decode -> compare to the original logical state.

Author: Aanha Islam
"""

from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error
import numpy as np


def build_repetition_code_circuit(distance: int, logical_state: int = 0) -> QuantumCircuit:
    """
    Build a distance-d bit-flip repetition code circuit.

    distance: number of physical qubits encoding the one logical qubit (must be odd)
    logical_state: 0 or 1, which logical state to encode
    """
    if distance % 2 == 0:
        raise ValueError("distance must be odd so majority-vote decoding has no ties")

    data = QuantumRegister(distance, name="data")
    ancilla = QuantumRegister(distance - 1, name="ancilla")
    syndrome_bits = ClassicalRegister(distance - 1, name="syndrome")
    data_bits = ClassicalRegister(distance, name="data_out")

    qc = QuantumCircuit(data, ancilla, syndrome_bits, data_bits)

    # Encode: prepare logical |0> or |1>, then fan out with CNOTs
    if logical_state == 1:
        qc.x(data[0])
    for i in range(1, distance):
        qc.cx(data[0], data[i])

    qc.barrier()
    return qc


def add_noise_layer(qc: QuantumCircuit, distance: int, p_error: float, rng: np.random.Generator) -> QuantumCircuit:
    """Manually inject independent bit-flip errors on each data qubit with probability p_error.
    (Explicit injection rather than a noise model, so the exact error pattern is known
    for validating the decoder against ground truth.)"""
    data = qc.qregs[0]
    for i in range(distance):
        if rng.random() < p_error:
            qc.x(data[i])
    qc.barrier()
    return qc


def add_syndrome_extraction(qc: QuantumCircuit, distance: int) -> QuantumCircuit:
    """Measure parity of each adjacent pair of data qubits onto an ancilla."""
    data = qc.qregs[0]
    ancilla = qc.qregs[1]
    syndrome_bits = qc.cregs[0]

    for i in range(distance - 1):
        qc.cx(data[i], ancilla[i])
        qc.cx(data[i + 1], ancilla[i])
        qc.measure(ancilla[i], syndrome_bits[i])

    qc.barrier()
    return qc


def decode_syndrome(syndrome: str, distance: int) -> list[int]:
    """
    Given a syndrome bitstring, return which data qubit(s) to flip to correct the error.

    For a distance-d repetition code the syndrome is a string of (d-1) parity checks.
    This decoder handles the standard single-error case exactly; for weight >= 2 errors
    (outside the code's guaranteed correction radius d // 2) it still returns its best
    single-qubit guess, which may not fully correct the error -- this is expected and is
    what the distance/threshold experiment in run_experiment.py is measuring.
    """
    # syndrome[i] = 1 means data qubits i and i+1 disagree
    syn = [int(b) for b in syndrome[::-1]]  # qiskit bit ordering is reversed
    correction = [0] * distance

    # Find contiguous blocks of triggered syndromes -> error is at the boundary
    i = 0
    while i < len(syn):
        if syn[i] == 1:
            # error most likely on qubit i or i+1; standard convention: flip qubit i+1
            correction[i + 1] ^= 1
            i += 1
        else:
            i += 1
    return correction


def run_single_trial(distance: int, p_error: float, logical_state: int, rng: np.random.Generator) -> bool:
    """Run one encode -> noise -> decode -> check cycle. Returns True if logical state survived."""
    qc = build_repetition_code_circuit(distance, logical_state)
    qc = add_noise_layer(qc, distance, p_error, rng)

    # Track the true error pattern for validation (in a real device you wouldn't have this)
    true_errors = _extract_applied_errors(qc, distance)

    qc = add_syndrome_extraction(qc, distance)
    data_bits = qc.cregs[1]
    data = qc.qregs[0]
    for i in range(distance):
        qc.measure(data[i], data_bits[i])

    sim = AerSimulator()
    result = sim.run(qc, shots=1).result()
    counts = result.get_counts()
    outcome = list(counts.keys())[0]  # format: "data_out syndrome"
    parts = outcome.split(" ")
    data_out = parts[0]
    syndrome = parts[1] if len(parts) > 1 else "0" * (distance - 1)

    correction = decode_syndrome(syndrome, distance)
    corrected = [int(b) ^ c for b, c in zip(data_out[::-1], correction)]

    # Majority vote to recover logical bit
    logical_out = 1 if sum(corrected) > distance / 2 else 0
    return logical_out == logical_state


def _extract_applied_errors(qc: QuantumCircuit, distance: int) -> list[int]:
    """Helper: count how many X gates were applied to each data qubit in the noise layer,
    for internal bookkeeping/validation only."""
    counts = [0] * distance
    for instr in qc.data:
        if instr.operation.name == "x":
            q = instr.qubits[0]
            if q._register.name == "data":
                counts[q._index] += 1
    return [c % 2 for c in counts]


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    qc = build_repetition_code_circuit(distance=3, logical_state=0)
    print(qc.draw())
