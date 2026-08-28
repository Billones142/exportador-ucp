"""Logica de exportacion de capas OSM a Shapefile/GeoPackage/SpatiaLite (sin dependencias de Qt)."""

import os
from collections import namedtuple

from qgis.core import QgsVectorLayer, QgsVectorFileWriter

RoleSpec = namedtuple(
    "RoleSpec",
    ["key", "label", "quickosm_names", "driver", "rel_path", "gpkg_layer", "final_name"],
)

# gpkg_layer es el nombre de capa a usar dentro del contenedor (GPKG/SpatiaLite);
# None para Shapefile, donde el archivo es la capa.
ROLES = [
    RoleSpec("place", "place (puntos)", ("place",),
             "ESRI Shapefile", "exercise_data/shapefile/places.shp", None, "places"),
    RoleSpec("natural_water", "natural_water (multipoligonos)", ("natural_water",),
             "ESRI Shapefile", "exercise_data/shapefile/water.shp", None, "water"),
    RoleSpec("waterway_river", "waterway_river (lineas)", ("waterway_river",),
             "ESRI Shapefile", "exercise_data/shapefile/rivers.shp", None, "rivers"),
    RoleSpec("boundary_protected_area", "boundary_protected_area (multipoligonos)",
             ("boundary_protected_area",),
             "ESRI Shapefile", "exercise_data/shapefile/protected_areas.shp", None, "protected_areas"),
    RoleSpec("building", "building (multipoligonos)", ("building",),
             "GPKG", "exercise_data/training_data.gpkg", "buildings", "buildings"),
    RoleSpec("highway", "highway (lineas)", ("highway",),
             "GPKG", "exercise_data/training_data.gpkg", "roads", "roads"),
    RoleSpec("landuse", "landuse (multipoligonos)", ("landuse",),
             "SQLite", "exercise_data/landuse.sqlite", "landuse", "landuse"),
]

ExportResult = namedtuple("ExportResult", ["ok", "message", "new_filename", "new_layername"])


# Sufijos de tipo de geometria que QuickOSM (u otras herramientas) suelen agregar al
# nombre de capa (p.ej. "building_multipolygons", "highway_lines"). Se prueban del mas
# largo al mas corto para no cortar de mas.
_GEOM_SUFFIXES = (
    "_multipolygons", "_multipolygon", "_polygons", "_polygon",
    "_multilinestrings", "_multilinestring", "_multilines", "_multiline",
    "_lines", "_line", "_points", "_point",
)


def _normalize(name):
    n = name.strip().lower().replace(" ", "_")
    changed = True
    while changed:
        changed = False
        for suf in _GEOM_SUFFIXES:
            if n.endswith(suf) and len(n) > len(suf):
                n = n[: -len(suf)]
                changed = True
    return n


def detect_matches(project):
    """Devuelve (dict role.key -> QgsVectorLayer o None, lista de capas vectoriales del proyecto).

    Cada capa cargada se compara, tras normalizar (minusculas, sin sufijo de geometria),
    contra el nombre final del rol (p.ej. "water") y contra el/los nombre(s) por defecto
    de QuickOSM (p.ej. "natural_water"). Esto cubre tanto un proyecto recien salido de
    QuickOSM como uno que ya tiene las capas finales cargadas (por ejemplo al re-abrir un
    proyecto ya exportado). Se resuelve en dos pasadas para que una coincidencia exacta de
    nombre final tenga prioridad sobre una coincidencia por nombre QuickOSM, y para que
    ninguna capa quede asignada a mas de un rol.
    """
    vector_layers = [lyr for lyr in project.mapLayers().values() if isinstance(lyr, QgsVectorLayer)]
    normalized = {lyr.id(): _normalize(lyr.name()) for lyr in vector_layers}
    matches = {role.key: None for role in ROLES}
    claimed_ids = set()

    for tier in range(2):  # 0: nombre final del rol : 1: nombre(s) por defecto de QuickOSM
        for role in ROLES:
            if matches[role.key] is not None:
                continue
            candidates = (
                [role.final_name.lower()] if tier == 0
                else [name.lower() for name in role.quickosm_names]
            )
            found = next(
                (lyr for lyr in vector_layers
                 if lyr.id() not in claimed_ids and normalized[lyr.id()] in candidates),
                None,
            )
            if found is not None:
                matches[role.key] = found
                claimed_ids.add(found.id())

    return matches, vector_layers


