# FakeCephus-108Q

**Quantum processor simulator for Rigetti's 108-qubit Cephus-1-108Q**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A complete, production-ready simulator for Rigetti's 108-qubit Cephus-1-108Q processor with a 3×4 chiplet grid topology.

---

## Features

| Feature | Details |
|---------|---------|
| **Qubits** | 108 (12 chiplets × 9 qubits each) |
| **Topology** | 3×4 chiplet grid |
| **Connectivity** | 195 2-qubit gates (144 intra-chip + 51 inter-chip) |
| **Noise Model** | Heterogeneous: 99.5% intra-chip, 99.0% inter-chip fidelities |
| **Frameworks** | Qiskit BackendV2 + PyQuil |
| **Calibration** | Per-qubit data from hardware specifications |
| **Testing** | Comprehensive test suite, 100% passing |

### Chiplet Grid Topology

```
Chiplet Layout (3×4):
┌─────┬─────┬─────┬─────┐
│  0  │  1  │  2  │  3  │  Row 0
├─────┼─────┼─────┼─────┤
│  4  │  5  │  6  │  7  │  Row 1
├─────┼─────┼─────┼─────┤
│  8  │  9  │ 10  │ 11  │  Row 2
└─────┴─────┴─────┴─────┘

Each chiplet: 9 qubits (numbered sequentially)
Intra-chip edges: 12 per chiplet (144 total)
Inter-chip edges: Grid connections (51 total)
```

---

## Installation

### From Source

```bash
git clone <repository-url>
cd rigetti-fake-backend
pip install -e ".[all]"
```

### Dependencies

```bash
# Qiskit backend (recommended)
pip install "qiskit>=1.0" "qiskit-aer>=0.13" numpy

# PyQuil backend (requires Docker services)
pip install "pyquil>=4.0" numpy
```

---

## Quick Start

### Qiskit Backend

```python
from fakecephus_108q.qiskit import FakeCephus108Q
from fakecephus_108q.specs import CEPHUS_108Q_SPECS_CALIBRATED
from qiskit import QuantumCircuit

# Create backend with realistic per-qubit calibration noise
backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS_CALIBRATED, noise=True)

# Create and run a circuit
qc = QuantumCircuit(10)
qc.h(0)
for i in range(9):
    qc.cx(i, i+1)
qc.measure_all()

job = backend.run(qc, shots=1024)
result = job.result()
print(result.get_counts())
```

### Topology Queries

```python
# Which chiplet?
chip_id = backend.get_qubit_chip(45)  # Returns 5

# Grid position?
row, col = backend.get_grid_position(45)  # Returns (1, 1)

# All 2-qubit connections?
coupling_map = backend.coupling_map  # 390 directed edges
```

### Fidelity Analysis

```python
# Cumulative fidelity at depth 5
f = backend.cumulative_fidelity(depth=5)

# Maximum depth for 70% fidelity
max_depth = backend.optimal_depth(threshold=0.70)
```

---

## Backend Profiles

### CEPHUS_108Q_SPECS (Ideal)
- No noise model
- 100% gate fidelities
- Use for correctness testing

### CEPHUS_108Q_SPECS_CALIBRATED (Recommended)
- Heterogeneous noise model
- Per-qubit calibration data from CSV
- Realistic fidelities and relaxation times
- **Recommended for production simulations**

### CEPHUS_108Q_SPECS_CONSERVATIVE
- Lower fidelity estimates (99.4% intra, 98.5% inter)
- Useful for worst-case analysis

---

## Noise Model

The heterogeneous noise model includes:

1. **Depolarizing errors** on 2-qubit gates
   - Intra-chip: 99.5% fidelity (144 edges)
   - Inter-chip: 99.0% fidelity (51 edges)

2. **Single-qubit errors**: 99.9% fidelity

3. **Thermal relaxation**: Per-qubit T1, T2 times

4. **Readout errors**: Per-qubit confusion matrices

---

## API Reference

