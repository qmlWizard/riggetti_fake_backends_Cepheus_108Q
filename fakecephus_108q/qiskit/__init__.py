"""
FakeCephus-108Q Qiskit Backend Module
======================================

Qiskit BackendV2 implementation for 108-qubit system.

Example:
    from fakecephus_108q.qiskit import FakeCephus108Q
    backend = FakeCephus108Q()
    
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(108)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    
    job = backend.run(qc, shots=1000)
    counts = job.result().get_counts()
"""

from .backend import FakeCephus108Q
from .noise import create_cephus_noise_model, create_cephus_target

__all__ = [
    "FakeCephus108Q",
    "create_cephus_noise_model",
    "create_cephus_target",
]
