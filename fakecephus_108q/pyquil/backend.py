"""
FakeCephus-108Q - PyQuil Backend Implementation
===============================================

Native Rigetti implementation using PyQuil's noise modeling and QVM.

This provides authentic Rigetti ecosystem support with:
- Native Quil assembly
- QVM simulation with realistic heterogeneous noise
- quilc compilation
- Compatible with Rigetti QCS for real hardware

KEY FEATURE: Heterogeneous noise model - intra-chip edges have higher
fidelity than inter-chip edges.

Prerequisites:
    docker run -d -p 5555:5555 rigetti/quilc -R
    docker run -d -p 5000:5000 rigetti/qvm -S

Author: Daniel Mo Houshmand (QDaria AS)
License: MIT
"""

from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
import numpy as np

# Check for PyQuil availability
try:
    from pyquil import Program
    from pyquil.quilbase import Declare
    from pyquil.gates import RX, RY, RZ, CZ, MEASURE, I
    from pyquil.noise import (
        NoiseModel,
        KrausModel,
        damping_kraus_map,
        dephasing_kraus_map,
        combine_kraus_maps,
        add_decoherence_noise,
    )
    from pyquil.quantum_processor import NxQuantumProcessor
    PYQUIL_AVAILABLE = True
except ImportError:
    PYQUIL_AVAILABLE = False
    NoiseModel = Any  # type: ignore

from ..specs import (
    Cephus108QSpecs,
    CEPHUS_108Q_SPECS,
    CEPHUS_108Q_EDGES,
    CEPHUS_108Q_INTRA_CHIP_EDGES,
    CEPHUS_108Q_INTER_CHIP_EDGES,
    CEPHUS_108Q_QUBITS,
    get_topology,
)


def _check_pyquil():
    """Raise ImportError if PyQuil is not available."""
    if not PYQUIL_AVAILABLE:
        raise ImportError(
            "PyQuil is required for native Rigetti support.\n"
            "Install with: pip install pyquil\n"
            "For Qiskit compatibility, use: from fakecephus_108q.qiskit import FakeCephus108Q"
        )


def _get_bidirectional_edges(
    edges: List[tuple],
) -> List[tuple]:
    """Get edges in both directions for symmetric 2Q gates."""
    result = []
    for a, b in edges:
        result.append((a, b))
        result.append((b, a))
    return result


def _compute_kraus_ops(
    t1: float,
    t2: float,
    gate_time: float,
) -> List[np.ndarray]:
    """
    Compute combined Kraus operators for T1/T2 decoherence noise.

    Combines amplitude damping (T1) and pure dephasing (T2) channels.

    Args:
        t1: T1 relaxation time in seconds.
        t2: T2 dephasing time in seconds.
        gate_time: Gate duration in seconds.

    Returns:
        List of 2x2 Kraus operator matrices.
    """
    _check_pyquil()

    # Amplitude damping probability
    p_decay = 1 - np.exp(-gate_time / t1) if t1 > 0 else 0

    # Pure dephasing probability (T2 < 2*T1)
    if t1 > 0 and t2 > 0:
        t1_decay = np.exp(-gate_time / t1)
        p_dephase = (1 - t1_decay) * (1 - t2 / (2 * t1))
    else:
        p_dephase = 0

    # Construct combined Kraus operators
    kraus = []

    # K0: No error
    k0 = np.array([[np.sqrt(1 - p_decay), 0],
                   [0, np.sqrt((1 - p_decay) * (1 - p_dephase))]])
    kraus.append(k0)

    # K1: Amplitude damping (decay)
    if p_decay > 0:
        k1 = np.array([[0, np.sqrt(p_decay)],
                       [0, 0]])
        kraus.append(k1)

    # K2: Pure dephasing
    if p_dephase > 0:
        k2 = np.array([[0, 0],
                       [0, np.sqrt(p_dephase)]])
        kraus.append(k2)

    return kraus


