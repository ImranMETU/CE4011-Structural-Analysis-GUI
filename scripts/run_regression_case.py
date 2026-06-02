"""Quick script to run a single regression case and show outputs."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
COURSE_ROOT = PROJECT_ROOT.parent
A3_ROOT = COURSE_ROOT / "Assignment3"
A3_Q2_ROOT = A3_ROOT / "q2_frame_analysis"

for path in (SRC_ROOT, IO_ROOT, PROJECT_ROOT, A3_ROOT, A3_Q2_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from model.structure import Structure
from xml_loader import load_structure_from_xml


def run_case(case_name: str):
    case_path = PROJECT_ROOT / "inputs" / "regression" / "xml" / case_name
    print(f"Loading case: {case_path.name}")
    print("-" * 80)

    data = load_structure_from_xml(case_path)
    structure = Structure.from_dict(data)

    print(f"Nodes: {len(structure.nodes)}")
    print(f"Elements: {len(structure.elements)}")
    print(f"Active DOFs: {structure.n_active_dofs}")

    if structure.n_active_dofs > 0:
        structure.assemble_global_stiffness()
        structure.assemble_global_load_vector()

    D = structure.solve()
    reactions = structure.compute_reactions()
    member_forces = structure.compute_member_end_forces()

    print(f"\nDisplacement norm: {D.norm():.6e}")
    print(f"\nSupport reactions:")
    for node_id in sorted(reactions):
        r = reactions[node_id]
        print(f"  Node {node_id}: Rx={r['rx']: .6e}, Ry={r['ry']: .6e}, Mz={r['mz']: .6e}")

    print(f"\nMember end forces (local coordinates):")
    for elem_id in sorted(member_forces):
        q = member_forces[elem_id]
        print(f"  Element {elem_id}:")
        print(f"    i-end: Nx={q['node_i']['nx']: .6e}, Vy={q['node_i']['vy']: .6e}, Mz={q['node_i']['mz']: .6e}")
        print(f"    j-end: Nx={q['node_j']['nx']: .6e}, Vy={q['node_j']['vy']: .6e}, Mz={q['node_j']['mz']: .6e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        case_name = sys.argv[1]
    else:
        case_name = "regression_thermal_uniform_truss.xml"
    
    run_case(case_name)
