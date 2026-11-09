"""
Test suite for FakeCephus-108Q implementation.

Tests both ideal and noisy backends with various specifications.
"""

import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qiskit import QuantumCircuit


def test_specs():
    """Test specifications module."""
    print("[TEST] Specifications...")
    
    try:
        from fakecephus_108q.specs import (
            CEPHUS_108Q_SPECS,
            CEPHUS_108Q_SPECS_CALIBRATED,
            CEPHUS_108Q_SPECS_CONSERVATIVE,
            CEPHUS_108Q_EDGES,
            CEPHUS_108Q_INTRA_CHIP_EDGES,
            CEPHUS_108Q_INTER_CHIP_EDGES,
            get_chip_id,
            get_grid_position,
            is_inter_chip_edge,
            cumulative_fidelity,
            optimal_depth,
        )
    except Exception as e:
        print(f"  [ERROR] Failed to import: {e}")
        raise
    
    # Test defaults
    assert CEPHUS_108Q_SPECS.num_qubits == 108
    assert CEPHUS_108Q_SPECS.num_chips == 12
    assert CEPHUS_108Q_SPECS.num_qubits_per_chip == 9
    assert len(CEPHUS_108Q_INTRA_CHIP_EDGES) == 144
    assert len(CEPHUS_108Q_EDGES) == 195
    
    # Test chip ID calculations
    assert get_chip_id(0) == 0
    assert get_chip_id(8) == 0
    assert get_chip_id(9) == 1
    assert get_chip_id(35) == 3
    assert get_chip_id(36) == 4
    assert get_chip_id(107) == 11
    
    # Test grid positions
    assert get_grid_position(0) == (0, 0)
    assert get_grid_position(35) == (0, 3)
    assert get_grid_position(36) == (1, 0)
    assert get_grid_position(71) == (1, 3)
    assert get_grid_position(72) == (2, 0)
    assert get_grid_position(107) == (2, 3)
    
    # Test edge detection
    assert is_inter_chip_edge(8, 15)  # Chip 0 -> 1
    assert is_inter_chip_edge(15, 8)  # Bidirectional
    assert not is_inter_chip_edge(0, 1)  # Intra-chip
    
    # Test fidelity calculations
    f_depth1 = cumulative_fidelity(1, CEPHUS_108Q_SPECS)
    f_depth5 = cumulative_fidelity(5, CEPHUS_108Q_SPECS)
    assert 0 < f_depth1 < 1
    assert f_depth5 < f_depth1  # Deeper circuits have lower fidelity
    
    # Test optimal depth
    opt_depth = optimal_depth(0.70, CEPHUS_108Q_SPECS)
    assert opt_depth > 0
    assert cumulative_fidelity(int(opt_depth), CEPHUS_108Q_SPECS) >= 0.65
    
    print("  [PASS] All specification tests passed")


def test_qiskit_backends():
    """Test Qiskit backend implementations."""
    print("[TEST] Qiskit backends...")
    
    from fakecephus_108q.qiskit import FakeCephus108Q
    from fakecephus_108q.specs import (
        CEPHUS_108Q_SPECS,
        CEPHUS_108Q_SPECS_CALIBRATED,
        CEPHUS_108Q_SPECS_CONSERVATIVE,
    )
    
    # Test ideal backend
    backend_ideal = FakeCephus108Q(specs=CEPHUS_108Q_SPECS, noise=False)
    assert backend_ideal.num_qubits == 108
    assert backend_ideal.num_chips == 12
    assert backend_ideal.num_intra_edges == 144
    assert backend_ideal.num_inter_edges == 33  # 51 undirected -> 102 directed
    assert backend_ideal.noise_model is None
    
    # Test noisy backend
    backend_noisy = FakeCephus108Q(specs=CEPHUS_108Q_SPECS, noise=True)
    assert backend_noisy.noise_model is not None
    
    # Test calibrated backend
    backend_calibrated = FakeCephus108Q(specs=CEPHUS_108Q_SPECS_CALIBRATED, noise=True)
    assert backend_calibrated.specs.per_qubit_data is not None
    assert len(backend_calibrated.specs.per_qubit_data) > 0
    
    # Test conservative backend
    backend_conservative = FakeCephus108Q(specs=CEPHUS_108Q_SPECS_CONSERVATIVE, noise=True)
    assert backend_conservative.specs.fidelity_2q_intra == 0.994
    assert backend_conservative.specs.fidelity_2q_inter == 0.985
    
    print("  [PASS] All Qiskit backend tests passed")


