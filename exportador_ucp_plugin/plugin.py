"""Clase de plugin QGIS: registro en el menu/toolbar y ciclo de vida."""

from qgis.PyQt.QtWidgets import QAction

from .export_dialog import ExportDialog

MENU_NAME = "&Exportador UCP"


class ExportadorUcpPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("Exportador UCP", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(MENU_NAME, self.action)
        self.iface.addToolBarIcon(self.action)

    def run(self):
        self.dialog = ExportDialog(self.iface, self.iface.mainWindow())
        self.dialog.exec()

    def unload(self):
        self.iface.removePluginMenu(MENU_NAME, self.action)
        self.iface.removeToolBarIcon(self.action)
        self.action = None


def classFactory(iface):
    return ExportadorUcpPlugin(iface)
