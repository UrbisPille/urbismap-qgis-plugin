import hashlib
import hmac
import os
import shutil
import subprocess
import time
import webbrowser

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    Qgis,
)
from qgis.gui import QgsMapTool

VERSION = "1.0.1"
HMAC_SECRET = b"SuperSegretissimo_Agente008"


class UrbisMapPointTool(QgsMapTool):
    def __init__(self, canvas, iface, action):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.action = action

    def activate(self):
        self.canvas.setCursor(Qt.CrossCursor)

    def deactivate(self):
        if self.action:
            self.action.setChecked(False)
        super().deactivate()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        try:
            point = self.toMapCoordinates(event.pos())
            source_crs = self.canvas.mapSettings().destinationCrs()
            dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
            point_wgs84 = transform.transform(point)

            lat = point_wgs84.y()
            lng = point_wgs84.x()
            url = f"https://www.urbismap.com/?lat={lat:.8f}&lng={lng:.8f}"
            self._open_external_browser(url)

        except Exception as e:
            self.iface.messageBar().pushMessage(
                "UrbisMap Click",
                f"Errore durante l'apertura di UrbisMap: {e}",
                level=Qgis.Critical,
                duration=5,
            )
        finally:
            self.canvas.unsetMapTool(self)
            self.iface.actionPan().trigger()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.canvas.unsetMapTool(self)
            self.iface.actionPan().trigger()

    def _open_external_browser(self, url):
        ts = str(int(time.time()))
        sig_payload = f"{url}|{ts}|{VERSION}"
        sig = hmac.new(HMAC_SECRET, sig_payload.encode(), hashlib.sha256).hexdigest()
        sep = "&" if "?" in url else "?"
        tracked_url = f"{url}{sep}source=qgis-plugin&v={VERSION}&ts={ts}&sig={sig}"

        chrome_candidates = []
        if os.name == "nt":
            local = os.environ.get("LOCALAPPDATA", "")
            program_files = os.environ.get("PROGRAMFILES", "")
            program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")
            chrome_candidates = [
                os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
            ]

        chrome_path = next((p for p in chrome_candidates if p and os.path.exists(p)), None)
        if not chrome_path:
            chrome_path = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")

        if chrome_path:
            subprocess.Popen([chrome_path, tracked_url], shell=False)
        else:
            webbrowser.open_new(tracked_url)


class UrbisMapPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.toolbar = None
        self.tool = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(QIcon(icon_path), "Apri in UrbisMap", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.setToolTip("Click sul pulsante, poi click sulla mappa per aprire UrbisMap")
        self.action.triggered.connect(self.run)

        self.toolbar = self.iface.addToolBar("UrbisMap Click")
        self.toolbar.setObjectName("UrbisMapClickToolbar")
        self.toolbar.addAction(self.action)
        self.iface.addPluginToMenu("&UrbisMap Click", self.action)

    def unload(self):
        if self.tool and self.canvas.mapTool() == self.tool:
            self.canvas.unsetMapTool(self.tool)
        if self.action:
            self.iface.removePluginMenu("&UrbisMap Click", self.action)
            if self.toolbar:
                self.toolbar.removeAction(self.action)
            self.action.deleteLater()
            self.action = None
        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

    def run(self):
        self.tool = UrbisMapPointTool(self.canvas, self.iface, self.action)
        self.canvas.setMapTool(self.tool)
        self.action.setChecked(True)
        self.iface.messageBar().pushMessage(
            "UrbisMap Click",
            "Clicca un punto sulla mappa",
            level=Qgis.Info,
            duration=3,
        )
