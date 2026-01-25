"""
SIRE TERMINAL v3.0 - Sistema de Registro de Extranjeros
Interfaz de Control Migratorio con estética Passport Terminal

Convierte archivos Police Report al formato requerido por SIRE
(Migración Colombia)

Características v3.0:
- Motor de detección inteligente de columnas
- Inferencia automática de campos faltantes
- Sistema de confianza para cada campo
- Validación robusta de datos
- Logs detallados con campos faltantes
- UI responsive
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
import os
import time
import subprocess
from typing import Dict
import threading

# Importar el motor de conversión v3.0
from sire_converter import SireConverter

# Configuración de tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta de colores "Passport Terminal"
COLORS = {
    "bg_dark": "#0a0f1a",
    "bg_panel": "#111827",
    "bg_input": "#1e293b",
    "accent_gold": "#d4a574",
    "accent_blue": "#3b82f6",
    "accent_green": "#10b981",
    "accent_red": "#ef4444",
    "accent_yellow": "#f59e0b",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border": "#334155",
    "stamp_red": "#dc2626",
}


class StampWidget(ctk.CTkFrame):
    """Widget de sello de pasaporte con animación estilo stamp - Optimizado."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.stamp_visible = False
        self.movement_type = "E"
        self.stamp_date = ""  # Inicializar para evitar AttributeError
        self.animation_step = 0
        self.animation_id = None
        self.resize_id = None
        self.size = 180
        self._last_resize_time = 0
        self._canvas_items = {}  # Cache de items del canvas

        self.canvas = ctk.CTkCanvas(
            self, width=self.size, height=self.size,
            bg=COLORS["bg_panel"], highlightthickness=0
        )
        self.canvas.pack(expand=True, fill="both")
        self._init_canvas_items()
        self._draw_empty_state()

        # Bind resize con throttle inteligente
        self.bind("<Configure>", self._on_resize_throttled)

    def _init_canvas_items(self):
        """Pre-crea items del canvas para reutilizar (evita delete/create)."""
        # Items para estado vacío
        self._canvas_items['empty_lines'] = []
        for i in range(5):
            item = self.canvas.create_line(0, 0, 0, 0, fill=COLORS["border"], dash=(4, 4), state='hidden')
            self._canvas_items['empty_lines'].append(item)
        self._canvas_items['empty_text'] = self.canvas.create_text(0, 0, text="SIRE",
            font=("Courier", 20, "bold"), fill=COLORS["text_muted"], state='hidden')

        # Items para sello
        self._canvas_items['outer_circle'] = self.canvas.create_oval(0, 0, 0, 0, outline="", width=3, state='hidden')
        self._canvas_items['inner_circle'] = self.canvas.create_oval(0, 0, 0, 0, outline="", width=2, state='hidden')
        self._canvas_items['text_colombia'] = self.canvas.create_text(0, 0, text="COLOMBIA",
            font=("Courier", 10, "bold"), fill="", state='hidden')
        self._canvas_items['text_tipo'] = self.canvas.create_text(0, 0, text="",
            font=("Courier", 13, "bold"), fill="", state='hidden')
        self._canvas_items['text_date'] = self.canvas.create_text(0, 0, text="",
            font=("Courier", 10), fill="", state='hidden')
        self._canvas_items['text_sire'] = self.canvas.create_text(0, 0, text="SIRE",
            font=("Courier", 11, "bold"), fill="", state='hidden')

    def _on_resize_throttled(self, event):
        """Throttle inteligente: responde rápido pero evita saturación."""
        current_time = time.time() * 1000  # ms

        # Si está en animación, ignorar resize
        if self.animation_id:
            return

        # Throttle de 16ms (~60fps) durante resize activo
        if current_time - self._last_resize_time < 16:
            if self.resize_id:
                self.after_cancel(self.resize_id)
            self.resize_id = self.after(16, lambda: self._on_resize(event))
            return

        self._last_resize_time = current_time
        self._on_resize(event)

    def _on_resize(self, event):
        """Ajusta el tamaño del canvas al redimensionar - Optimizado."""
        new_size = min(event.width, event.height, 200)
        if abs(new_size - self.size) > 3 and new_size > 50:
            self.size = new_size
            # Usar after_idle para que el canvas se actualice en el próximo ciclo idle
            self.after_idle(self._update_canvas_size)

    def _update_canvas_size(self):
        """Actualiza el canvas de forma diferida."""
        self.canvas.configure(width=self.size, height=self.size)
        if self.stamp_visible:
            self._update_stamp_positions(1.0)
        else:
            self._update_empty_positions()

    def _hide_all_items(self):
        """Oculta todos los items del canvas."""
        for key, item in self._canvas_items.items():
            if isinstance(item, list):
                for i in item:
                    self.canvas.itemconfigure(i, state='hidden')
            else:
                self.canvas.itemconfigure(item, state='hidden')

    def _draw_empty_state(self):
        """Muestra estado vacío reutilizando items existentes."""
        self._hide_all_items()
        self._update_empty_positions()

        # Mostrar items de estado vacío
        for item in self._canvas_items['empty_lines']:
            self.canvas.itemconfigure(item, state='normal')
        self.canvas.itemconfigure(self._canvas_items['empty_text'], state='normal')

    def _update_empty_positions(self):
        """Actualiza posiciones de items vacíos sin recrearlos."""
        center = self.size // 2
        for i, item in enumerate(self._canvas_items['empty_lines']):
            y = center - 40 + i * 20
            self.canvas.coords(item, 20, y, self.size - 20, y)
        self.canvas.coords(self._canvas_items['empty_text'], center, center)

    def _draw_stamp(self, scale: float = 1.0):
        """Dibuja el sello actualizando items existentes."""
        self._hide_all_items()
        self._update_stamp_positions(scale)

        stamp_color = COLORS["accent_green"] if self.movement_type == "E" else COLORS["accent_red"]

        # Actualizar colores y mostrar items del sello
        self.canvas.itemconfigure(self._canvas_items['outer_circle'], outline=stamp_color, state='normal')
        self.canvas.itemconfigure(self._canvas_items['inner_circle'], outline=stamp_color, state='normal')
        self.canvas.itemconfigure(self._canvas_items['text_colombia'], fill=stamp_color, state='normal')

        tipo_text = "ENTRADA" if self.movement_type == "E" else "SALIDA"
        self.canvas.itemconfigure(self._canvas_items['text_tipo'], text=tipo_text, fill=stamp_color, state='normal')

        if self.stamp_date:
            self.canvas.itemconfigure(self._canvas_items['text_date'], text=self.stamp_date, fill=stamp_color, state='normal')

        self.canvas.itemconfigure(self._canvas_items['text_sire'], fill=stamp_color, state='normal')

    def _update_stamp_positions(self, scale: float):
        """Actualiza posiciones del sello sin recrear items."""
        center = self.size // 2
        base_r = min(70, self.size // 3)
        outer_r = int(base_r * scale)
        inner_r = int(base_r * 0.8 * scale)

        # Actualizar círculos
        self.canvas.coords(self._canvas_items['outer_circle'],
            center - outer_r, center - outer_r, center + outer_r, center + outer_r)
        self.canvas.coords(self._canvas_items['inner_circle'],
            center - inner_r, center - inner_r, center + inner_r, center + inner_r)

        # Actualizar textos
        font_size = max(8, int(10 * scale * self.size / 180))
        self.canvas.coords(self._canvas_items['text_colombia'], center, center - base_r * 0.55 * scale)
        self.canvas.itemconfigure(self._canvas_items['text_colombia'], font=("Courier", font_size, "bold"))

        self.canvas.coords(self._canvas_items['text_tipo'], center, center - base_r * 0.15 * scale)
        self.canvas.itemconfigure(self._canvas_items['text_tipo'], font=("Courier", int(font_size * 1.3), "bold"))

        self.canvas.coords(self._canvas_items['text_date'], center, center + base_r * 0.2 * scale)
        self.canvas.itemconfigure(self._canvas_items['text_date'], font=("Courier", font_size))

        self.canvas.coords(self._canvas_items['text_sire'], center, center + base_r * 0.55 * scale)
        self.canvas.itemconfigure(self._canvas_items['text_sire'], font=("Courier", int(font_size * 1.1), "bold"))

    def _animate_stamp(self):
        """Animación de sello con efecto bounce - Optimizado."""
        animation_frames = [2.5, 2.0, 1.5, 1.2, 1.0, 0.92, 1.0, 0.96, 1.0]

        if self.animation_step < len(animation_frames):
            scale = animation_frames[self.animation_step]
            self._draw_stamp(scale)
            self.animation_step += 1
            delay = 25 if self.animation_step < 5 else 40  # Más rápido
            self.animation_id = self.after(delay, self._animate_stamp)
        else:
            self._draw_stamp(1.0)
            self.animation_step = 0
            self.animation_id = None

    def show_stamp(self, movement_type: str = "E", date: str = ""):
        """Muestra el sello con animación."""
        if self.animation_id:
            self.after_cancel(self.animation_id)
            self.animation_id = None

        self.movement_type = movement_type
        self.stamp_date = date
        self.stamp_visible = True
        self.animation_step = 0
        self._animate_stamp()

    def reset(self):
        """Resetea el sello al estado vacío."""
        if self.animation_id:
            self.after_cancel(self.animation_id)
            self.animation_id = None

        self.stamp_visible = False
        self.animation_step = 0
        self._draw_empty_state()

    def destroy(self):
        """Limpia recursos antes de destruir el widget."""
        if self.animation_id:
            self.after_cancel(self.animation_id)
        if self.resize_id:
            self.after_cancel(self.resize_id)
        super().destroy()


class SireTerminal(ctk.CTk):
    """Interfaz principal del terminal SIRE - Optimizada para fluidez."""

    def __init__(self):
        super().__init__()

        self.title("SIRE TERMINAL v3.0 | Control Migratorio")
        self.geometry("1100x750")
        self.minsize(800, 600)
        self.configure(fg_color=COLORS["bg_dark"])

        self.file_path = ctk.StringVar()
        self.hotel_code = ctk.StringVar()
        self.city_code = ctk.StringVar(value="5001")
        self.movement_type = ctk.StringVar(value="E")
        self.output_lines = []
        self.converter = None

        # Optimización: batch de logs pendientes
        self._pending_logs = []
        self._log_flush_id = None

        # Optimización: throttle de resize principal
        self._main_resize_id = None
        self._last_main_resize = 0

        # Configurar grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_ui()
        self._update_datetime()

        # Bind resize optimizado para ventana principal
        self.bind("<Configure>", self._on_main_resize)

    def _create_ui(self):
        self._create_header()
        self._create_main_content()
        self._create_footer()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        header.grid_columnconfigure(1, weight=1)

        # Logo y título
        left_frame = ctk.CTkFrame(header, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=15, pady=12)

        ctk.CTkLabel(
            left_frame, text="SIRE TERMINAL",
            font=ctk.CTkFont(family="Courier", size=24, weight="bold"),
            text_color=COLORS["accent_gold"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            left_frame, text="Sistema Integrado de Registro de Extranjeros v3.0",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]
        ).pack(anchor="w")

        # Estado y fecha
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="e", padx=15, pady=12)

        status_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        status_frame.pack(anchor="e")

        ctk.CTkLabel(status_frame, text="●", font=ctk.CTkFont(size=10),
                    text_color=COLORS["accent_green"]).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(status_frame, text="ACTIVO", font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"]).pack(side="left")

        self.datetime_label = ctk.CTkLabel(
            right_frame, text="", font=ctk.CTkFont(family="Courier", size=12),
            text_color=COLORS["text_muted"]
        )
        self.datetime_label.pack(anchor="e", pady=(3, 0))

    def _create_main_content(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

        # Configurar 3 columnas: input | stamp | output
        main.grid_columnconfigure(0, weight=2, minsize=280)
        main.grid_columnconfigure(1, weight=0, minsize=180)
        main.grid_columnconfigure(2, weight=3, minsize=320)
        main.grid_rowconfigure(0, weight=1)

        self._create_input_panel(main)
        self._create_stamp_panel(main)
        self._create_output_panel(main)

    def _create_input_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=8)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(panel, fg_color=COLORS["bg_input"], corner_radius=6)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        ctk.CTkLabel(header, text="01", font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
                    text_color=COLORS["accent_gold"]).pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(header, text="DATOS DE ENTRADA", font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=COLORS["text_primary"]).pack(side="left", pady=8)

        # Content con scroll
        content = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=5)
        content.grid_columnconfigure(0, weight=1)

        # Archivo
        self._create_label(content, "ARCHIVO POLICE REPORT")
        file_frame = ctk.CTkFrame(content, fg_color=COLORS["bg_input"], corner_radius=6)
        file_frame.grid(row=1, column=0, sticky="ew", pady=(3, 12))
        file_frame.grid_columnconfigure(0, weight=1)

        self.file_label = ctk.CTkLabel(file_frame, text="Seleccione un archivo...",
                                       font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
                                       wraplength=200)
        self.file_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        ctk.CTkButton(file_frame, text="EXAMINAR", font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color=COLORS["accent_blue"], hover_color="#2563eb",
                     height=32, command=self._browse_file).grid(row=1, column=0, padx=10, pady=(0, 10))

        # Código establecimiento
        self._create_label(content, "CÓDIGO ESTABLECIMIENTO", row=2)
        entry1 = ctk.CTkEntry(content, textvariable=self.hotel_code,
                    font=ctk.CTkFont(family="Courier", size=13),
                    fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                    height=38, placeholder_text="Ej: 110031")
        entry1.grid(row=3, column=0, sticky="ew", pady=(3, 12))

        # Código ciudad
        self._create_label(content, "CÓDIGO CIUDAD", row=4)
        entry2 = ctk.CTkEntry(content, textvariable=self.city_code,
                    font=ctk.CTkFont(family="Courier", size=13),
                    fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                    height=38, placeholder_text="Ej: 5001")
        entry2.grid(row=5, column=0, sticky="ew", pady=(3, 12))

        # Tipo de movimiento
        self._create_label(content, "TIPO DE MOVIMIENTO", row=6)
        mov_frame = ctk.CTkFrame(content, fg_color="transparent")
        mov_frame.grid(row=7, column=0, sticky="ew", pady=(3, 12))
        mov_frame.grid_columnconfigure(0, weight=1)
        mov_frame.grid_columnconfigure(1, weight=1)

        self.btn_entrada = ctk.CTkButton(
            mov_frame, text="⬇ ENTRADA", font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_green"], hover_color="#059669", height=40,
            command=lambda: self._set_movement("E")
        )
        self.btn_entrada.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_salida = ctk.CTkButton(
            mov_frame, text="⬆ SALIDA", font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["bg_input"], hover_color=COLORS["accent_red"],
            border_color=COLORS["border"], border_width=1, height=40,
            command=lambda: self._set_movement("S")
        )
        self.btn_salida.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Botón procesar
        self.process_btn = ctk.CTkButton(
            panel, text="▶  PROCESAR REGISTRO",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_gold"], hover_color="#b8956a",
            text_color=COLORS["bg_dark"], height=45, corner_radius=6,
            command=self._process
        )
        self.process_btn.grid(row=2, column=0, sticky="ew", padx=12, pady=12)

    def _create_stamp_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=8)
        panel.grid(row=0, column=1, sticky="nsew", padx=8)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text="SELLO", font=ctk.CTkFont(family="Courier", size=11),
                    text_color=COLORS["text_muted"]).grid(row=0, column=0, pady=(12, 5))

        self.stamp_widget = StampWidget(panel)
        self.stamp_widget.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 15))

    def _create_output_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=8)
        panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(panel, fg_color=COLORS["bg_input"], corner_radius=6)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        ctk.CTkLabel(header, text="02", font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
                    text_color=COLORS["accent_gold"]).pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(header, text="RESULTADO", font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=COLORS["text_primary"]).pack(side="left", pady=8)

        # Stats
        self.stats_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=5)
        self.stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_labels = {}
        for i, (key, label, color) in enumerate([
            ("total", "TOTAL", COLORS["text_secondary"]),
            ("valid", "VÁLIDOS", COLORS["accent_green"]),
            ("skipped", "OMITIDOS", COLORS["accent_yellow"]),
            ("colombianos", "COL", COLORS["accent_blue"])
        ]):
            card = ctk.CTkFrame(self.stats_frame, fg_color=COLORS["bg_input"], corner_radius=6)
            card.grid(row=0, column=i, sticky="ew", padx=2)

            val_label = ctk.CTkLabel(card, text="0",
                                     font=ctk.CTkFont(family="Courier", size=18, weight="bold"),
                                     text_color=color)
            val_label.pack(pady=(8, 0))
            self.stat_labels[key] = val_label

            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=8),
                        text_color=COLORS["text_muted"]).pack(pady=(0, 8))

        # Console
        console_frame = ctk.CTkFrame(panel, fg_color=COLORS["bg_input"], corner_radius=6)
        console_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        console_frame.grid_rowconfigure(1, weight=1)
        console_frame.grid_columnconfigure(0, weight=1)

        console_header = ctk.CTkFrame(console_frame, fg_color=COLORS["bg_dark"], corner_radius=4)
        console_header.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        for color in ["#ef4444", "#f59e0b", "#10b981"]:
            ctk.CTkLabel(console_header, text="●", font=ctk.CTkFont(size=7),
                        text_color=color).pack(side="left", padx=(6, 1), pady=4)

        ctk.CTkLabel(console_header, text="Terminal", font=ctk.CTkFont(size=9),
                    text_color=COLORS["text_muted"]).pack(side="left", padx=8)

        self.console = ctk.CTkTextbox(
            console_frame, font=ctk.CTkFont(family="Courier", size=11),
            fg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"],
            wrap="word", corner_radius=0
        )
        self.console.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.console.insert("end", "SIRE Terminal v3.0\n")
        self.console.insert("end", "Motor de detección inteligente activo\n")
        self.console.insert("end", "Esperando archivo de entrada...\n")
        self.console.configure(state="disabled")

        # Botón descargar
        self.download_btn = ctk.CTkButton(
            panel, text="⬇  EXTRAER ARCHIVO SIRE",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_green"], hover_color="#059669",
            height=42, corner_radius=6, command=self._download
        )

    def _create_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 10))
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(footer, text="MIGRACIÓN COLOMBIA  |  SIRE",
                    font=ctk.CTkFont(size=9), text_color=COLORS["text_muted"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(footer, text="by E.Herrera",
                    font=ctk.CTkFont(size=9, slant="italic"), text_color=COLORS["accent_gold"]).grid(row=0, column=1)
        ctk.CTkLabel(footer, text="v3.0.0", font=ctk.CTkFont(family="Courier", size=9),
                    text_color=COLORS["text_muted"]).grid(row=0, column=2, sticky="e")

    def _create_label(self, parent, text, row=None):
        label = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=COLORS["text_secondary"])
        if row is not None:
            label.grid(row=row, column=0, sticky="w", pady=(0, 0))
        else:
            label.grid(row=0, column=0, sticky="w", pady=(0, 0))

    def _update_datetime(self):
        self.datetime_label.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.after(1000, self._update_datetime)

    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Police Report",
            filetypes=[("Archivos soportados", "*.txt *.xlsx *.xls *.csv"),
                      ("Texto", "*.txt"), ("Excel", "*.xlsx *.xls"), ("CSV", "*.csv")]
        )
        if file_path:
            self._reset_for_new_file()
            self.file_path.set(file_path)
            filename = os.path.basename(file_path)
            display_name = filename if len(filename) < 25 else filename[:22] + "..."
            self.file_label.configure(text=f"✓ {display_name}", text_color=COLORS["accent_green"])
            self._log(f"Archivo cargado: {filename}")

    def _reset_for_new_file(self):
        """Resetea logs, sello y estadísticas para un nuevo archivo."""
        self.stamp_widget.reset()

        for key in self.stat_labels:
            self.stat_labels[key].configure(text="0")

        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.insert("end", "SIRE Terminal v3.0\n")
        self.console.insert("end", "Motor de detección inteligente activo\n")
        self.console.insert("end", "─" * 40 + "\n")
        self.console.configure(state="disabled")

        self.download_btn.grid_forget()
        self.output_lines = []
        self.converter = None

    def _set_movement(self, movement: str):
        self.movement_type.set(movement)
        if movement == "E":
            self.btn_entrada.configure(fg_color=COLORS["accent_green"])
            self.btn_salida.configure(fg_color=COLORS["bg_input"])
        else:
            self.btn_entrada.configure(fg_color=COLORS["bg_input"])
            self.btn_salida.configure(fg_color=COLORS["accent_red"])
        self.stamp_widget.reset()

    def _on_main_resize(self, event):
        """Throttle del resize principal para mejor rendimiento."""
        # Solo procesar eventos de la ventana principal
        if event.widget != self:
            return

        current_time = time.time() * 1000

        # Throttle de 32ms durante resize activo
        if current_time - self._last_main_resize < 32:
            if self._main_resize_id:
                self.after_cancel(self._main_resize_id)
            self._main_resize_id = self.after(32, lambda: self._do_main_resize(event))
            return

        self._last_main_resize = current_time

    def _do_main_resize(self, event):
        """Ejecuta el resize de forma diferida."""
        self._main_resize_id = None
        self.update_idletasks()

    def _log(self, message: str, log_type: str = "info"):
        """Log con batching para mejor rendimiento."""
        prefix = {"info": "►", "success": "✓", "error": "✗", "warn": "⚠", "detail": "  "}
        formatted = f"{prefix.get(log_type, '►')} {message}\n"
        self._pending_logs.append(formatted)

        # Flush diferido para agrupar múltiples logs
        if self._log_flush_id is None:
            self._log_flush_id = self.after_idle(self._flush_logs)

    def _flush_logs(self):
        """Escribe todos los logs pendientes de una vez."""
        self._log_flush_id = None
        if not self._pending_logs:
            return

        self.console.configure(state="normal")
        for log in self._pending_logs:
            self.console.insert("end", log)
        self._pending_logs.clear()
        self.console.see("end")
        self.console.configure(state="disabled")

    def _process(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Seleccione un archivo Police Report")
            return
        if not self.hotel_code.get():
            messagebox.showerror("Error", "Ingrese el código del establecimiento")
            return
        if not self.city_code.get():
            messagebox.showerror("Error", "Ingrese el código de ciudad")
            return

        self.process_btn.configure(state="disabled", text="PROCESANDO...")
        self._log("Iniciando conversión con motor v3.0...", "info")

        thread = threading.Thread(target=self._do_process, daemon=True)
        thread.start()

    def _do_process(self):
        """Procesa el archivo en thread separado con UI updates optimizados."""
        try:
            self.converter = SireConverter(
                hotel_code=self.hotel_code.get(),
                city_code=self.city_code.get()
            )

            df = self.converter.read_file(self.file_path.get())

            # Agrupar logs iniciales en un solo update
            def log_initial():
                self._log(f"Registros leídos: {len(df)}")
                self._log("Columnas detectadas:", "info")
                if hasattr(self.converter, 'column_map'):
                    for field, (col, conf) in self.converter.column_map.items():
                        self._log(f"  {field} → {col}", "detail")
            self.after_idle(log_initial)

            lines, stats = self.converter.convert(df, self.movement_type.get())
            self.output_lines = lines

            # Usar after_idle para mejor integración con el event loop
            self.after_idle(lambda: self._update_results(stats))

        except Exception as e:
            def handle_error():
                self._log(f"Error: {str(e)}", "error")
                self.process_btn.configure(state="normal", text="▶  PROCESAR REGISTRO")
            self.after_idle(handle_error)

    def _update_results(self, stats: Dict):
        """Actualiza resultados con optimización de batch."""
        # Actualizar stats en batch usando after_idle
        def update_stats():
            for key, value in stats.items():
                if key in self.stat_labels:
                    self.stat_labels[key].configure(text=str(value))
        self.after_idle(update_stats)

        # Logs agrupados (el batching se encarga de escribirlos juntos)
        self._log(f"Total procesados: {stats['total']}", "info")
        self._log(f"Registros válidos: {stats['valid']}", "success")

        if stats.get('inferidos', 0) > 0:
            self._log(f"Campos inferidos automáticamente: {stats['inferidos']}", "info")

        if stats['colombianos'] > 0:
            self._log(f"Colombianos excluidos (SIRE es para extranjeros): {stats['colombianos']}", "info")

        if stats.get('duplicados', 0) > 0:
            self._log(f"Duplicados removidos: {stats['duplicados']}", "warn")

        if stats['skipped'] > 0:
            self._log(f"Registros omitidos: {stats['skipped']}", "warn")

            if self.converter and self.converter.errors:
                self._log("Detalle de errores:", "warn")
                # Limitar errores mostrados para no saturar
                for err in self.converter.errors[:10]:
                    self._log(err, "detail")
                if len(self.converter.errors) > 10:
                    self._log(f"  ... y {len(self.converter.errors) - 10} errores más", "detail")

        if self.converter and self.converter.warnings:
            self._log("Advertencias:", "warn")
            for warn in self.converter.warnings[:5]:
                self._log(warn, "detail")
            if len(self.converter.warnings) > 5:
                self._log(f"  ... y {len(self.converter.warnings) - 5} advertencias más", "detail")

        # Mostrar sello con pequeño delay para que los logs se rendericen primero
        def show_stamp_delayed():
            date = datetime.now().strftime("%d/%m/%Y")
            self.stamp_widget.show_stamp(self.movement_type.get(), date)
        self.after(50, show_stamp_delayed)

        if stats['valid'] > 0:
            self.download_btn.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
            self._log("¡Archivo listo para extraer!", "success")
        else:
            self._log("No se generaron registros válidos", "error")

        self.process_btn.configure(state="normal", text="▶  PROCESAR REGISTRO")

    def _download(self):
        if not self.output_lines:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"reporte_sire_{timestamp}.txt"

        # Obtener ruta del Desktop (compatible con OneDrive y rutas personalizadas)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            # Fallback: usar directorio del usuario
            desktop = os.path.expanduser("~")

        file_path = os.path.join(desktop, filename)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.output_lines))

            self._log(f"Archivo extraído: {filename}", "success")

            # Abrir Explorer y seleccionar archivo (sin shell=True para seguridad)
            subprocess.Popen(['explorer', '/select,', file_path])

        except Exception as e:
            self._log(f"Error al guardar: {str(e)}", "error")
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {str(e)}")

    def destroy(self):
        """Limpia recursos antes de cerrar la aplicación."""
        # Cancelar callbacks pendientes
        if self._log_flush_id:
            self.after_cancel(self._log_flush_id)
        if self._main_resize_id:
            self.after_cancel(self._main_resize_id)
        super().destroy()


if __name__ == "__main__":
    app = SireTerminal()
    app.mainloop()
