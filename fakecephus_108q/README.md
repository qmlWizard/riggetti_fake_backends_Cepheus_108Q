# FakeCephus-108Q: Rigetti Cephus-1-108Q Quantum Processor Simulator

A complete dual-implementation noise model package for simulating Rigetti's **Cephus-1-108Q** quantum processor.

## Overview

**Cephus-1-108Q** is a 108-qubit multi-chip processor built from **twelve 9-qubit Ankaa-class chiplets** arranged in a **3×4 grid** with intermodule couplers. This package provides:

- **Ideal behavior**: Noise-free simulation for baseline comparisons
- **Calibration-based**: Per-qubit fidelities from device calibration data
- **Heterogeneous noise model**: Different fidelities for intra-chip vs inter-chip gates
- **Dual implementations**: PyQuil (native Rigetti) and Qiskit (compatibility)

### Topology

```
3 rows × 4 columns of chiplets
Each chiplet: 3×3 qubit grid (9 qubits)

Row 0: Chip 0-3   (qubits 0-35)    [Connected horizontally]
Row 1: Chip 4-7   (qubits 36-71)   [Connected horizontally]
Row 2: Chip 8-11  (qubits 72-107)  [Connected horizontally]
       [Connected vertically]
```

- **144 intra-chip edges** (12 per chiplet × 12 chiplets)
- **51 inter-chip edges** (3 per boundary × 17 boundaries)
- **195 total two-qubit connections**

## Quick Start

### Installation

```bash
# Required for Qiskit backend (no Docker needed)
pip install qiskit qiskit-aer numpy

# Optional: For PyQuil backend (requires Docker)
pip install pyquil
```

### Qiskit (Recommended - No Docker)

```python
from fakecephus_108q.qiskit import FakeCephus108Q
from qiskit import QuantumCircuit

# Create backend with ideal behavior
backend_ideal = FakeCephus108Q(noise=False)

# Or with realistic noise
backend_noisy = FakeCephus108Q(noise=True)

# Or with calibration data
from fakecephus_108q.specs import CEPHUS_108Q_SPECS_CALIBRATED
backend_calibrated = FakeCephus108Q(specs=CEPHUS_108Q_SPECS_CALIBRATED)

# Run a circuit
qc = QuantumCircuit(4)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

job = backend_noisy.run(qc, shots=1000)
result = job.result()
counts = result.get_counts()
print(counts)
```

### PyQuil (Native Rigetti - Requires Docker)

```bash
# Start services in Docker
docker run -d -p 5555:5555 rigetti/quilc -R
docker run -d -p 5000:5000 rigetti/qvm -S
```

```python
from fakecephus_108q.pyquil import get_qc
from pyquil import Program
from pyquil.gates import H, CNOT, MEASURE

qc = get_qc()  # 108-qubit QuantumComputer with noise model

program = Program()
program += H(0)
program += CNOT(0, 1)
program += MEASURE(0, [0])
program += MEASURE(1, [1])

bitstring = qc.run(program, [0, 1], trials=1000)
print(bitstring)
```

## Specification Profiles

### CEPHUS_108Q_SPECS (Default - Ideal)
- **F_1Q**: 99.91% (Ankaa-3 median)
- **F_2Q_intra**: 99.5% (on-chip)
- **F_2Q_inter**: 99.0% (cross-chip)
- **T1**: 28 µs, **T2**: 10 µs
- **Readout**: 96.7%

### CEPHUS_108Q_SPECS_CALIBRATED
- Per-qubit data from `Cepheus-1-108Q_device_specs.csv`
- Realistic heterogeneous T1/T2 and fidelities
- Best matches actual hardware

### CEPHUS_108Q_SPECS_CONSERVATIVE
- **F_2Q_intra**: 99.4%
- **F_2Q_inter**: 98.5%
- Pessimistic but robust profile

## API Reference

### Backend Creation

```python
from fakecephus_108q.qiskit import FakeCephus108Q
from fakecephus_108q.specs import (
    CEPHUS_108Q_SPECS,
    CEPHUS_108Q_SPECS_CALIBRATED,
    CEPHUS_108Q_SPECS_CONSERVATIVE,
)

# Qiskit backend
backend = FakeCephus108Q(
    specs=CEPHUS_108Q_SPECS,        # Which profile to use
    seed=42,                         # RNG seed
    noise=True,                      # Include noise (default: True)
)
```

### Backend Properties

```python
backend.num_qubits           # 108
backend.num_chips            # 12
backend.num_qubits_per_chip  # 9
backend.num_intra_edges      # 144
backend.num_inter_edges      # 51
backend.coupling_map         # All valid two-qubit gates
backend.noise_model          # Qiskit NoiseModel (if enabled)
```

### Topology Queries

```python
from fakecephus_108q.specs import (
    get_chip_id,          # Which chiplet does qubit belong to?
    get_grid_position,    # Grid coordinates of qubit
    is_inter_chip_edge,   # Is this edge between chiplets?
)

chip = get_chip_id(107)            # Returns 11
row, col = get_grid_position(107)  # Returns (2, 3)
is_inter = is_inter_chip_edge(8, 18)  # Qubit 8→18 crosses boundary
```

