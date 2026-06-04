"""Parametric structural model generators."""

from .frame_generator import generate_floor_mass_mapping, generate_frame_model

__all__ = ["generate_floor_mass_mapping", "generate_frame_model"]