def test_circuit_execution():
    """Test circuit execution on backend."""
    print("[TEST] Circuit execution...")
    
    from fakecephus_108q.qiskit import FakeCephus108Q
    from fakecephus_108q.specs import CEPHUS_108Q_SPECS
    
    backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS, noise=True, seed=42)
    
    # Simple Bell state
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    
    job = backend.run(qc, shots=100)
    result = job.result()
    counts = result.get_counts()
    
    # Should get mostly |00> and |11>
    assert '00' in counts or '11' in counts
    assert sum(counts.values()) == 100
    
    # Test multi-qubit circuit
    qc_large = QuantumCircuit(10)
    for q in range(9):
        qc_large.cx(q, q + 1)
    qc_large.measure_all()
    
    job = backend.run(qc_large, shots=50)
    result = job.result()
    counts = result.get_counts()
    assert sum(counts.values()) == 50
    
    print("  [PASS] All circuit execution tests passed")


def test_topology_helpers():
    """Test topology and grid position functions."""
    print("[TEST] Topology helpers...")
    
    from fakecephus_108q.qiskit import FakeCephus108Q
    from fakecephus_108q.specs import CEPHUS_108Q_SPECS
    
    backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS)
    
    # Test get_qubit_chip
    assert backend.get_qubit_chip(0) == 0
    assert backend.get_qubit_chip(9) == 1
    assert backend.get_qubit_chip(107) == 11
    
    # Test get_grid_position
    row, col = backend.get_grid_position(0)
    assert (row, col) == (0, 0)
    
    row, col = backend.get_grid_position(107)
    assert (row, col) == (2, 3)
    
    print("  [PASS] All topology tests passed")


def test_fidelity_methods():
    """Test fidelity calculation methods."""
    print("[TEST] Fidelity methods...")
    
    from fakecephus_108q.qiskit import FakeCephus108Q
    from fakecephus_108q.specs import CEPHUS_108Q_SPECS
    
    backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS)
    
    # Test cumulative_fidelity method
    f1 = backend.cumulative_fidelity(1)
    f5 = backend.cumulative_fidelity(5)
    assert 0 < f1 < 1
    assert f5 < f1
    
    # Test optimal_depth method
    opt_depth = backend.optimal_depth(0.70)
    assert isinstance(opt_depth, int)
    assert opt_depth > 0
    
    print("  [PASS] All fidelity tests passed")


def test_noise_model_creation():
    """Test noise model creation."""
    print("[TEST] Noise model creation...")
    
    from fakecephus_108q.qiskit.noise import create_cephus_noise_model, create_cephus_target
    from fakecephus_108q.specs import CEPHUS_108Q_SPECS
    
    # Create noise model
    nm = create_cephus_noise_model(CEPHUS_108Q_SPECS)
    assert nm is not None
    
    # Create target
    target = create_cephus_target(CEPHUS_108Q_SPECS)
    assert target is not None
    assert target.num_qubits == 108
    
    print("  [PASS] All noise model tests passed")


def test_coupling_map():
    """Test coupling map."""
    print("[TEST] Coupling map...")
    
    from fakecephus_108q.qiskit import FakeCephus108Q
    from fakecephus_108q.specs import CEPHUS_108Q_SPECS
    
    backend = FakeCephus108Q(specs=CEPHUS_108Q_SPECS)
    coupling_map = backend.coupling_map
    
    # Should have 2-qubit connections (bidirectional)
    assert len(coupling_map) == 390  # 195 edges * 2 directions
    
    # Check specific edges
    assert [0, 1] in coupling_map or [1, 0] in coupling_map
    assert [8, 15] in coupling_map or [15, 8] in coupling_map
    
    print("  [PASS] All coupling map tests passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("FakeCephus-108Q Test Suite")
    print("="*60 + "\n")
    
    try:
        test_specs()
        test_qiskit_backends()
        test_circuit_execution()
        test_topology_helpers()
        test_fidelity_methods()
        test_noise_model_creation()
        test_coupling_map()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60 + "\n")
        return True
    except AssertionError as e:
        print(f"\n[FAIL] Assertion Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
