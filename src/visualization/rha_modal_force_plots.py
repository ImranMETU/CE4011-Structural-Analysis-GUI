"""Modal inertia-force state view for response-history postprocessing."""

from __future__ import annotations

from postprocessing.rha_modal_response import package_modal_rha_response
from visualization.modal_force_state_plots import plot_modal_force_state


def plot_modal_story_forces(rha_result, modal_parameters, mode_index=0, time_index=None, ax=None):
    """Compatibility wrapper for the former RHA-only force-state plot."""
    package = package_modal_rha_response(rha_result, modal_parameters)
    acceleration = package["pseudo_acceleration_histories"]
    if mode_index < 0 or mode_index >= acceleration.shape[0]:
        raise IndexError("mode_index is outside the modes used by the RHA.")
    if time_index is None:
        import numpy as np
        time_index = int(np.nanargmax(np.abs(acceleration[mode_index])))
    time_index = int(time_index)
    time = package["time"][time_index]
    a = acceleration[mode_index, time_index]
    model_data = {
        "nodes": {
            idx + 1: {"x": 0.0, "y": float(height)}
            for idx, height in enumerate(modal_parameters["floor_heights"])
        },
        "elements": {},
    }
    return plot_modal_force_state(
        model_data,
        modal_parameters,
        mode_number=mode_index + 1,
        A_value=float(a),
        time_value=float(time),
        ax=ax,
    )
