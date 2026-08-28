"""Dialogo del plugin: elegir carpeta base, asignar capas por rol y exportar."""

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from . import export_logic as core


class ExportDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Exportador UCP")
        self.resize(560, 520)
        self.base_dir = None
        self.role_combos = {}
        self.role_status = {}

        project = QgsProject.instance()
        self.matches, self.vector_layers = core.detect_matches(project)

        layout = QVBoxLayout(self)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        pick_btn = QPushButton("Elegir carpeta base...")
        pick_btn.clicked.connect(self.pick_folder)
        folder_row.addWidget(QLabel("Carpeta base:"))
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(pick_btn)
        layout.addLayout(folder_row)

        form = QFormLayout()
        for role in core.ROLES:
            combo = QComboBox()
            combo.addItem("-- Ninguna / omitir --", None)
            for lyr in self.vector_layers:
                combo.addItem(lyr.name(), lyr.id())
            matched = self.matches.get(role.key)
            if matched is not None:
                idx = combo.findData(matched.id())
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            status = QLabel("")
            self.role_combos[role.key] = combo
            self.role_status[role.key] = status
            row = QHBoxLayout()
            row.addWidget(combo)
            row.addWidget(status)
            form.addRow(f"{role.label} -> {role.final_name}", row)
        layout.addLayout(form)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.export_btn = QPushButton("Exportar")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.do_export)
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.close)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def pick_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Elegir carpeta base", "")
        if chosen:
            self.base_dir = chosen
            self.folder_edit.setText(chosen)
            self.export_btn.setEnabled(True)

    def selected_pairs(self):
        project = QgsProject.instance()
        pairs = []
        for role in core.ROLES:
            layer_id = self.role_combos[role.key].currentData()
            if layer_id is None:
                continue
            layer = project.mapLayer(layer_id)
            if layer is not None:
                pairs.append((role, layer))
        return pairs

    def do_export(self):
        if not self.base_dir:
            return
        pairs = self.selected_pairs()
        if not pairs:
            QMessageBox.information(self, "Nada para exportar", "No se selecciono ninguna capa.")
            return

        conflicts = core.find_conflicts(self.base_dir, pairs)
        if conflicts:
            msg = "Los siguientes archivos/capas ya existen y se van a sobrescribir:\n\n" + "\n".join(conflicts)
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            if QMessageBox.question(self, "Confirmar sobrescritura", msg, buttons) != QMessageBox.StandardButton.Yes:
                self.log.appendPlainText("Cancelado por el usuario (conflictos no confirmados).")
                return

        core.ensure_output_dirs(self.base_dir)
        self.log.appendPlainText(
            f"Carpeta raster/SRTM preparada en {self.base_dir}/exercise_data/raster/SRTM "
            "(la descarga del DEM sigue siendo manual)."
        )

        project = QgsProject.instance()
        tctx = project.transformContext()
        ok_count = 0
        fail_count = 0

        for role, layer in pairs:
            self.role_status[role.key].setText("...")
            result = core.export_role(role, layer, self.base_dir, tctx)
            if not result.ok:
                fail_count += 1
                self.role_status[role.key].setText("FALLO")
                self.log.appendPlainText(f"[{role.key}] ERROR al exportar: {result.message}")
                continue

            uri = core.build_output_uri(role, result.new_filename, result.new_layername)
            new_layer, err = core.replace_layer_in_project(project, layer, uri, role.final_name)
            if new_layer is None:
                fail_count += 1
                self.role_status[role.key].setText("FALLO")
                self.log.appendPlainText(f"[{role.key}] guardado OK pero fallo el reemplazo: {err}")
                continue

            ok_count += 1
            self.role_status[role.key].setText("OK")
            self.log.appendPlainText(f"[{role.key}] -> {role.rel_path} ({role.final_name}) OK")

        skipped = len(core.ROLES) - len(pairs)
        summary = f"Exportacion terminada: {ok_count} OK, {fail_count} con error, {skipped} omitidas."
        self.log.appendPlainText(summary)
        self.log.appendPlainText("Nota: los estilos/simbologia no se copian automaticamente.")
        level = Qgis.Success if fail_count == 0 else Qgis.Warning
        self.iface.messageBar().pushMessage("Exportador UCP", summary, level=level, duration=6)
