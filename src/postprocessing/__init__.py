"""Postprocessing package.

Keep this initializer lightweight. Import helpers directly from their concrete
modules, for example ``postprocessing.static_results`` or
``postprocessing.comparison_results``. Eager re-exports here can create circular
imports with ``model`` and ``analysis`` modules.
"""

__all__: list[str] = []
