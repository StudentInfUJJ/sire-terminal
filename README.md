# Cross-Platform Python App Builder 🔧

GitHub Actions workflow para **compilar aplicaciones Python** en **Windows y macOS** simultáneamente usando **Nuitka**.

![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF.svg)
![Nuitka](https://img.shields.io/badge/Nuitka-Compiler-orange.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)

## ¿Qué hace?

- ✅ Compila tu app Python a **ejecutable nativo** (no necesita Python instalado)
- ✅ Genera binarios para **Windows (.exe)** y **macOS** automáticamente
- ✅ Build en la nube gratis (GitHub Actions)
- ✅ Más pequeño y rápido que PyInstaller

## Cómo usar este template

### 1. Copia el workflow

Copia `.github/workflows/build.yml` a tu repositorio.

### 2. Ajusta el archivo principal

Edita el workflow y cambia `sire_terminal.py` por tu archivo principal:

```yaml
sire_terminal.py  →  tu_app.py
```

### 3. Ajusta las dependencias

Modifica el paso "Instalar dependencias":

```yaml
pip install nuitka customtkinter pandas openpyxl pillow
```

### 4. Push y listo

```bash
git push
```

GitHub compilará automáticamente para ambas plataformas.

## Estructura del workflow

```yaml
Jobs:
  ├── build (windows-latest)  → SIRE_Terminal.exe
  └── build (macos-latest)    → SIRE_Terminal
```

## Ventajas vs PyInstaller

| Característica | Nuitka | PyInstaller |
|---------------|--------|-------------|
| Tamaño | ~30-60 MB | ~150-250 MB |
| Velocidad | Más rápido | Normal |
| Compilación | A código C | Empaquetado |
| Anti-virus | Menos falsos positivos | Más detecciones |

## Requisitos

- Repositorio público (builds ilimitados gratis)
- O privado (2,000 min/mes gratis)

## Tiempo de build

| Plataforma | Tiempo aprox. |
|------------|---------------|
| Windows | 40-60 min |
| macOS | 25-35 min |

## Descargar ejecutables

Después del build, descarga desde **Actions → Artifacts** o crea un Release.

---

by **E.Herrera** 🇨🇴
