"""Analysis package.

Keep this initializer lightweight. Import analysis functionality directly from
its concrete module, for example ``analysis.modal_solver`` or
``analysis.modal_rha``. Eager re-exports here can create circular imports with
``model`` and ``postprocessing`` modules.
"""

__all__: list[str] = []