def ensure_output_dirs(base_dir):
    """Crea las carpetas de salida. exercise_data/ tambien aloja el .gpkg y el .sqlite directamente."""
    os.makedirs(os.path.join(base_dir, "exercise_data", "shapefile"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "exercise_data", "raster", "SRTM"), exist_ok=True)


def _gpkg_layer_exists(container_path, layer_name):
    if not os.path.exists(container_path):
        return False
    probe = QgsVectorLayer(f"{container_path}|layername={layer_name}", "conflict_probe", "ogr")
    return probe.isValid()


def find_conflicts(base_dir, selected):
    """selected: lista de (RoleSpec, QgsVectorLayer). Devuelve lista de strings legibles."""
    conflicts = []
    for role, _layer in selected:
        out_path = os.path.join(base_dir, role.rel_path)
        if role.gpkg_layer is not None:
            if _gpkg_layer_exists(out_path, role.gpkg_layer):
                conflicts.append(f"{role.rel_path} -> capa '{role.gpkg_layer}' ya existe (se sobrescribira)")
        elif os.path.exists(out_path):
            conflicts.append(f"{role.rel_path} ya existe (se sobrescribira)")
    return conflicts


def export_role(role, source_layer, base_dir, transform_context):
    """Escribe source_layer a disco segun la spec de role. No modifica el proyecto."""
    out_path = os.path.join(base_dir, role.rel_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.fileEncoding = "UTF-8"
    opts.driverName = role.driver

    if role.driver == "GPKG":
        opts.layerName = role.gpkg_layer
        # Regla dinamica: solo se crea/sobrescribe el archivo completo si aun no existe;
        # si ya existe (de esta corrida o una anterior), se crea/sobrescribe solo esa capa,
        # sin tocar la otra capa que comparte el mismo .gpkg (buildings/roads).
        opts.actionOnExistingFile = (
            QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(out_path)
            else QgsVectorFileWriter.CreateOrOverwriteFile
        )
    elif role.driver == "SQLite":
        opts.layerName = role.gpkg_layer
        opts.datasourceOptions = ["SPATIALITE=YES"]
        opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    else:  # ESRI Shapefile
        opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

    err, err_msg, new_filename, new_layername = QgsVectorFileWriter.writeAsVectorFormatV3(
        source_layer, out_path, transform_context, opts
    )
    if err != QgsVectorFileWriter.NoError:
        return ExportResult(False, err_msg or f"error desconocido (code {err})", None, None)

    return ExportResult(True, "OK", new_filename or out_path, new_layername or role.gpkg_layer)


def build_output_uri(role, new_filename, new_layername):
    if role.gpkg_layer is not None:
        return f"{new_filename}|layername={new_layername}"
    return new_filename


def replace_layer_in_project(project, old_layer, new_uri, final_name):
    """Valida la capa nueva antes de tocar el proyecto, y la inserta en la misma posicion
    del arbol que ocupaba la capa vieja, usando addMapLayer(False) + insertLayer (patron seguro)."""
    new_layer = QgsVectorLayer(new_uri, final_name, "ogr")
    if not new_layer.isValid():
        return None, f"la capa nueva no es valida: {new_uri}"

    root = project.layerTreeRoot()
    old_node = root.findLayer(old_layer.id()) if old_layer is not None else None
    if old_node is not None:
        parent_group = old_node.parent() or root
        siblings = parent_group.children()
        index = siblings.index(old_node) if old_node in siblings else 0
        project.removeMapLayer(old_layer.id())
    else:
        parent_group = root
        index = 0

    project.addMapLayer(new_layer, False)
    parent_group.insertLayer(index, new_layer)
    return new_layer, None
