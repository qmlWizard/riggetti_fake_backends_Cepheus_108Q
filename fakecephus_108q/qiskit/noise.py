"""
FakeCephus-108Q - Qiskit Noise Model
====================================

Creates Qiskit noise models matching Cephus-1-108Q hardware characteristics.

KEY FEATURE: Heterogeneous noise model - intra-chip edges use higher fidelity
(F_2Q = 99.5%) while inter-chip edges use lower fidelity (F_2Q = 99.0%)
to reflect intermodule coupler overhead.

Author: Daniel Mo Houshmand (QDaria AS)
"""

from typing import Dict, List, Optional, Any
import numpy as np

from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
    thermal_relaxation_error,
    ReadoutError,
)
from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit.library import RZGate, SXGate, XGate, CZGate, IGate
from qiskit.circuit import Parameter, Reset, Measure, Delay

from ..specs import (
    CEPHUS_108Q_SPECS,
    CEPHUS_108Q_INTRA_CHIP_EDGES,
    CEPHUS_108Q_INTER_CHIP_EDGES,
    CEPHUS_108Q_EDGES,
    CEPHUS_108Q_QUBITS,
    Cephus108QSpecs,
)


def create_cephus_noise_model(
    specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
    include_readout: bool = True,
    include_thermal: bool = True,
) -> NoiseModel:
    """
    Create a Qiskit NoiseModel for FakeCephus-108Q with heterogeneous fidelities.

    Includes:
    - Depolarizing errors on 1Q gates (from F_1Q)
    - T1/T2 thermal relaxation (optional)
    - HETEROGENEOUS 2Q errors: intra-chip vs inter-chip fidelities
    - Asymmetric readout errors (optional)

    Args:
        specs: Cephus-108Q hardware specifications
        include_readout: Include readout errors
        include_thermal: Include T1/T2 relaxation

    Returns:
        Configured NoiseModel
    """
    noise_model = NoiseModel()

    # Convert units
    t1 = specs.t1_us * 1e-6
    t2 = specs.t2_us * 1e-6
    gate_time_1q = specs.gate_time_1q_ns * 1e-9
    gate_time_2q = specs.gate_time_2q_ns * 1e-9

    # ----- Single-qubit gate error -----
    p_error_1q = 1 - specs.fidelity_1q

    if include_thermal and t1 > 0 and t2 > 0:
        error_1q = thermal_relaxation_error(t1, t2, gate_time_1q)
        if p_error_1q > 0:
            depol_1q = depolarizing_error(p_error_1q, 1)
            error_1q = error_1q.compose(depol_1q)
    else:
        error_1q = (
            depolarizing_error(p_error_1q, 1) if p_error_1q > 0 else None
        )

    if error_1q is not None:
        noise_model.add_all_qubit_quantum_error(
            error_1q, ['rz', 'sx', 'x', 'id']
        )

    # ----- Two-qubit gate errors (HETEROGENEOUS) -----
    def _make_2q_error(fidelity_2q: float):
        """Create a 2Q error channel for the given fidelity."""
        p_error = 1 - fidelity_2q
        if include_thermal and t1 > 0 and t2 > 0:
            error_single = thermal_relaxation_error(t1, t2, gate_time_2q)
            error = error_single.tensor(error_single)
            if p_error > 0:
                depol = depolarizing_error(p_error, 2)
                error = error.compose(depol)
            return error
        else:
            return depolarizing_error(p_error, 2) if p_error > 0 else None

    # Intra-chip edges: higher fidelity
    error_2q_intra = _make_2q_error(specs.fidelity_2q_intra)

    # Inter-chip edges: lower fidelity
    error_2q_inter = _make_2q_error(specs.fidelity_2q_inter)

    # Add errors to specific edges
    for q0, q1 in CEPHUS_108Q_INTRA_CHIP_EDGES:
        if error_2q_intra is not None:
            noise_model.add_quantum_error(error_2q_intra, ['cx'], [q0, q1])

    for q0, q1 in CEPHUS_108Q_INTER_CHIP_EDGES:
        if error_2q_inter is not None:
            noise_model.add_quantum_error(error_2q_inter, ['cx'], [q0, q1])

    # ----- Readout errors (OPTIONAL) -----
    if include_readout:
        for qubit in CEPHUS_108Q_QUBITS:
            ro_fidelity = specs.readout_fidelity

            # Use per-qubit data if available
            if (specs.per_qubit_data and
                qubit in specs.per_qubit_data):
                ro_fidelity = specs.per_qubit_data[qubit].get(
                    'readout_fidelity', specs.readout_fidelity
                )

            p_error_ro = 1 - ro_fidelity

            # Confusion matrix: [P(measured 0|prepared 0), P(measured 1|prepared 0)]
            # [P(measured 0|prepared 1), P(measured 1|prepared 1)]
            confusion_matrix = np.array([
                [1 - p_error_ro / 2, p_error_ro / 2],
                [p_error_ro / 2, 1 - p_error_ro / 2],
            ])

            noise_model.add_readout_error(
                ReadoutError(confusion_matrix), [qubit]
            )

    return noise_model


def create_cephus_target(
    specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
) -> Target:
    """
    Create a Qiskit Target representing Cephus-108Q topology and gates.

    Args:
        specs: Cephus-108Q hardware specifications

    Returns:
        Configured Target with qubits and gates
    """
    target = Target()

    # Prepare single-qubit gate properties for all qubits
    # Standard Rigetti gate set: RZ, SX, X, ID
    qargs_1q = {(qubit,): None for qubit in CEPHUS_108Q_QUBITS}

    target.add_instruction(RZGate(Parameter("theta")), qargs_1q)
    target.add_instruction(SXGate(), qargs_1q)
    target.add_instruction(XGate(), qargs_1q)
    target.add_instruction(IGate(), qargs_1q)

    # Add two-qubit CZ gates for all edges
    qargs_2q = {(q0, q1): None for q0, q1 in CEPHUS_108Q_EDGES}
    target.add_instruction(CZGate(), qargs_2q)

    # Add measurement and reset for all qubits
    target.add_instruction(Measure(), qargs_1q)
    target.add_instruction(Reset(), qargs_1q)
    target.add_instruction(Delay(Parameter("t")), qargs_1q)

    return target