### FakeCephus108Q (Qiskit BackendV2)

```python
class FakeCephus108Q:
    def __init__(self, specs=CEPHUS_108Q_SPECS_CALIBRATED, noise=True, seed=None)
    
    # Properties
    num_qubits: int                           # 108
    num_chips: int                            # 12
    coupling_map: list[tuple[int, int]]       # All 2Q connections
    noise_model: NoiseModel | None            # Qiskit noise model
    
    # Methods
    run(circuits, shots=1024, **kwargs) -> Job
    cumulative_fidelity(depth: int) -> float
    optimal_depth(threshold: float) -> int
    get_qubit_chip(qubit: int) -> int
    get_grid_position(qubit: int) -> tuple[int, int]
```

### Specifications

```python
from fakecephus_108q.specs import (
    CEPHUS_108Q_SPECS,                # Ideal specs
    CEPHUS_108Q_SPECS_CALIBRATED,     # With per-qubit data
    CEPHUS_108Q_SPECS_CONSERVATIVE,   # Pessimistic
    CEPHUS_108Q_EDGES,                # All 195 edges
    CEPHUS_108Q_INTRA_CHIP_EDGES,     # 144 intra-chip
    CEPHUS_108Q_INTER_CHIP_EDGES,     # 51 inter-chip
)
```

---

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_fakecephus_108q.py -v

# With coverage
pytest tests/ --cov=fakecephus_108q --cov-report=term-missing
```

**Test Coverage:**
- Specifications validation
- Qiskit backend creation
- Circuit execution with noise
- Topology helper functions
- Fidelity calculations
- Noise model creation
- Coupling map validation

---

## File Structure

```
rigetti-fake-backend/
├── fakecephus_108q/                   # Main package
│   ├── specs.py                       # Topology & specifications
│   ├── __init__.py                    # Package initialization
│   ├── README.md                      # API reference
│   ├── qiskit/
│   │   ├── backend.py                 # Qiskit BackendV2
│   │   ├── noise.py                   # Noise model
│   │   └── __init__.py
│   └── pyquil/
│       ├── backend.py                 # PyQuil backend
│       └── __init__.py
├── tests/
│   └── test_fakecephus_108q.py        # Test suite
├── cephus_calibration_data/
│   └── Cepheus-1-108Q_device_specs.csv # Per-qubit calibration data
├── README.md                          # This file
├── pyproject.toml                     # Package configuration
└── LICENSE                            # MIT License
```

---

## Examples

### Example 1: Bell Pair with Noise

```python
from fakecephus_108q.qiskit import FakeCephus108Q
from fakecephus_108q.specs import CEPHUS_108Q_SPECS_CALIBRATED
from qiskit import QuantumCircuit

backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS_CALIBRATED, noise=True)

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

job = backend.run(qc, shots=1000)
result = job.result()
counts = result.get_counts()
print(counts)
```

### Example 2: GHZ State

```python
qc = QuantumCircuit(6)
qc.h(0)
for i in range(5):
    qc.cx(i, i+1)
qc.measure_all()

job = backend.run(qc, shots=512)
result = job.result()
counts = result.get_counts()
print(counts)
```

### Example 3: Depth Analysis

```python
for depth in [1, 5, 10, 20, 50]:
    f = backend.cumulative_fidelity(depth)
    print(f"Depth {depth}: {f:.2%} fidelity")
```

---

## Troubleshooting

### ImportError: No module named 'fakecephus_108q'

Ensure the package is installed:
```bash
pip install -e .
```

### Circuit execution is slow

Use the ideal backend for benchmarking:
```python
from fakecephus_108q.specs import CEPHUS_108Q_SPECS
backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS, noise=False)
```

### PyQuil backend errors

PyQuil requires docker services:
```bash
docker run -d -p 5555:5555 rigetti/quilc -R
docker run -d -p 5000:5000 rigetti/qvm -S
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Status**: Production Ready | **Tests**: All Passing | **Python**: 3.9+
