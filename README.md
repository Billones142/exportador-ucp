# Exportador UCP

Plugin de [QGIS](https://qgis.org) que exporta capas vectoriales cargadas en el proyecto a **ESRI Shapefile**, **GeoPackage** y **SpatiaLite**, con el formato, la ruta y el nombre de capa correctos, y las reemplaza en el proyecto por la versión guardada en disco.

Está pensado para el flujo típico de extracción de datos OSM con [QuickOSM](https://github.com/3liz/QuickOSM) (edificios, uso de suelo, áreas protegidas, agua, caminos, ríos y lugares), pero detecta las capas tanto por su nombre original de QuickOSM como por el nombre final ya exportado, así que también sirve para reordenar/reexportar un proyecto que ya tiene las capas cargadas.

## Qué hace

1. Pide una carpeta base de destino (nunca escribe nada antes de elegirla).
2. Detecta automáticamente, entre las capas vectoriales cargadas en el proyecto, cuál corresponde a cada uno de los siguientes destinos (editable a mano si la detección falla o si querés forzar otra capa):

   | capa | formato | ruta de salida | nombre final |
   |---|---|---|---|
   | `place` | ESRI Shapefile | `exercise_data/shapefile/places.shp` | `places` |
   | `natural_water` | ESRI Shapefile | `exercise_data/shapefile/water.shp` | `water` |
   | `waterway_river` | ESRI Shapefile | `exercise_data/shapefile/rivers.shp` | `rivers` |
   | `boundary_protected_area` | ESRI Shapefile | `exercise_data/shapefile/protected_areas.shp` | `protected_areas` |
   | `building` | GeoPackage | `exercise_data/training_data.gpkg` (capa `buildings`) | `buildings` |
   | `highway` | GeoPackage (mismo .gpkg) | `exercise_data/training_data.gpkg` (capa `roads`) | `roads` |
   | `landuse` | SpatiaLite | `exercise_data/landuse.sqlite` | `landuse` |

3. Antes de sobrescribir un archivo o una capa ya existente, pide confirmación.
4. Exporta cada capa asignada, maneja errores de forma independiente por capa (si una falla, las demás se completan igual) y reemplaza cada capa temporal en el proyecto por la versión en disco, conservando su posición en el árbol de capas.
5. Crea además `exercise_data/raster/SRTM/` para alojar el DEM SRTM que se descarga manualmente aparte.

## Requisitos

- QGIS 3.0 o superior (probado en QGIS 4.2.1).
- No tiene dependencias externas más allá de PyQGIS (no requiere `pip install` de nada).
- Opcional: el plugin [QuickOSM](https://github.com/3liz/QuickOSM) para generar las capas de origen desde OpenStreetMap.

## Instalación

### Ubicación de la carpeta de plugins de QGIS

QGIS busca los plugins en la carpeta `python/plugins` del perfil activo. Esa carpeta cambia según el sistema operativo y la versión mayor de QGIS instalada (`QGIS3` para QGIS 3.x, `QGIS4` para QGIS 4.x):

| SO | Ruta típica |
|---|---|
| Linux | `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/` (o `QGIS3` según tu versión) |
| Windows | `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\` (o `QGIS3`) — normalmente `C:\Users\<usuario>\AppData\Roaming\QGIS\QGIS4\profiles\default\python\plugins\` |
| macOS | `~/Library/Application Support/QGIS/QGIS4/profiles/default/python/plugins/` (o `QGIS3`) |

Si usás un perfil de QGIS distinto de `default`, reemplazá esa parte de la ruta por el nombre de tu perfil (podés verlo en QGIS en **Configuración ► Perfiles de usuario**).

### Opción A — Clonar/copiar la carpeta del plugin (recomendada)

1. Cloná este repositorio en cualquier ubicación:

   ```bash
   git clone https://github.com/Billones142/exportador-ucp.git
   ```

2. Copiá (o enlazá) la carpeta `exportador_ucp_plugin/` dentro de la carpeta de plugins de tu perfil de QGIS.

   **Linux / macOS** (enlace simbólico, se actualiza solo si volvés a hacer `git pull`):

   ```bash
   ln -s "$(pwd)/exportador-ucp/exportador_ucp_plugin" \
         ~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/exportador_ucp_plugin
   ```

   En macOS cambiá la ruta de destino por:

   ```bash
   ln -s "$(pwd)/exportador-ucp/exportador_ucp_plugin" \
         ~/Library/Application\ Support/QGIS/QGIS4/profiles/default/python/plugins/exportador_ucp_plugin
   ```

   **Windows** (PowerShell, como copia normal):

   ```powershell
   Copy-Item -Recurse .\exportador-ucp\exportador_ucp_plugin `
     "$env:APPDATA\QGIS\QGIS4\profiles\default\python\plugins\exportador_ucp_plugin"
   ```

   (En Windows también podés crear un enlace simbólico con `New-Item -ItemType SymbolicLink`, ejecutando PowerShell como administrador.)

3. Reiniciá QGIS (o usá el plugin **Plugin Reloader** si ya lo tenés).

### Opción B — Instalar desde ZIP en QGIS

1. Descargá o cloná este repositorio y comprimí la carpeta `exportador_ucp_plugin/` en un `.zip` (el `.zip` debe contener directamente `exportador_ucp_plugin/` en su raíz, con `metadata.txt` adentro).
2. En QGIS: **Complementos ► Administrar/Instalar complementos ► Instalar desde ZIP**, elegí el `.zip` y presioná **Instalar complemento**.

### Activar el plugin

En cualquiera de los dos casos, andá a **Complementos ► Administrar/Instalar complementos ► pestaña Instalados** y tildá **Exportador UCP**.

## Uso

1. Cargá en el proyecto las capas vectoriales a exportar (por ejemplo, extraídas con QuickOSM).
2. Abrí el plugin desde **Complementos ► Exportador UCP** o el ícono en la barra de herramientas.
3. Elegí la carpeta base de destino.
4. Revisá/corregí la asignación automática de capas por rol.
5. Presioná **Exportar** y confirmá si se te pide sobrescribir algo existente.
6. Revisá el registro del diálogo y el mensaje final para confirmar qué se exportó correctamente.

## Estructura del repositorio

```
exportador-ucp/
└── exportador_ucp_plugin/      # carpeta del plugin (esta es la que se instala en QGIS)
    ├── __init__.py
    ├── metadata.txt
    ├── plugin.py                # registro en QGIS (initGui/unload/run)
    ├── export_logic.py          # lógica de exportación (sin dependencias de Qt)
    └── export_dialog.py         # diálogo (selector de carpeta, asignación por capa, log)
```
