from __future__ import annotations

import base64
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..app_state import FileSelectionModel
from ..models import AnnotationOptions, RunOptions
from ..pipeline import (
    CancelledError,
    default_output_dir,
    open_output_folder,
    process_pdfs,
    render_preview_png,
    resolve_output_path,
)
from .widgets import Tooltip


class AnnotateMergePanel(ttk.Frame):
    """Panel containing the annotate-and-merge workflow UI."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        status_var: tk.StringVar,
        progress_var: tk.DoubleVar,
        event_queue: queue.Queue[tuple[str, object]],
        run_lock: threading.Lock | None = None,
    ) -> None:
        super().__init__(parent)
        self.status_var = status_var
        self.progress_var = progress_var
        self.event_queue = event_queue
        self._run_lock = run_lock  # hub-level lock preventing concurrent cross-panel runs

        self.model = FileSelectionModel()
        self.cancel_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.preview_image: tk.PhotoImage | None = None
        self.custom_output_dir: Path | None = None
        self.running = False

        self.annotation_template_var = tk.StringVar(value="{filename}")
        self.position_var = tk.StringVar(value="top-center")
        self.font_size_var = tk.IntVar(value=12)
        self.margin_var = tk.IntVar(value=24)
        self.box_opacity_var = tk.DoubleVar(value=0.5)
        self.output_filename_var = tk.StringVar(value="annotated-merged.pdf")
        self.save_intermediate_var = tk.BooleanVar(value=False)
        self.open_folder_var = tk.BooleanVar(value=True)
        self.output_dir_var = tk.StringVar(value=str(default_output_dir([])))

        self._build_ui()
        self._refresh_list()
        self._refresh_output_dir()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=12)
        right = ttk.Frame(self, padding=(0, 12, 12, 12))
        left.grid(row=0, column=0, sticky="nsew")
        right.grid(row=0, column=1, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        header = ttk.Label(
            left,
            text="PDF Queue",
            font=("Segoe UI", 18, "bold"),
        )
        header.grid(row=0, column=0, sticky="w")

        controls = ttk.Frame(left)
        controls.grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.add_files_button = ttk.Button(controls, text="Add Files", command=self.add_files)
        self.add_folder_button = ttk.Button(controls, text="Add Folder", command=self.add_folder)
        self.remove_button = ttk.Button(controls, text="Remove", command=self.remove_selected)
        self.include_button = ttk.Button(
            controls,
            text="Include",
            command=lambda: self.set_selected_included(True),
        )
        self.exclude_button = ttk.Button(
            controls,
            text="Exclude",
            command=lambda: self.set_selected_included(False),
        )
        self.up_button = ttk.Button(
            controls,
            text="Move Up",
            command=lambda: self.move_selected(-1),
        )
        self.down_button = ttk.Button(
            controls,
            text="Move Down",
            command=lambda: self.move_selected(1),
        )
        self.clear_button = ttk.Button(controls, text="Clear", command=self.clear_all)
        buttons = [
            self.add_files_button,
            self.add_folder_button,
            self.remove_button,
            self.include_button,
            self.exclude_button,
            self.up_button,
            self.down_button,
            self.clear_button,
        ]
        for index, button in enumerate(buttons):
            button.grid(row=index // 4, column=index % 4, padx=4, pady=4)

        self.tree = ttk.Treeview(
            left,
            columns=("included", "name", "folder"),
            show="headings",
            height=20,
        )
        self.tree.heading("included", text="Use")
        self.tree.heading("name", text="File")
        self.tree.heading("folder", text="Folder")
        self.tree.column("included", width=60, anchor="center", stretch=False)
        self.tree.column("name", width=220, stretch=True)
        self.tree.column("folder", width=320, stretch=True)
        self.tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._refresh_preview())
        self.tree.bind("<Double-1>", self._toggle_selected_included)

        settings_frame = ttk.LabelFrame(right, text="Run Settings", padding=12)
        settings_frame.grid(row=0, column=0, sticky="ew")
        settings_frame.columnconfigure(1, weight=1)

        text_label_frame = ttk.Frame(settings_frame)
        text_label_frame.grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(text_label_frame, text="Annotation text").grid(row=0, column=0, sticky="w")
        help_label = ttk.Label(
            text_label_frame,
            text="?",
            cursor="question_arrow",
            font=("Segoe UI", 7, "bold"),
        )
        help_label.grid(row=0, column=1, sticky="n", padx=(2, 0), pady=(0, 0))
        Tooltip(
            help_label,
            (
                "Leave empty to skip text and box.\n"
                "Fields: {filename}, {stem}, {index}, {page_number}, {total_pages}"
            ),
        )
        template_entry = ttk.Entry(settings_frame, textvariable=self.annotation_template_var)
        template_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(settings_frame, text="Position").grid(row=1, column=0, sticky="w", pady=4)
        position_box = ttk.Combobox(
            settings_frame,
            state="readonly",
            textvariable=self.position_var,
            values=[
                "top-left",
                "top-center",
                "top-right",
                "bottom-left",
                "bottom-center",
                "bottom-right",
            ],
        )
        position_box.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(settings_frame, text="Font size").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(settings_frame, from_=8, to=48, textvariable=self.font_size_var, width=10).grid(
            row=2,
            column=1,
            sticky="w",
            pady=4,
        )

        ttk.Label(settings_frame, text="Margin").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Spinbox(settings_frame, from_=4, to=96, textvariable=self.margin_var, width=10).grid(
            row=3,
            column=1,
            sticky="w",
            pady=4,
        )

        ttk.Label(settings_frame, text="Box opacity").grid(row=4, column=0, sticky="w", pady=4)
        opacity_scale = ttk.Scale(settings_frame, from_=0.1, to=1.0, variable=self.box_opacity_var)
        opacity_scale.grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(settings_frame, text="Output file").grid(row=5, column=0, sticky="w", pady=4)
        output_entry = ttk.Entry(settings_frame, textvariable=self.output_filename_var)
        output_entry.grid(row=5, column=1, sticky="ew", pady=4)

        ttk.Label(settings_frame, text="Output folder").grid(row=6, column=0, sticky="w", pady=4)
        output_folder_frame = ttk.Frame(settings_frame)
        output_folder_frame.grid(row=6, column=1, sticky="ew", pady=4)
        output_folder_frame.columnconfigure(0, weight=1)
        ttk.Label(
            output_folder_frame,
            textvariable=self.output_dir_var,
            wraplength=240,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        self.output_folder_button = ttk.Button(
            output_folder_frame,
            text="Browse",
            command=self.choose_output_folder,
            width=8,
        )
        self.output_folder_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.default_output_folder_button = ttk.Button(
            output_folder_frame,
            text="Default",
            command=self.use_default_output_folder,
            width=8,
        )
        self.default_output_folder_button.grid(row=0, column=2, sticky="e", padx=(4, 0))

        ttk.Checkbutton(
            settings_frame,
            text="Save intermediate annotated PDFs",
            variable=self.save_intermediate_var,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            settings_frame,
            text="Open output folder after merge",
            variable=self.open_folder_var,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=4)

        preview_frame = ttk.LabelFrame(right, text="Preview", padding=12)
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview_label = ttk.Label(
            preview_frame,
            text="Preview updates from the first selected PDF.",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        actions = ttk.Frame(right, padding=(0, 12, 0, 0))
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        self.progress_bar = ttk.Progressbar(actions, maximum=100, variable=self.progress_var)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.start_button = ttk.Button(actions, text="Start Merge", command=self.start_merge)
        self.cancel_button = ttk.Button(
            actions,
            text="Cancel",
            command=self.cancel_merge,
            state="disabled",
        )
        self.start_button.grid(row=0, column=1, padx=4)
        self.cancel_button.grid(row=0, column=2, padx=4)

        for variable in (
            self.annotation_template_var,
            self.position_var,
            self.font_size_var,
            self.margin_var,
            self.box_opacity_var,
            self.output_filename_var,
        ):
            variable.trace_add("write", lambda *_args: self._on_settings_changed())

    # ------------------------------------------------------------------
    # Settings / output helpers
    # ------------------------------------------------------------------

    def _on_settings_changed(self) -> None:
        self._refresh_output_dir()
        self._refresh_preview()

    def _refresh_output_dir(self) -> None:
        self.output_dir_var.set(str(self._current_output_dir()))

    def _current_output_dir(self) -> Path:
        if self.custom_output_dir is not None:
            return self.custom_output_dir
        return default_output_dir(self.model.get_included_paths())

    # ------------------------------------------------------------------
    # Tree helpers
    # ------------------------------------------------------------------

    def _selected_indices(self) -> list[int]:
        return [int(item_id) for item_id in self.tree.selection()]

    def _refresh_list(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        for index, row in enumerate(self.model.get_display_rows()):
            self.tree.insert("", "end", iid=str(index), values=row)
        self._refresh_output_dir()

    def _set_controls_running(self, running: bool) -> None:
        self.running = running
        state = "disabled" if running else "normal"
        for control in (
            self.add_files_button,
            self.add_folder_button,
            self.remove_button,
            self.include_button,
            self.exclude_button,
            self.up_button,
            self.down_button,
            self.clear_button,
            self.output_folder_button,
            self.default_output_folder_button,
            self.start_button,
        ):
            control.config(state=state)
        self.cancel_button.config(state="normal" if running else "disabled")

    # ------------------------------------------------------------------
    # DnD / file operations
    # ------------------------------------------------------------------

    def _handle_drop(self, event: object) -> None:
        raw_data = getattr(event, "data", "")
        try:
            dropped = [Path(item) for item in self.tk.splitlist(raw_data)]
        except tk.TclError:
            dropped = [Path(raw_data)] if raw_data else []
        self.add_paths(dropped)

    def add_paths(self, paths: list[Path]) -> None:
        added = 0
        for path in paths:
            if path.is_dir():
                added += self.model.add_directory(path)
            else:
                added += self.model.add_files([path])
        self._refresh_list()
        self._refresh_preview()
        if added:
            self.status_var.set(f"Added {added} PDF file(s).")
        else:
            self.status_var.set("No new PDF files were added.")

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        self.add_paths([Path(path) for path in paths])

    def add_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.add_paths([Path(path)])

    def choose_output_folder(self) -> None:
        path = filedialog.askdirectory(initialdir=str(self._current_output_dir()))
        if not path:
            return
        self.custom_output_dir = Path(path).resolve()
        self._refresh_output_dir()
        self.status_var.set(f"Output folder set to {self.custom_output_dir}")

    def use_default_output_folder(self) -> None:
        self.custom_output_dir = None
        self._refresh_output_dir()
        self.status_var.set(f"Output folder reset to {self.output_dir_var.get()}")

    def remove_selected(self) -> None:
        indices = self._selected_indices()
        self.model.remove_indices(indices)
        self._refresh_list()
        self._refresh_preview()

    def set_selected_included(self, included: bool) -> None:
        self.model.set_included(self._selected_indices(), included)
        self._refresh_list()
        self._refresh_preview()

    def _toggle_selected_included(self, _event: object) -> None:
        indices = self._selected_indices()
        if not indices:
            return
        include = not self.model.items[indices[0]].included
        self.model.set_included(indices, include)
        self._refresh_list()
        self.tree.selection_set(*(str(index) for index in indices))
        self._refresh_preview()

    def move_selected(self, direction: int) -> None:
        new_indices = self.model.move(self._selected_indices(), direction)
        self._refresh_list()
        if new_indices:
            self.tree.selection_set(*(str(index) for index in new_indices))
        self._refresh_preview()

    def clear_all(self) -> None:
        self.model.clear()
        self._refresh_list()
        self._refresh_preview()
        self.status_var.set("Selection cleared.")

    # ------------------------------------------------------------------
    # Options builders
    # ------------------------------------------------------------------

    def build_annotation_options(self) -> AnnotationOptions:
        return AnnotationOptions(
            text_template=self.annotation_template_var.get().strip(),
            position=self.position_var.get(),
            font_size=int(self.font_size_var.get()),
            margin=int(self.margin_var.get()),
            box_opacity=float(self.box_opacity_var.get()),
        )

    def build_run_options(self, overwrite: bool) -> RunOptions:
        return RunOptions(
            output_dir=self._current_output_dir(),
            output_filename=self.output_filename_var.get().strip() or "annotated-merged.pdf",
            save_intermediate=self.save_intermediate_var.get(),
            open_folder=self.open_folder_var.get(),
            overwrite=overwrite,
        )

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _first_selected_path(self) -> Path | None:
        indices = self._selected_indices()
        if indices:
            try:
                return self.model.items[indices[0]].path
            except IndexError:
                return None
        included = self.model.get_included_paths()
        return included[0] if included else None

    def _refresh_preview(self) -> None:
        source_path = self._first_selected_path()
        if source_path is None:
            self.preview_image = None
            self.preview_label.configure(
                image="",
                text="Preview updates from the first selected PDF.",
            )
            return
        try:
            png_bytes = render_preview_png(source_path, self.build_annotation_options(), scale=0.6)
            image = tk.PhotoImage(data=base64.b64encode(png_bytes).decode("ascii"))
            self.preview_image = image
            self.preview_label.configure(image=image, text="")
        except Exception as exc:
            self.preview_image = None
            self.preview_label.configure(image="", text=f"Preview unavailable: {exc}")

    # ------------------------------------------------------------------
    # Merge execution
    # ------------------------------------------------------------------

    def start_merge(self) -> None:
        included_paths = self.model.get_included_paths()
        if not included_paths:
            messagebox.showerror("No PDFs selected", "Add at least one PDF file before starting.")
            return

        # Prevent concurrent runs across panels (shared hub-level lock).
        if self._run_lock is not None and not self._run_lock.acquire(blocking=False):
            messagebox.showinfo("Tool busy", "Another tool is already running. Please wait.")
            return

        overwrite = False
        run_options = self.build_run_options(overwrite=False)
        output_path = resolve_output_path(included_paths, run_options)
        if output_path.exists():
            overwrite = messagebox.askyesno(
                "Overwrite output?",
                f"{output_path.name} already exists in:\n{output_path.parent}\n\nOverwrite it?",
            )
            if not overwrite:
                if self._run_lock is not None:
                    self._run_lock.release()
                self.status_var.set("Merge cancelled before start. Output file already exists.")
                return
            run_options = self.build_run_options(overwrite=True)

        self.progress_var.set(0.0)
        self.cancel_event.clear()
        self._set_controls_running(True)
        self.status_var.set("Starting merge...")
        annotation_options = self.build_annotation_options()

        panel = self  # capture ref so hub routes events here even after navigation
        run_lock = self._run_lock

        def worker() -> None:
            try:
                result = process_pdfs(
                    included_paths,
                    annotation_options,
                    run_options,
                    progress_callback=lambda payload: self.event_queue.put(
                        ("progress", payload, panel)
                    ),
                    cancel_event=self.cancel_event,
                )
                self.event_queue.put(("result", result, panel))
            except Exception as exc:
                self.event_queue.put(("error", exc, panel))
            finally:
                if run_lock is not None:
                    run_lock.release()

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def cancel_merge(self) -> None:
        if not self.running:
            return
        self.cancel_event.set()
        self.status_var.set("Cancellation requested...")

    # ------------------------------------------------------------------
    # Event handling (called by hub's drain loop)
    # ------------------------------------------------------------------

    def _handle_event(self, event_type: str, payload: object) -> None:
        if event_type == "progress":
            self._handle_progress(payload)
        elif event_type == "result":
            self._handle_result(payload)
        elif event_type == "error":
            self._handle_error(payload)

    def _handle_progress(self, payload: object) -> None:
        assert isinstance(payload, dict)
        self.status_var.set(str(payload.get("message", "Working...")))
        current_file = int(payload.get("current_file", 0) or 0)
        total_files = int(payload.get("total_files", 0) or 0)
        current_page = int(payload.get("current_page", 0) or 0)
        total_pages = int(payload.get("total_pages", 0) or 0)
        if total_files and current_file:
            base_progress = (current_file - 1) / total_files
            page_progress = (current_page / total_pages) / total_files if total_pages else 0.0
            self.progress_var.set(min((base_progress + page_progress) * 100, 100))

    def _handle_result(self, result: object) -> None:
        self._set_controls_running(False)
        self.progress_var.set(100.0)
        output_dir = getattr(result, "output_dir", None)
        merged_path = getattr(result, "merged_pdf_path", None)
        self.status_var.set(f"Merge complete: {merged_path}")
        if output_dir is not None and self.open_folder_var.get():
            open_output_folder(Path(output_dir))
        messagebox.showinfo("Success", f"Created merged PDF:\n{merged_path}")

    def _handle_error(self, error: object) -> None:
        self._set_controls_running(False)
        self.progress_var.set(0.0)
        if isinstance(error, CancelledError):
            self.status_var.set("Merge cancelled.")
            messagebox.showinfo("Cancelled", "Merge cancelled before completion.")
            return
        self.status_var.set(f"Merge failed: {error}")
        messagebox.showerror("Merge failed", str(error))
