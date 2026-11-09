"""
FakeCephus-108Q - Dual Implementation Noise Model for Rigetti Cephus-1-108Q
============================================================================

A complete noise model package for simulating Rigetti's Cephus-1-108Q QPU.

Cephus-1-108Q is a 108-qubit multi-chip processor built from twelve 9-qubit
Ankaa-class chiplets arranged in a 3x4 grid with intermodule couplers. This
package models the HETEROGENEOUS fidelity: intra-chip gates have higher fidelity
than inter-chip gates.

TWO IMPLEMENTATIONS AVAILABLE:

1. **PyQuil (Native Rigetti)** - PRIMARY
   - Uses Rigetti's native QVM and quilc
   - Authentic Rigetti ecosystem support
   - Requires Docker: quilc + qvm

   ```python
   from fakecephus_108q.pyquil import get_qc, CEPHUS_108Q_SPECS
   qc = get_qc()  # Returns configured QuantumComputer
   ```

2. **Qiskit (Compatibility)** - SECONDARY
   - Uses Qiskit AerSimulator
   - No external dependencies
   - Good for quick prototyping

   ```python
   from fakecephus_108q.qiskit import FakeCephus108Q
   backend = FakeCephus108Q()  # Returns BackendV2
   ```

SPECIFICATION PROFILES:
- CEPHUS_108Q_SPECS (default): F_2Q_intra=99.5%, F_2Q_inter=99.0%
- CEPHUS_108Q_SPECS_CALIBRATED: Per-qubit data from device calibration CSV
- CEPHUS_108Q_SPECS_CONSERVATIVE: F_2Q_intra=99.4%, F_2Q_inter=98.5%

Quick Start (Qiskit - no Docker needed):
    from fakecephus_108q.qiskit import FakeCephus108Q
    backend = FakeCephus108Q()
    
Quick Start (PyQuil - with Docker):
    docker run -d -p 5555:5555 rigetti/quilc -R
    docker run -d -p 5000:5000 rigetti/qvm -S
    
    from fakecephus_108q.pyquil import get_qc
    qc = get_qc()

For topology analysis:
    from fakecephus_108q import get_topology, print_specs
    topology = get_topology()
    print_specs()

Author: Daniel Mo Houshmand (QDaria AS)
License: MIT
Version: 1.0.0
"""

# Shared specifications (always available)
from .specs import (
    Cephus108QSpecs,
    CEPHUS_108Q_SPECS,
    CEPHUS_108Q_SPECS_CALIBRATED,
    CEPHUS_108Q_SPECS_CONSERVATIVE,
    CEPHUS_108Q_EDGES,
    CEPHUS_108Q_INTRA_CHIP_EDGES,
    CEPHUS_108Q_INTER_CHIP_EDGES,
    CEPHUS_108Q_QUBITS,
    CEPHUS_108Q_COUPLING_MAP,
    CEPHUS_108Q_CHIPS,
    is_inter_chip_edge,
    get_chip_id,
    get_grid_position,
    get_topology,
    cumulative_fidelity,
    optimal_depth,
    print_specs,
)

# Version info
__version__ = "1.0.0"
__author__ = "Daniel Mo Houshmand"
__email__ = "mo@qdaria.com"

__all__ = [
    # Specifications
    "Cephus108QSpecs",
    "CEPHUS_108Q_SPECS",
    "CEPHUS_108Q_SPECS_CALIBRATED",
    "CEPHUS_108Q_SPECS_CONSERVATIVE",
    "CEPHUS_108Q_EDGES",
    "CEPHUS_108Q_INTRA_CHIP_EDGES",
    "CEPHUS_108Q_INTER_CHIP_EDGES",
    "CEPHUS_108Q_QUBITS",
    "CEPHUS_108Q_COUPLING_MAP",
    "CEPHUS_108Q_CHIPS",
    # Topology helpers
    "is_inter_chip_edge",
    "get_chip_id",
    "get_grid_position",
    "get_topology",
    # Analysis
    "cumulative_fidelity",
    "optimal_depth",
    "print_specs",
    # Submodules (import as needed)
    "pyquil",
    "qiskit",
]


def get_backend(framework: str = "auto", specs=None, **kwargs):
    """
    Get a FakeCephus108Q backend for the specified framework.

    Args:
        framework: "pyquil", "qiskit", or "auto" (tries qiskit by default)
        specs: Hardware specifications (default: CEPHUS_108Q_SPECS)
        **kwargs: Passed to backend constructor
            - For pyquil: noisy (bool), qvm_url (str), quilc_url (str)
            - For qiskit: seed (int), noise (bool)

    Returns:
        Configured backend (QuantumComputer or BackendV2)

    Example:
        >>> backend = get_backend("qiskit", seed=42)
        >>> backend = get_backend("qiskit", specs=CEPHUS_108Q_SPECS_CALIBRATED)
    """
    if specs is None:
        specs = CEPHUS_108Q_SPECS

    pyquil_params = {'noisy', 'qvm_url', 'quilc_url', 'name', 'specs'}
    qiskit_params = {'seed', 'noise', 'specs'}

    def filter_kwargs(valid_params):
        return {k: v for k, v in kwargs.items() if k in valid_params}

    if framework == "auto":
        try:
            from .qiskit import FakeCephus108Q
            return FakeCephus108Q(specs=specs, **filter_kwargs(qiskit_params))
        except ImportError:
            try:
                from .pyquil import get_qc
                return get_qc(specs=specs, **filter_kwargs(pyquil_params))
            except (ImportError, RuntimeError) as e:
                raise ImportError(
                    f"Could not initialize any backend: {e}\n"
                    "Try: pip install qiskit qiskit-aer"
                )

    elif framework == "pyquil":
        from .pyquil import get_qc
        return get_qc(specs=specs, **filter_kwargs(pyquil_params))

    elif framework == "qiskit":
        from .qiskit import FakeCephus108Q
        return FakeCephus108Q(specs=specs, **filter_kwargs(qiskit_params))

    else:
        raise ValueError(
            f"Unknown framework: {framework}. Use 'pyquil', 'qiskit', or 'auto'"
        )


def _show_status():
    """Check available backends."""
    status = []

    try:
        import pyquil
        status.append("✓ PyQuil available")
    except ImportError:
        status.append("✗ PyQuil not installed (pip install pyquil)")

    try:
        import qiskit
        import qiskit_aer
        status.append("✓ Qiskit available")
    except ImportError:
        status.append("✗ Qiskit not installed (pip install qiskit qiskit-aer)")

    return "\n".join(status)
