"""
Example App - Demo para el workflow de compilación
Esta es una app de ejemplo para demostrar el build multiplataforma.
"""

import customtkinter as ctk
from datetime import datetime
import platform

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ExampleApp(ctk.CTk):
    """App de ejemplo con CustomTkinter."""

    def __init__(self):
        super().__init__()

        self.title("Example App - Cross Platform Build Demo")
        self.geometry("500x400")
        self.configure(fg_color="#1a1a2e")

        # Header
        ctk.CTkLabel(
            self,
            text="🔧 Cross-Platform Build Demo",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#e94560"
        ).pack(pady=30)

        # Info del sistema
        info_frame = ctk.CTkFrame(self, fg_color="#16213e")
        info_frame.pack(padx=40, pady=20, fill="x")

        ctk.CTkLabel(
            info_frame,
            text=f"Sistema: {platform.system()} {platform.release()}",
            font=ctk.CTkFont(size=14),
            text_color="#a0a0a0"
        ).pack(pady=10)

        ctk.CTkLabel(
            info_frame,
            text=f"Python: {platform.python_version()}",
            font=ctk.CTkFont(size=14),
            text_color="#a0a0a0"
        ).pack(pady=5)

        ctk.CTkLabel(
            info_frame,
            text=f"Arquitectura: {platform.machine()}",
            font=ctk.CTkFont(size=14),
            text_color="#a0a0a0"
        ).pack(pady=10)

        # Botón interactivo
        self.click_count = 0
        self.btn = ctk.CTkButton(
            self,
            text="Clic aquí: 0",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#e94560",
            hover_color="#b8374a",
            height=50,
            command=self.on_click
        )
        self.btn.pack(pady=30)

        # Hora actual
        self.time_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Courier", size=12),
            text_color="#505050"
        )
        self.time_label.pack(pady=10)
        self.update_time()

        # Footer
        ctk.CTkLabel(
            self,
            text="Compilado con Nuitka + GitHub Actions",
            font=ctk.CTkFont(size=10),
            text_color="#404040"
        ).pack(side="bottom", pady=15)

    def on_click(self):
        self.click_count += 1
        self.btn.configure(text=f"Clic aquí: {self.click_count}")

    def update_time(self):
        self.time_label.configure(
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.after(1000, self.update_time)


if __name__ == "__main__":
    app = ExampleApp()
    app.mainloop()