def create_noise_model(
    specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
    include_readout: bool = True,
) -> NoiseModel:
    """
    Create a PyQuil NoiseModel for FakeCephus-108Q with heterogeneous fidelities.

    Includes:
    - Depolarizing errors on 1Q gates (from F_1Q)
    - T1/T2 thermal relaxation
    - HETEROGENEOUS 2Q errors: intra-chip vs inter-chip fidelities
    - Asymmetric readout errors (optional)

    Args:
        specs: Cephus-108Q hardware specifications
        include_readout: Include readout errors

    Returns:
        Configured PyQuil NoiseModel
    """
    _check_pyquil()

    noise_model = NoiseModel()

    # Convert units to seconds
    t1 = specs.t1_us * 1e-6
    t2 = specs.t2_us * 1e-6
    gate_time_1q = specs.gate_time_1q_ns * 1e-9
    gate_time_2q = specs.gate_time_2q_ns * 1e-9

    # Single-qubit gate error (RX, RY, RZ)
    p_error_1q = 1 - specs.fidelity_1q

    kraus_1q = [
        np.sqrt(1 - p_error_1q) * np.eye(2),
        np.sqrt(p_error_1q / 3) * np.array([[0, 1], [1, 0]]),    # X error
        np.sqrt(p_error_1q / 3) * np.array([[0, -1j], [1j, 0]]), # Y error
        np.sqrt(p_error_1q / 3) * np.array([[1, 0], [0, -1]]),   # Z error
    ]

    for qubit in CEPHUS_108Q_QUBITS:
        noise_model.add_quantum_error(
            KrausModel(kraus_1q), ["RX", "RY", "RZ"], [qubit]
        )

    # Readout errors (optional)
    if include_readout:
        # Use per-qubit data if available, otherwise use default
        for qubit in CEPHUS_108Q_QUBITS:
            ro_fidelity = specs.readout_fidelity
            
            # If per-qubit data is available, use it
            if (specs.per_qubit_data and 
                qubit in specs.per_qubit_data):
                ro_fidelity = specs.per_qubit_data[qubit].get(
                    'readout_fidelity', specs.readout_fidelity
                )

            p_error_ro = 1 - ro_fidelity

            # Asymmetric readout: P(0|0), P(1|1)
            # Simple model: uniform error
            confusion_matrix = np.array([
                [1 - p_error_ro / 2, p_error_ro / 2],
                [p_error_ro / 2, 1 - p_error_ro / 2],
            ])

            noise_model.add_readout_error(
                confusion_matrix, [qubit]
            )

    # Two-qubit gate errors (HETEROGENEOUS)
    def _make_2q_kraus(fidelity: float):
        """Create 2Q Kraus operators for given fidelity."""
        p_error = 1 - fidelity
        # Depolarizing channel for 2Q gates
        # K0 = sqrt(1-p) * I
        # K1, K2, K3 = sqrt(p/3) * (XX, YY, ZZ)
        return [
            np.sqrt(1 - p_error) * np.eye(4),
            np.sqrt(p_error / 15) * np.kron(np.array([[0, 1], [1, 0]]),
                                             np.array([[0, 1], [1, 0]])),  # XX
            np.sqrt(p_error / 15) * np.kron(np.array([[0, -1j], [1j, 0]]),
                                             np.array([[0, -1j], [1j, 0]])),  # YY
            np.sqrt(p_error / 15) * np.kron(np.array([[1, 0], [0, -1]]),
                                             np.array([[1, 0], [0, -1]])),  # ZZ
        ]

    kraus_2q_intra = _make_2q_kraus(specs.fidelity_2q_intra)
    kraus_2q_inter = _make_2q_kraus(specs.fidelity_2q_inter)

    # Apply intra-chip errors
    for q0, q1 in CEPHUS_108Q_INTRA_CHIP_EDGES:
        noise_model.add_quantum_error(
            KrausModel(kraus_2q_intra), ["CZ"], [q0, q1]
        )

    # Apply inter-chip errors (different fidelity)
    for q0, q1 in CEPHUS_108Q_INTER_CHIP_EDGES:
        noise_model.add_quantum_error(
            KrausModel(kraus_2q_inter), ["CZ"], [q0, q1]
        )

    return noise_model


def get_qc(
    specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
    name: str = "FakeCephus108Q",
    noisy: bool = True,
    qvm_url: str = "http://localhost:5000",
    quilc_url: str = "http://localhost:5555",
) -> Any:
    """
    Get a configured QuantumComputer for Cephus-108Q.

    Args:
        specs: Hardware specifications
        name: Name for the quantum computer
        noisy: Whether to include noise model (default: True)
        qvm_url: URL for QVM server
        quilc_url: URL for quilc compiler

    Returns:
        Configured PyQuil QuantumComputer with 108 qubits

    Raises:
        ImportError: If PyQuil is not installed
        RuntimeError: If QVM/quilc are not accessible
    """
    _check_pyquil()

    from pyquil.api import get_qc as pyquil_get_qc

    # Get topology
    topology = get_topology()

    # Create quantum processor with topology
    qp = NxQuantumProcessor(topology)

    # Add noise model if requested
    if noisy:
        noise_model = create_noise_model(specs)
        qp.noise_model = noise_model

    # Get quantum computer from PyQuil with custom processor
    try:
        qc = pyquil_get_qc(
            name=name,
            quantum_processor=qp,
            asynchronous=False,
            execution_timeout=30,
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not connect to QVM/quilc at {qvm_url}/{quilc_url}\n"
            "Make sure they are running:\n"
            "  docker run -d -p 5555:5555 rigetti/quilc -R\n"
            "  docker run -d -p 5000:5000 rigetti/qvm -S\n"
            f"Error: {e}"
        )

    return qc
