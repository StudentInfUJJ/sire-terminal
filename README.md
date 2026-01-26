# Cross-Platform Python App Builder 🔧

GitHub Actions workflow para **compilar aplicaciones Python** en **Windows y macOS** simultáneamente usando **Nuitka**.

![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Ready-2088FF.svg)
![Nuitka](https://img.shields.io/badge/Nuitka-Compiler-orange.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)

## ¿Qué hace?

- ✅ Compila tu app Python a **ejecutable nativo** (no necesita Python instalado)
- ✅ Genera binarios para **Windows (.exe)** y **macOS** automáticamente
- ✅ Build en la nube gratis con GitHub Actions
- ✅ Más pequeño y rápido que PyInstaller

## Cómo usar este template

### 1. Fork o copia este repositorio

### 2. Reemplaza `example_app.py` con tu aplicación

### 3. Edita el workflow (`.github/workflows/build.yml`)

Cambia el nombre del archivo y del ejecutable:

```yaml
# Línea 58 y 74: cambia example_app.py por tu archivo
example_app.py  →  mi_app.py

# Líneas 17-22: cambia nombres de artifacts
artifact_name: MiApp.exe
asset_name: MiApp_Windows.exe
```

### 4. Ajusta las dependencias

Si tu app usa librerías adicionales, agrégalas en el paso "Instalar dependencias":

```yaml
pip install nuitka customtkinter pillow TU_LIBRERIA
```

Y en el build:

```yaml
--include-package=TU_LIBRERIA
```

### 5. Push y listo

```bash
git push
```

GitHub compilará automáticamente para ambas plataformas (~15-30 min).

## Estructura del proyecto

```
├── .github/workflows/
│   └── build.yml          # Workflow de GitHub Actions
├── example_app.py         # App de ejemplo (reemplazar)
├── requirements.txt       # Dependencias Python
└── README.md
```

## Ventajas de Nuitka vs PyInstaller

| Característica | Nuitka | PyInstaller |
|---------------|--------|-------------|
| Tamaño ejecutable | ~20-60 MB | ~100-250 MB |
| Velocidad ejecución | Más rápido | Normal |
| Método | Compila a C | Empaqueta bytecode |
| Falsos positivos antivirus | Menos | Más frecuentes |

## Límites de GitHub Actions

| Tipo de repo | Minutos gratis/mes |
|--------------|-------------------|
| **Público** | ∞ Ilimitado |
| Privado | 2,000 min |

## Tiempo de build aproximado

| Plataforma | Tiempo |
|------------|--------|
| Windows | 15-40 min |
| macOS | 10-25 min |

## Descargar ejecutables

Después del build:
1. Ve a **Actions** en tu repo
2. Selecciona el workflow completado
3. Descarga desde **Artifacts**

Para releases públicos, crea un tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

---

by **E.Herrera** 🇨🇴