### Fidelity Analysis

```python
from fakecephus_108q.specs import cumulative_fidelity, optimal_depth

# Calculate fidelity at depth d
f_depth_5 = cumulative_fidelity(5, backend.specs)  # ~0.005

# Find depth for target fidelity (70% = QRC threshold)
d_opt = optimal_depth(0.70, backend.specs)  # Returns 0.3 layers
```

### Printing Specifications

```python
from fakecephus_108q.specs import print_specs
print_specs()
```

## Heterogeneous Noise Model

Unlike homogeneous systems, Cephus-108Q's noise is **chiplet-aware**:

**Intra-chip gates** (on same chiplet):
- Higher fidelity (99.5%)
- Shorter decoherence exposure
- Example: qubits 0↔1, 0↔3, 0↔4

**Inter-chip gates** (across chiplet boundary):
- Lower fidelity (99.0%)
- Longer decoherence + coupler noise
- Example: qubits 8↔18 (chip 0→2), 2↔9 (chip 0→1)

## Calibration Data

Per-qubit measurements from `Cepheus-1-108Q_device_specs.csv`:
- T1 relaxation time (µs)
- T2 dephasing time (µs)
- Single-qubit fidelity (f1Q)
- Readout fidelity (fRO)
- Two-qubit fidelity (fCZ)

Used by `CEPHUS_108Q_SPECS_CALIBRATED` profile.

## Examples

### Variational Quantum Algorithm (VQA)

```python
import numpy as np
from qiskit import QuantumCircuit
from fakecephus_108q.qiskit import FakeCephus108Q
from fakecephus_108q.specs import optimal_depth

backend = FakeCephus108Q(noise=True)

# Determine safe depth for 70% fidelity retention
safe_depth = backend.optimal_depth(0.70)
print(f"Safe circuit depth: {safe_depth} layers")

# Build VQA circuit (depth <= safe_depth)
def build_circuit(params):
    qc = QuantumCircuit(10)
    for layer in range(int(safe_depth)):
        for q in range(10):
            qc.rx(params[layer * 10 + q], q)
        for q in range(9):
            qc.cx(q, q + 1)
    return qc

# Simulate
params = np.random.randn(int(safe_depth) * 10)
qc = build_circuit(params)
qc.measure_all()

job = backend.run(qc, shots=1000)
result = job.result()
```

### Multi-Chip Comparison

```python
from fakecephus_108q.specs import (
    CEPHUS_108Q_INTRA_CHIP_EDGES,
    CEPHUS_108Q_INTER_CHIP_EDGES,
)

# Simulate same circuit on intra-chip vs inter-chip qubits
qc_intra = QuantumCircuit(2)
qc_intra.cx(0, 1)  # Use qubit pair from same chiplet
qc_intra.measure_all()

qc_inter = QuantumCircuit(2)
qc_inter.cx(8, 18)  # Use qubit pair from different chiplets
qc_inter.measure_all()

backend = FakeCephus108Q(noise=True)
job1 = backend.run(qc_intra, shots=1000)
job2 = backend.run(qc_inter, shots=1000)

# Inter-chip gates show higher error rates
```

## Files

```
fakecephus_108q/
├── specs.py              # Hardware specifications & topology
├── __init__.py           # Package initialization
├── qiskit/
│   ├── backend.py        # FakeCephus108Q BackendV2
│   ├── noise.py          # Qiskit noise model creation
│   └── __init__.py
└── pyquil/
    ├── backend.py        # PyQuil QuantumComputer wrapper
    └── __init__.py
```

## Architecture Highlights

### Topology Representation
- 12 chiplets in 3×4 grid
- Each chiplet: 3×3 square lattice
- Intra-chip edges: 144 (12 per chiplet)
- Inter-chip edges: 51 (grid boundaries)

### Noise Model
- **Depolarizing errors** on 1Q gates (from F_1Q)
- **Thermal relaxation** (T1/T2)
- **Heterogeneous 2Q errors**:
  - Intra-chip: F_2Q = 99.5%
  - Inter-chip: F_2Q = 99.0%
- **Readout errors** per-qubit

### Specifications
- Dataclass-based for immutability
- Frozen fields prevent accidental modification
- Optional per-qubit calibration data
- Validation of physical constraints (T2 ≤ 2×T1)

## Reference

**Rigetti Cephus-1-108Q**:
- 108-qubit system (12 × 9-qubit chiplets)
- Ankaa-class qubits
- Multi-chip with intermodule couplers
- iSWAP native gate set

**Sources**:
- Rigetti press release: Ankaa-3 performance metrics
- AWS Braket documentation
- SQMS Center collaboration (coherence improvements)
- Calibration data: `Cepheus-1-108Q_device_specs.csv`

## License

MIT License - See LICENSE file

## Author

Daniel Mo Houshmand (QDaria AS)  
mo@qdaria.com

## Contributing

Improvements welcome! This package extends the FakeCepheus-36Q design to 108 qubits with a 3×4 chiplet grid topology.
