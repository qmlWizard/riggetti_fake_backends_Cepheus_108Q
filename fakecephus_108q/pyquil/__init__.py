"""
FakeCephus-108Q PyQuil Backend Module
======================================

Native Rigetti implementation for 108-qubit system.

Example:
    from fakecephus_108q.pyquil import get_qc
    qc = get_qc()  # Returns QuantumComputer with 108 qubits
"""

try:
    from .backend import get_qc, create_noise_model
    PYQUIL_AVAILABLE = True
except ImportError:
    PYQUIL_AVAILABLE = False

__all__ = [
    "get_qc",
    "create_noise_model",
    "PYQUIL_AVAILABLE",
]

if PYQUIL_AVAILABLE:
    from ..specs import (
        CEPHUS_108Q_SPECS,
        CEPHUS_108Q_SPECS_CALIBRATED,
        CEPHUS_108Q_QUBITS,
    )
    __all__.extend([
        "CEPHUS_108Q_SPECS",
        "CEPHUS_108Q_SPECS_CALIBRATED",
        "CEPHUS_108Q_QUBITS",
    ])
