"""Analysis backends beyond the static DSM solver."""

from .mass_assembly import (
    assemble_lumped_mass_matrix,
    assemble_lumped_mass_vector,
    build_lateral_floor_mass_mapping,
)
from .modal_solver import (
    ModalDependencyError,
    solve_modal_analysis,
    solve_modal_from_matrices,
)
from .response_spectrum_generator import generate_elastic_response_spectrum

__all__ = [
    "ModalDependencyError",
    "assemble_lumped_mass_matrix",
    "assemble_lumped_mass_vector",
    "build_lateral_floor_mass_mapping",
    "generate_elastic_response_spectrum",
    "solve_modal_analysis",
    "solve_modal_from_matrices",
]
