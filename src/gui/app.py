"""Tkinter application for generating the daily Programa workbook."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.pipeline import run
from src.utils.execution_lock import RunAlreadyInProgressError
from src.utils.shared_workspace import SharedWorkspace


class ProgramaApp(ttk.Frame):
    """Simple operator-facing desktop interface for the ETL pipeline."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=18)
        self.master = master
        self.master.title("Programa ETL")
        self.master.minsize(660, 420)
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        default_root = Path.home() / "Documents" / "ProgramaETL"
        self.shared_root = tk.StringVar(value=str(default_root))
        self.pdf_path = tk.StringVar()
        self.word_path = tk.StringVar()
        self.template_path = tk.StringVar()
        self.program_date = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.has_test_train = tk.BooleanVar(value=False)
        self.test_train = tk.StringVar()
        self.test_mr = tk.StringVar()
        self.status = tk.StringVar(value="Selecciona los tres archivos de origen.")
        self._build_form()

    def _build_form(self) -> None:
        self.columnconfigure(1, weight=1)
        ttk.Label(self, text="Generar Programa diario", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )
        self._path_row(1, "Carpeta compartida:", self.shared_root, self._select_shared_folder, "Carpeta")
        self._path_row(2, "Previsión de flota (PDF):", self.pdf_path, self._select_pdf, "Examinar")
        self._path_row(3, "Parte de operaciones (Word):", self.word_path, self._select_word, "Examinar")
        self._path_row(4, "Plantilla Programa (Excel):", self.template_path, self._select_template, "Examinar")

        ttk.Label(self, text="Fecha del Programa (dd/mm/aaaa):").grid(row=5, column=0, sticky="w", pady=(10, 4))
        ttk.Entry(self, textvariable=self.program_date, width=18).grid(row=5, column=1, sticky="w", pady=(10, 4))

        ttk.Checkbutton(self, text="Hay tren de pruebas", variable=self.has_test_train, command=self._toggle_test_fields).grid(
            row=6, column=0, sticky="w", pady=(8, 4)
        )
        self.test_train_entry = ttk.Entry(self, textvariable=self.test_train, width=18, state="disabled")
        self.test_train_entry.grid(row=6, column=1, sticky="w", padx=(0, 8), pady=(8, 4))
        self.test_mr_entry = ttk.Entry(self, textvariable=self.test_mr, width=18, state="disabled")
        self.test_mr_entry.grid(row=6, column=2, sticky="w", pady=(8, 4))
        ttk.Label(self, text="Tren").grid(row=7, column=1, sticky="w")
        ttk.Label(self, text="MR (ej. N001)").grid(row=7, column=2, sticky="w")

        ttk.Button(self, text="Generar Programa", command=self._generate).grid(
            row=8, column=0, columnspan=3, sticky="ew", pady=(18, 8)
        )
        ttk.Label(self, textvariable=self.status, wraplength=610).grid(row=9, column=0, columnspan=3, sticky="w")

    def _path_row(self, row: int, label: str, variable: tk.StringVar, command: object, button_text: str) -> None:
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(self, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 8))
        ttk.Button(self, text=button_text, command=command).grid(row=row, column=2, sticky="ew", pady=4)

    def _select_shared_folder(self) -> None:
        selected = filedialog.askdirectory(title="Selecciona la carpeta compartida")
        if selected:
            self.shared_root.set(selected)

    def _select_pdf(self) -> None:
        self._select_file(self.pdf_path, [("PDF", "*.pdf")])

    def _select_word(self) -> None:
        self._select_file(self.word_path, [("Word", "*.docx")])

    def _select_template(self) -> None:
        self._select_file(self.template_path, [("Excel", "*.xlsx")])

    @staticmethod
    def _select_file(variable: tk.StringVar, filetypes: list[tuple[str, str]]) -> None:
        selected = filedialog.askopenfilename(filetypes=filetypes)
        if selected:
            variable.set(selected)

    def _toggle_test_fields(self) -> None:
        state = "normal" if self.has_test_train.get() else "disabled"
        self.test_train_entry.configure(state=state)
        self.test_mr_entry.configure(state=state)

    def _generate(self) -> None:
        paths = [Path(self.pdf_path.get()), Path(self.word_path.get()), Path(self.template_path.get())]
        if not all(path.is_file() for path in paths):
            messagebox.showerror("Archivos requeridos", "Selecciona un PDF, un Word y una plantilla Excel válidos.")
            return
        try:
            selected_date = datetime.strptime(self.program_date.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Fecha no válida", "Usa el formato dd/mm/aaaa, por ejemplo 10/07/2026.")
            return
        if self.has_test_train.get() and (not self.test_train.get().strip() or not self.test_mr.get().strip()):
            messagebox.showerror("Datos de pruebas", "Captura el número de tren y la matrícula MR.")
            return

        workspace = SharedWorkspace.from_root(Path(self.shared_root.get()).expanduser())
        workspace.ensure_exists()
        output_path = workspace.output_dir / f"Programa_{selected_date:%Y-%m-%d}.xlsx"
        if output_path.exists() and not messagebox.askyesno("Reemplazar archivo", f"Ya existe {output_path.name}. ¿Deseas reemplazarlo?"):
            return
        self.status.set("Procesando archivos; espera un momento...")
        self.master.update_idletasks()
        try:
            result = run(
                pdf_path=paths[0], word_path=paths[1], workbook_path=paths[2], output_path=output_path,
                program_date=selected_date,
                test_train=self.test_train.get().strip() if self.has_test_train.get() else None,
                test_mr=self.test_mr.get().strip() if self.has_test_train.get() else None,
                report_path=workspace.output_dir / f"Reporte_calidad_{selected_date:%Y-%m-%d}.json",
                log_dir=workspace.logs_dir, lock_dir=workspace.output_dir, archive_dir=workspace.archive_dir,
            )
        except RunAlreadyInProgressError:
            messagebox.showwarning("Proceso en curso", "Otra persona ya está generando un Programa. Intenta nuevamente al terminar.")
            self.status.set("No se generó archivo: hay otro proceso en curso.")
        except PermissionError:
            messagebox.showwarning(
                "Archivo en uso",
                "No se pudo guardar el Programa porque está abierto en Excel. "
                "Ciérralo y vuelve a intentar.",
            )
            self.status.set("No se generó archivo: el Programa está abierto en Excel.")
        except Exception as error:
            messagebox.showerror("No se pudo generar", str(error))
            self.status.set("No se generó archivo. Consulta el reporte de calidad y los registros.")
        else:
            messagebox.showinfo("Programa generado", f"Archivo creado:\n{result.output_path}")
            self.status.set(f"Programa generado correctamente: {result.output_path.name}")


def main() -> None:
    root = tk.Tk()
    ProgramaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
