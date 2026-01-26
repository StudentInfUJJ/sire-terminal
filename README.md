# SIRE Terminal 🛂

Herramienta de escritorio para convertir archivos **Police Report** al formato requerido por **SIRE** (Sistema de Información para el Reporte de Extranjeros) de Migración Colombia.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Características

- 🔍 **Detección inteligente de columnas** - Reconoce automáticamente los campos del Police Report
- 🌎 **249 códigos de países** - Base de datos oficial de Migración Colombia
- 🏙️ **Ciudades colombianas** - Detecta destinos locales automáticamente
- 📊 **Múltiples formatos** - Excel (.xlsx, .xls), CSV y TXT
- 🎨 **Interfaz moderna** - GUI oscura estilo terminal
- ⚡ **Portable** - No requiere instalación

## Descarga

| Sistema | Descargar |
|---------|-----------|
| Windows | [SIRE_Terminal.exe](../../releases/latest) |
| macOS | [SIRE_Terminal](../../releases/latest) |

## Uso

1. Ejecutar `SIRE_Terminal.exe` (Windows) o `SIRE_Terminal` (macOS)
2. Seleccionar archivo Police Report
3. Ingresar código del establecimiento
4. Ingresar código de ciudad (default: 5001 = Medellín)
5. Seleccionar tipo de movimiento (Entrada/Salida)
6. Clic en **PROCESAR REGISTRO**
7. Clic en **EXTRAER ARCHIVO SIRE**

## Formato de salida

El archivo generado contiene 13 campos separados por TAB:

```
Código Hotel | Ciudad | Tipo Doc | Número Doc | Nacionalidad | Apellido 1 | Apellido 2 | Nombres | Movimiento | Fecha Mov | Procedencia | Destino | Fecha Nac
```

## Requisitos del sistema

- **Windows**: Windows 10/11 (64-bit)
- **macOS**: macOS 10.14+ (Intel o Apple Silicon)

## Compilar desde código fuente

```bash
# Clonar repositorio
git clone https://github.com/jihadz14/sire-terminal.git
cd sire-terminal

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python sire_terminal.py
```

## Tecnologías

- Python 3.9+
- CustomTkinter (GUI)
- Pandas (procesamiento de datos)
- Nuitka (compilación)

---

Desarrollado por **E.Herrera** | Colombia 🇨🇴
