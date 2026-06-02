from pathlib import Path
import sys

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


def main() -> None:
    model_path = PROJECT_ROOT / "inputs" / "q2" / "ModelB.xml"
    data = load_structure_from_xml(model_path)
    s = Structure.from_dict(data)

    if s.n_active_dofs > 0:
        s.assemble_global_stiffness()
        s.assemble_global_load_vector()

    s.solve()

    out: list[str] = []
    out.append("=== MODEL B THERMAL RESULTS ===")
    out.append(f"Input XML: {model_path}")
    out.append("")
    out.append(f"Nodes: {len(s.nodes)}")
    out.append(f"Elements: {len(s.elements)}")
    out.append(f"Active DOFs: {s.n_active_dofs}")
    out.append("")

    out.append("Nodal Displacements [ux, uy, rz]")
    d_full = s.full_displacement_vector()
    for nid in sorted(s.nodes):
        pos = s.node_index[nid]
        ux = d_full[pos * 3 + 0]
        uy = d_full[pos * 3 + 1]
        rz = d_full[pos * 3 + 2]
        out.append(f"Node {nid}: ux={ux:.6e}, uy={uy:.6e}, rz={rz:.6e}")
    out.append("")

    out.append("Support Reactions [Rx, Ry, Mz]")
    reactions = s.compute_reactions()
    for nid in sorted(reactions):
        r = reactions[nid]
        out.append(f"Node {nid}: Rx={r['rx']:.6e}, Ry={r['ry']:.6e}, Mz={r['mz']:.6e}")
    out.append("")

    out.append("Element End Forces")
    member_forces = s.compute_member_end_forces()
    for eid in sorted(member_forces):
        q = member_forces[eid]
        out.append(f"Element {eid}:")
        out.append(
            "  i-end: "
            f"Nx={q['node_i']['nx']:.6e}, Vy={q['node_i']['vy']:.6e}, Mz={q['node_i']['mz']:.6e}"
        )
        out.append(
            "  j-end: "
            f"Nx={q['node_j']['nx']:.6e}, Vy={q['node_j']['vy']:.6e}, Mz={q['node_j']['mz']:.6e}"
        )

    report = "\n".join(out)
    (PROJECT_ROOT / "results" / "solver" / "Model_B_Results.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
