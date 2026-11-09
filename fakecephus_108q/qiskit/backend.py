"""
FakeCephus-108Q - Qiskit Backend
=================================

Qiskit-compatible BackendV2 implementation with Cephus-1-108Q noise model.

This provides compatibility for users without QVM/quilc infrastructure.
For native Rigetti support, use fakecephus_108q.pyquil instead.

KEY FEATURE: Heterogeneous noise - intra-chip gates use F_2Q = 99.5%,
inter-chip gates use F_2Q = 99.0%.

Author: Daniel Mo Houshmand (QDaria AS)
License: MIT
"""

from typing import Optional, List, Union
import numpy as np

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target
from qiskit_aer import AerSimulator

from ..specs import (
    CEPHUS_108Q_SPECS,
    CEPHUS_108Q_SPECS_CALIBRATED,
    CEPHUS_108Q_SPECS_CONSERVATIVE,
    CEPHUS_108Q_COUPLING_MAP,
    Cephus108QSpecs,
    cumulative_fidelity,
    optimal_depth,
)
from .noise import create_cephus_noise_model, create_cephus_target


class FakeCephus108Q(BackendV2):
    """
    Qiskit-based noise model for Rigetti Cephus-1-108Q quantum processor.

    Simulates Cephus-108Q QPU with realistic heterogeneous noise matching
    verified specs. Intra-chip gates have higher fidelity than inter-chip
    gates due to intermodule coupler overhead.

    Specification profiles:
    - CEPHUS_108Q_SPECS (default): F_2Q_intra=99.5%, F_2Q_inter=99.0%
    - CEPHUS_108Q_SPECS_CALIBRATED: Per-qubit data from device calibration
    - CEPHUS_108Q_SPECS_CONSERVATIVE: F_2Q_intra=99.4%, F_2Q_inter=98.5%

    Note: This uses Qiskit/AerSimulator. For native Rigetti simulation,
    use fakecephus_108q.pyquil with QVM.

    Example:
        >>> backend = FakeCephus108Q()
        >>> qc = QuantumCircuit(108)
        >>> qc.h(0)
        >>> qc.cx(0, 1)
        >>> qc.measure_all()
        >>> job = backend.run(qc, shots=1000)
        >>> counts = job.result().get_counts()
    """

    def __init__(
        self,
        specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
        seed: Optional[int] = None,
        noise: bool = True,
    ):
        """
        Initialize FakeCephus108Q backend.

        Args:
            specs: Hardware specifications
                   (CEPHUS_108Q_SPECS, CEPHUS_108Q_SPECS_CALIBRATED, or
                    CEPHUS_108Q_SPECS_CONSERVATIVE)
            seed: Random seed for reproducibility
            noise: Whether to include noise model (default: True)
        """
        super().__init__(
            name="fake_cephus_108q_qiskit",
            description=f"Qiskit-based Cephus-1-108Q ({specs.name})",
            backend_version="1.0.0",
        )

        self._specs = specs
        self._seed = seed
        self._noise_enabled = noise

        self._target = create_cephus_target(specs)
        self._noise_model = (
            create_cephus_noise_model(specs) if noise else None
        )

        self._simulator = AerSimulator(
            noise_model=self._noise_model,
            seed_simulator=seed,
        )

        self._options = Options()
        self._options.update_options(shots=2000, seed_simulator=seed)

    @property
    def target(self) -> Target:
        return self._target

    @property
    def max_circuits(self) -> Optional[int]:
        return None

    @property
    def num_qubits(self) -> int:
        return self._specs.num_qubits

    @property
    def specs(self) -> Cephus108QSpecs:
        return self._specs

    @property
    def coupling_map(self) -> List[List[int]]:
        return CEPHUS_108Q_COUPLING_MAP

    @property
    def noise_model(self):
        return self._noise_model

    @classmethod
    def _default_options(cls) -> Options:
        return Options(shots=2000)

    def run(
        self,
        circuits: Union[QuantumCircuit, List[QuantumCircuit]],
        **kwargs
    ):
        """Run circuits on the simulated backend."""
        options = dict(self._options.__dict__)
        options.update(kwargs)
        return self._simulator.run(circuits, **options)

    def cumulative_fidelity(self, depth: int, heterogeneous: bool = True) -> float:
        """Calculate cumulative fidelity for given depth.

        Args:
            depth: Circuit depth (number of variational layers)
            heterogeneous: Use per-edge fidelities (default True)

        Returns:
            Cumulative fidelity as a fraction [0, 1]
        """
        return cumulative_fidelity(depth, self._specs, heterogeneous)

    def optimal_depth(
        self, threshold: float = 0.70, heterogeneous: bool = True
    ) -> int:
        """Calculate optimal circuit depth from fidelity threshold.

        Args:
            threshold: Target cumulative fidelity (default 0.70)
            heterogeneous: Use per-edge fidelities (default True)

        Returns:
            Optimal depth (integer)
        """
        return int(np.ceil(
            optimal_depth(threshold, self._specs, heterogeneous)
        ))

    @property
    def num_chips(self) -> int:
        """Number of chiplets."""
        return self._specs.num_chips

    @property
    def num_qubits_per_chip(self) -> int:
        """Qubits per chiplet."""
        return self._specs.num_qubits_per_chip

    @property
    def num_intra_edges(self) -> int:
        """Number of intra-chip edges."""
        return self._specs.num_intra_edges

    @property
    def num_inter_edges(self) -> int:
        """Number of inter-chip edges."""
        return self._specs.num_inter_edges

    def get_qubit_chip(self, qubit: int) -> int:
        """Get chip ID for a qubit.

        Args:
            qubit: Qubit index (0-107)

        Returns:
            Chip ID (0-11)
        """
        from ..specs import get_chip_id
        return get_chip_id(qubit)

    def get_grid_position(self, qubit: int) -> tuple:
        """Get grid position (row, col) for a qubit.

        Args:
            qubit: Qubit index (0-107)

        Returns:
            Tuple of (row, col) where row in [0,2], col in [0,3]
        """
        from ..specs import get_grid_position
        return get_grid_position(qubit)
