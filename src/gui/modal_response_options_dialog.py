"""Modal response and force-state display options dialog."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox


class ModalResponseOptionsDialog:
    """Edit modal force-state display settings without cluttering the toolbar."""

    def __init__(
        self,
        parent: tk.Misc,
        force_mode: tk.StringVar,
        acceleration: tk.StringVar,
        use_rha: tk.BooleanVar,
        time_index: tk.StringVar,
        on_apply: Callable[[], None] | None = None,
    ) -> None:
        self.force_mode = force_mode
        self.acceleration = acceleration
        self.use_rha = use_rha
        self.time_index = time_index
        self.on_apply = on_apply

        self.window = tk.Toplevel(parent)
        self.window.title("Modal Response / Force-State Options")
        self.window.transient(parent)
        self.window.resizable(False, False)

        self.force_mode_input = tk.StringVar(self.window, value=force_mode.get())
        self.acceleration_input = tk.StringVar(self.window, value=acceleration.get())
        self.use_rha_input = tk.BooleanVar(self.window, value=use_rha.get())
        self.time_index_input = tk.StringVar(self.window, value=time_index.get())

        content = tk.Frame(self.window, padx=12, pady=12)
        content.pack(fill=tk.BOTH, expand=True)

        tk.Label(content, text="Force mode:").grid(row=0, column=0, sticky=tk.W, pady=3)
        tk.Spinbox(
            content,
            from_=1,
            to=20,
            textvariable=self.force_mode_input,
            width=8,
        ).grid(row=0, column=1, sticky=tk.W, pady=3)

        tk.Label(content, text="A_n:").grid(row=1, column=0, sticky=tk.W, pady=3)
        tk.Entry(content, textvariable=self.acceleration_input, width=10).grid(
            row=1,
            column=1,
            sticky=tk.W,
            pady=3,
        )

        tk.Checkbutton(content, text="Use RHA", variable=self.use_rha_input).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=tk.W,
            pady=3,
        )

        tk.Label(content, text="Time index:").grid(row=3, column=0, sticky=tk.W, pady=3)
        tk.Entry(content, textvariable=self.time_index_input, width=10).grid(
            row=3,
            column=1,
            sticky=tk.W,
            pady=3,
        )

        buttons = tk.Frame(content)
        buttons.grid(row=4, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        tk.Button(buttons, text="Apply", width=9, command=self.apply).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(buttons, text="Close", width=9, command=self.window.destroy).pack(side=tk.LEFT)

        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

    def apply(self) -> None:
        """Validate the entries, update the shared GUI state, and refresh if needed."""
        try:
            mode = int(self.force_mode_input.get())
            if mode < 1:
                raise ValueError("Force mode must be a positive integer.")
            acceleration = float(self.acceleration_input.get())
            time_text = self.time_index_input.get().strip()
            if time_text and int(time_text) < 0:
                raise ValueError("Time index must be blank or a nonnegative integer.")
        except ValueError as exc:
            messagebox.showerror("Invalid modal response option", str(exc), parent=self.window)
            return

        self.force_mode.set(str(mode))
        self.acceleration.set(str(acceleration))
        self.use_rha.set(bool(self.use_rha_input.get()))
        self.time_index.set(time_text)
        if self.on_apply is not None:
            self.on_apply()


def open_modal_response_options_dialog(
    parent: tk.Misc,
    force_mode: tk.StringVar,
    acceleration: tk.StringVar,
    use_rha: tk.BooleanVar,
    time_index: tk.StringVar,
    on_apply: Callable[[], None] | None = None,
) -> ModalResponseOptionsDialog:
    """Open and return the modal response / force-state options dialog."""
    return ModalResponseOptionsDialog(
        parent,
        force_mode,
        acceleration,
        use_rha,
        time_index,
        on_apply,
    )
