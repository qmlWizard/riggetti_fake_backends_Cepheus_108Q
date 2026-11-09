"""
FakeCephus-108Q - Shared Hardware Specifications
================================================

Rigetti Cephus-1-108Q QPU specifications.

Cephus-1-108Q is a 108-qubit multi-chip processor composed of TWELVE 9-qubit
Ankaa-class chiplets tiled in a 3x4 rectangular arrangement with intermodule
couplers connecting adjacent chiplets.

KEY NOVELTY: Heterogeneous fidelity model - intra-chip gates have higher
fidelity than inter-chip gates due to intermodule coupler overhead.

Topology: 12 chiplets in a 3x4 grid
- Each chiplet: 9 qubits in a 3x3 square lattice
- Total: 12 * 9 = 108 qubits
- Intra-chip edges: 12 per chiplet * 12 = 144 total
- Inter-chip edges: connections between adjacent chiplets in grid

Sources:
- Rigetti press release (2024): Ankaa-3 84Q median F_2Q = 99.5%
  https://www.rigetti.com/newsroom/press-releases/rigetti-announces-ankaa-3
- AWS Braket Rigetti docs: gate times ~40ns 1Q, iSWAP native gate set
  https://docs.aws.amazon.com/braket/latest/developerguide/braket-devices-rigetti.html
- SQMS Center collaboration: improved T1 coherence times
  https://sqms.fnal.gov/
- Cephus-1-108Q device specs: CSV calibration data

Specifications (from calibration data where available):
- T1 = varied per qubit (from CSV data, avg ~28 us)
- T2 = varied per qubit (from CSV data, avg ~10 us)
- F_1Q = varied per qubit (from CSV data, avg ~0.998)
- F_2Q_intra = 99.5% (Ankaa-3 median, conservative estimate)
- F_2Q_inter = 99.0% (conservative estimate for intermodule coupler)
- Readout = varied per qubit (from CSV data, avg ~0.967)
- Gate times: 1Q = 40ns, 2Q = 72ns (Ankaa-3 iSWAP)

Author: Daniel Mo Houshmand (QDaria AS)
License: MIT
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple, Optional
import numpy as np
import csv
import os

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


# =============================================================================
# TOPOLOGY: 3x4 GRID OF 12 CHIPLETS (108 QUBITS)
# =============================================================================

# 12 chiplets in a 3x4 arrangement (3 rows, 4 columns), each a 3x3 square lattice:
#
# Row 0: Chip 0-3   (qubits 0-35)
# Row 1: Chip 4-7   (qubits 36-71)
# Row 2: Chip 8-11  (qubits 72-107)
#
# Intra-chip layout (e.g., Chip 0, qubits 0-8):
#   0 -- 1 -- 2
#   |    |    |
#   3 -- 4 -- 5
#   |    |    |
#   6 -- 7 -- 8

# Chiplet qubit assignments: 12 chiplets * 9 qubits each
CEPHUS_108Q_CHIPS: Dict[int, List[int]] = {
    # Row 0
    0: list(range(0, 9)),        # Qubits 0-8
    1: list(range(9, 18)),       # Qubits 9-17
    2: list(range(18, 27)),      # Qubits 18-26
    3: list(range(27, 36)),      # Qubits 27-35
    # Row 1
    4: list(range(36, 45)),      # Qubits 36-44
    5: list(range(45, 54)),      # Qubits 45-53
    6: list(range(54, 63)),      # Qubits 54-62
    7: list(range(63, 72)),      # Qubits 63-71
    # Row 2
    8: list(range(72, 81)),      # Qubits 72-80
    9: list(range(81, 90)),      # Qubits 81-89
    10: list(range(90, 99)),     # Qubits 90-98
    11: list(range(99, 108)),    # Qubits 99-107
}

# Intra-chip edges: same topology within each chiplet
_INTRA_CHIP_OFFSETS: List[Tuple[int, int]] = [
    # Horizontal
    (0, 1), (1, 2),
    (3, 4), (4, 5),
    (6, 7), (7, 8),
    # Vertical
    (0, 3), (1, 4), (2, 5),
    (3, 6), (4, 7), (5, 8),
]

CEPHUS_108Q_INTRA_CHIP_EDGES: List[Tuple[int, int]] = []
for chip_id in range(12):
    offset = chip_id * 9
    for a, b in _INTRA_CHIP_OFFSETS:
        CEPHUS_108Q_INTRA_CHIP_EDGES.append((a + offset, b + offset))

# Inter-chip edges: connections between adjacent chiplets in 3x4 grid
# Grid positions: [row, col]
# Row 0: Chip 0 (0,0), Chip 1 (0,1), Chip 2 (0,2), Chip 3 (0,3)
# Row 1: Chip 4 (1,0), Chip 5 (1,1), Chip 6 (1,2), Chip 7 (1,3)
# Row 2: Chip 8 (2,0), Chip 9 (2,1), Chip 10 (2,2), Chip 11 (2,3)

CEPHUS_108Q_INTER_CHIP_EDGES: List[Tuple[int, int]] = []

# Helper function to get chip ID from grid position
def _chip_id_from_grid(row: int, col: int) -> int:
    """Get chip ID from grid position (3x4 grid)."""
    return row * 4 + col

# Horizontal connections (same row, adjacent columns)
for row in range(3):
    for col in range(3):  # 0->1, 1->2, 2->3
        chip_left = _chip_id_from_grid(row, col)
        chip_right = _chip_id_from_grid(row, col + 1)
        
        # Right column of left chip (indices 2, 5, 8)
        # connects to left column of right chip (indices 0, 3, 6)
        for local_row in range(3):
            q_left = chip_left * 9 + (2 + local_row * 3)
            q_right = chip_right * 9 + (local_row * 3)
            CEPHUS_108Q_INTER_CHIP_EDGES.append((q_left, q_right))

# Vertical connections (same column, adjacent rows)
for row in range(2):  # 0->1, 1->2
    for col in range(4):
        chip_top = _chip_id_from_grid(row, col)
        chip_bottom = _chip_id_from_grid(row + 1, col)
        
        # Bottom row of top chip (indices 6, 7, 8)
        # connects to top row of bottom chip (indices 0, 1, 2)
        for local_col in range(3):
            q_top = chip_top * 9 + (6 + local_col)
            q_bottom = chip_bottom * 9 + local_col
            CEPHUS_108Q_INTER_CHIP_EDGES.append((q_top, q_bottom))

# All edges combined
CEPHUS_108Q_EDGES: List[Tuple[int, int]] = (
    CEPHUS_108Q_INTRA_CHIP_EDGES + CEPHUS_108Q_INTER_CHIP_EDGES
)

CEPHUS_108Q_QUBITS: List[int] = list(range(108))

# Bidirectional for Qiskit coupling map
CEPHUS_108Q_COUPLING_MAP: List[List[int]] = [
    [a, b] for a, b in CEPHUS_108Q_EDGES
] + [
    [b, a] for a, b in CEPHUS_108Q_EDGES
]

# Sets for fast lookup
_INTER_CHIP_SET_108Q: FrozenSet[Tuple[int, int]] = frozenset(
    CEPHUS_108Q_INTER_CHIP_EDGES
    + [(b, a) for a, b in CEPHUS_108Q_INTER_CHIP_EDGES]
)


def is_inter_chip_edge(q0: int, q1: int) -> bool:
    """Check if an edge crosses chiplet boundaries.

    Args:
        q0: First qubit index
        q1: Second qubit index

    Returns:
        True if the edge is an inter-chip connection
    """
    return (q0, q1) in _INTER_CHIP_SET_108Q


def get_chip_id(qubit: int) -> int:
    """Return the chip ID (0-11) for a given qubit index.

    Args:
        qubit: Qubit index (0-107)

    Returns:
        Chip ID (0-11)

    Raises:
        ValueError: If qubit index is out of range
    """
    if not (0 <= qubit < 108):
        raise ValueError(f"Qubit {qubit} out of range [0, 107]")
    return qubit // 9


def get_grid_position(qubit: int) -> Tuple[int, int]:
    """Get grid position (row, col) from qubit index.

    Args:
        qubit: Qubit index (0-107)

    Returns:
        Tuple of (row, col) where row in [0,2], col in [0,3]
    """
    chip_id = get_chip_id(qubit)
    return (chip_id // 4, chip_id % 4)


# =============================================================================
# SPECIFICATION DATACLASS
# =============================================================================

@dataclass(frozen=True)
class Cephus108QSpecs:
    """
    Rigetti Cephus-1-108Q hardware specifications.

    Supports HETEROGENEOUS fidelity: intra-chip gates have higher fidelity
    than inter-chip gates due to intermodule coupler overhead.

    Attributes:
        name: Profile name
        num_qubits: Number of data qubits (108)
        num_chips: Number of chiplets (12)
        num_qubits_per_chip: Qubits per chiplet (9)
        num_intra_edges: Intra-chip two-qubit connections (144)
        num_inter_edges: Inter-chip two-qubit connections
        t1_us: T1 relaxation time (microseconds)
        t2_us: T2 dephasing time (microseconds)
        fidelity_1q: Single-qubit gate fidelity
        fidelity_2q_intra: Intra-chip two-qubit gate fidelity
        fidelity_2q_inter: Inter-chip two-qubit gate fidelity
        readout_fidelity: Measurement assignment fidelity
        gate_time_1q_ns: Single-qubit gate duration (nanoseconds)
        gate_time_2q_ns: Two-qubit gate duration (nanoseconds)
    """
    name: str = "cephus-1-108q"

    # Topology
    num_qubits: int = 108
    num_chips: int = 12
    num_qubits_per_chip: int = 9
    num_intra_edges: int = 144    # 12 per chip x 12 chips
    num_inter_edges: int = 33     # Calculated from grid connections

    # Coherence times (from calibration data averages)
    t1_us: float = 28.0          # Average from calibration data
    t2_us: float = 10.0          # Average from calibration data

    # Gate fidelities - HETEROGENEOUS
    fidelity_1q: float = 0.998            # From calibration data average
    fidelity_2q_intra: float = 0.995      # On-chip F_2Q (Ankaa-3 median)
    fidelity_2q_inter: float = 0.990      # Cross-chip F_2Q (conservative)

    # Readout (from calibration data)
    readout_fidelity: float = 0.967       # From calibration data average

    # Gate times (Ankaa-3)
    gate_time_1q_ns: float = 40.0         # Ankaa-3 1Q gate time
    gate_time_2q_ns: float = 72.0         # Ankaa-3 iSWAP gate time

    # Per-qubit data (optional, loaded from CSV if available)
    per_qubit_data: Optional[Dict[int, Dict[str, float]]] = None

    def __post_init__(self):
        """Validate physical constraints."""
        if self.t2_us > 2 * self.t1_us:
            raise ValueError(
                f"T2 ({self.t2_us}) cannot exceed 2*T1 ({2 * self.t1_us})"
            )
        if not (0 < self.fidelity_1q <= 1):
            raise ValueError("F_1Q must be in (0, 1]")
        if not (0 < self.fidelity_2q_intra <= 1):
            raise ValueError("F_2Q_intra must be in (0, 1]")
        if not (0 < self.fidelity_2q_inter <= 1):
            raise ValueError("F_2Q_inter must be in (0, 1]")

    @property
    def fidelity_2q(self) -> float:
        """Weighted average F_2Q across all edges."""
        total = self.num_intra_edges + self.num_inter_edges
        return (
            self.num_intra_edges * self.fidelity_2q_intra
            + self.num_inter_edges * self.fidelity_2q_inter
        ) / total

    @property
    def edges(self) -> List[Tuple[int, int]]:
        """Get all topology edges."""
        return CEPHUS_108Q_EDGES

    @property
    def n_edges(self) -> int:
        """Total number of two-qubit gate connections."""
        return len(CEPHUS_108Q_EDGES)

    @property
    def intra_edges(self) -> List[Tuple[int, int]]:
        """Get intra-chip topology edges."""
        return CEPHUS_108Q_INTRA_CHIP_EDGES

    @property
    def inter_edges(self) -> List[Tuple[int, int]]:
        """Get inter-chip topology edges."""
        return CEPHUS_108Q_INTER_CHIP_EDGES


# =============================================================================
# LOAD CALIBRATION DATA FROM CSV
# =============================================================================

def _load_calibration_data(csv_path: str) -> Dict[int, Dict[str, float]]:
    """Load per-qubit calibration data from CSV.

    Expects columns: Qubit, T1 (µs), T2 (µs), f1QRB, fRO, etc.

    Args:
        csv_path: Path to CSV file

    Returns:
        Dict mapping qubit index to {t1, t2, f1q, readout_fidelity}
    """
    data = {}
    if not os.path.exists(csv_path):
        return data

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    qubit = int(row['Qubit'])
                    if 0 <= qubit < 108:
                        data[qubit] = {
                            't1_us': float(row.get('T1 (µs)', 28.0)) if row.get('T1 (µs)') else 28.0,
                            't2_us': float(row.get('T2 (µs)', 10.0)) if row.get('T2 (µs)') else 10.0,
                            'f1q': float(row.get('f1Q sim. RB', 0.998)) if row.get('f1Q sim. RB') else 0.998,
                            'readout_fidelity': float(row.get('fRO', 0.967)) if row.get('fRO') else 0.967,
                        }
                except (ValueError, KeyError):
                    pass
    except Exception as e:
        print(f"Warning: Could not load calibration data from {csv_path}: {e}")

    return data


# =============================================================================
# SPECIFICATION PROFILES
# =============================================================================

# Default Cephus-1-108Q specs with ideal behavior
CEPHUS_108Q_SPECS = Cephus108QSpecs(
    name="cephus-1-108q-ideal",
)

# Load calibration data if available
_CALIB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "cephus_calibration_data",
    "Cepheus-1-108Q_device_specs.csv"
)

_CALIB_DATA = _load_calibration_data(_CALIB_PATH)

# Profile with actual calibration data
CEPHUS_108Q_SPECS_CALIBRATED = Cephus108QSpecs(
    name="cephus-1-108q-calibrated",
    t1_us=28.0,  # Will be overridden per-qubit
    t2_us=10.0,  # Will be overridden per-qubit
    fidelity_1q=0.998,  # Will be overridden per-qubit
    readout_fidelity=0.967,  # Will be overridden per-qubit
    per_qubit_data=_CALIB_DATA if _CALIB_DATA else None,
)

# Conservative profile for robustness
CEPHUS_108Q_SPECS_CONSERVATIVE = Cephus108QSpecs(
    name="cephus-1-108q-conservative",
    fidelity_2q_intra=0.994,
    fidelity_2q_inter=0.985,
)


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def cumulative_fidelity(
    depth: int,
    specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
    heterogeneous: bool = True,
) -> float:
    """
    Calculate cumulative circuit fidelity for given depth.

    With heterogeneous=True (default), accounts for different intra-chip
    and inter-chip gate fidelities.

    Args:
        depth: Circuit depth (number of variational layers)
        specs: Hardware specifications
        heterogeneous: Use per-edge fidelities (default True)

    Returns:
        Cumulative fidelity as a fraction [0, 1]
    """
    if heterogeneous:
        n_intra = specs.num_intra_edges * depth
        n_inter = specs.num_inter_edges * depth
        return (
            specs.fidelity_2q_intra ** n_intra
            * specs.fidelity_2q_inter ** n_inter
        )
    else:
        n_total = specs.n_edges * depth
        return specs.fidelity_2q ** n_total


def optimal_depth(
    fidelity_threshold: float = 0.70,
    specs: Cephus108QSpecs = CEPHUS_108Q_SPECS,
    heterogeneous: bool = True,
) -> float:
    """
    Calculate optimal circuit depth from cumulative fidelity threshold.

    Args:
        fidelity_threshold: Target cumulative fidelity (default 0.70)
        specs: Hardware specifications
        heterogeneous: Use per-edge fidelities (default True)

    Returns:
        Optimal depth (may be fractional; round for practical use)
    """
    if heterogeneous:
        log_per_layer = (
            specs.num_intra_edges * np.log(specs.fidelity_2q_intra)
            + specs.num_inter_edges * np.log(specs.fidelity_2q_inter)
        )
    else:
        log_per_layer = specs.n_edges * np.log(specs.fidelity_2q)

    return np.log(fidelity_threshold) / log_per_layer


def get_topology():
    """
    Get Cephus-108Q topology as NetworkX graph.

    Nodes have 'chip' and 'grid_pos' attributes.
    Edges have a 'type' attribute: 'intra' or 'inter'.

    Returns:
        NetworkX Graph with 108 nodes and edges

    Raises:
        ImportError: If networkx is not installed
    """
    if not HAS_NETWORKX:
        raise ImportError("networkx required: pip install networkx")

    G = nx.Graph()

    # Add nodes with chip and grid position attributes
    for chip_id, qubits in CEPHUS_108Q_CHIPS.items():
        row, col = divmod(chip_id, 4)
        for q in qubits:
            G.add_node(q, chip=chip_id, grid_pos=(row, col))

    # Add intra-chip edges
    for a, b in CEPHUS_108Q_INTRA_CHIP_EDGES:
        G.add_edge(a, b, type="intra")

    # Add inter-chip edges
    for a, b in CEPHUS_108Q_INTER_CHIP_EDGES:
        G.add_edge(a, b, type="inter")

    return G


def print_specs(specs: Cephus108QSpecs = CEPHUS_108Q_SPECS):
    """Print formatted specifications."""
    print(f"\n{'Cephus-1-108Q Specifications':=^60}")
    print(f"Profile: {specs.name}")
    print(f"\n{'Topology':^60}")
    print(f"  Qubits:              {specs.num_qubits}")
    print(f"  Chiplets:            {specs.num_chips}")
    print(f"  Qubits per chiplet:  {specs.num_qubits_per_chip}")
    print(f"  Intra-chip edges:    {specs.num_intra_edges}")
    print(f"  Inter-chip edges:    {specs.num_inter_edges}")
    print(f"  Total edges:         {specs.n_edges}")
    print(f"\n{'Coherence Times':^60}")
    print(f"  T1:                  {specs.t1_us:.1f} µs")
    print(f"  T2:                  {specs.t2_us:.1f} µs")
    print(f"\n{'Gate Fidelities':^60}")
    print(f"  1Q gate:             {specs.fidelity_1q*100:.3f}%")
    print(f"  2Q (intra-chip):     {specs.fidelity_2q_intra*100:.3f}%")
    print(f"  2Q (inter-chip):     {specs.fidelity_2q_inter*100:.3f}%")
    print(f"  2Q (weighted avg):   {specs.fidelity_2q*100:.3f}%")
    print(f"\n{'Readout':^60}")
    print(f"  Fidelity:            {specs.readout_fidelity*100:.3f}%")
    print(f"\n{'Gate Times':^60}")
    print(f"  1Q:                  {specs.gate_time_1q_ns:.1f} ns")
    print(f"  2Q:                  {specs.gate_time_2q_ns:.1f} ns")
    print()
