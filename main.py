
from core import thread, process, config, cdphandler as cdph, tablemanager as tm
from core.cdphandler import TyranoVars
from ui.ui import InterfazJAca

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QTreeWidgetItem,
    QMessageBox,
    QComboBox,
)
from PySide6.QtGui import QBrush, QColor
from PySide6.QtCore import Signal, QTimer, Qt

import asyncio
import json
import os
import sys
import time


class MotorJAca(InterfazJAca):
    update_gui_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.language = config.obtener_valor_configuracion("app", "language")
        self.traducir_interfaz()

        self._spb_value = 0
        self._lpb_value = 0
        self._scan_history = []

        self.thread_manager = thread.ThreadManager()
        self.persistent_async = thread.PersistentAsync()
        self.persistent_async.start()

        self.handler = None
        self.game = None

        self.update_gui_signal.connect(self.procesar_actualizacion_interfaz)

        self.actionLaunch_Game.triggered.connect(self.iniciar_juego)
        self.actionStop_Game.triggered.connect(self.detener_juego)
        self.actionTheme.triggered.connect(self.alternar_tema)
        self.actionLanguage.triggered.connect(self.alternar_idioma)
        self.actionSettings.triggered.connect(self.mostrar_configuracion)
        self.actionTutorial.triggered.connect(self.mostrar_tutorial)
        self.actionAbout.triggered.connect(self.mostrar_acerca)
        self.actionSave_Logs.triggered.connect(self.guardar_registros)
        self.LoadButton.clicked.connect(self.cargar_lista_cruda)
        self.UnloadButton.clicked.connect(self.descargar_lista_cruda)
        self.UndoButton.clicked.connect(self.volver_a_escanear)

        self.ScanButton.clicked.connect(self.escanear)
        self.ClearButton.clicked.connect(self.limpiar_resultados)

        self._update_prog_bar = QTimer(self)
        self._update_prog_bar.timeout.connect(self.actualizar_barras_progreso)
        self._update_prog_bar.start(100)

    def closeEvent(self, event):
        try:
            self._pause_polling = True
            self._connected = False

            if self.handler is not None:
                self.close_websocket()

            if self.game is not None:
                self.game.detener()

            self.persistent_async.detener()
        except Exception as exc:
            print(repr(exc))

        event.accept()

    @thread.ejecutar_protocolo_cdp
    async def set_value(self, target, value):
        self.pausar_lectura()

        try:
            while not self._polling_paused:
                await asyncio.sleep(0.05)

            if not self.handler:
                return

            value = self.interpretar_valor(value)

            if target.startswith("TYRANO.kag."):
                expression_target = target
            elif target.startswith("stat.f."):
                expression_target = (
                    "TYRANO.kag." + target
                )
            elif target.startswith("variable.tf."):
                expression_target = (
                    "TYRANO.kag." + target
                )
            elif target.startswith("variable.sf."):
                expression_target = (
                    "TYRANO.kag." + target
                )
            else:
                expression_target = (
                    "TYRANO.kag." + target
                )

            await self.handler.set_value(
                expression_target,
                value,
            )

        except Exception as exc:
            print(
                f"Error changing value {target}: {exc!r}"
            )

        finally:
            self.reanudar_lectura()

    def actualizar_barras_progreso(self):
        self.ScanProgressBar.setValue(max(0, min(100, self._spb_value)))
        self.LoadProgressBar.setValue(max(0, min(100, self._lpb_value)))

    def actualizar_interfaz(self, func, *args, **kwargs):
        self.update_gui_signal.emit(
            {
                "func": func,
                "args": args,
                "kwargs": kwargs,
            }
        )

    def procesar_actualizacion_interfaz(self, data):
        try:
            func = data["func"]
            args = data.get("args", ())
            kwargs = data.get("kwargs", {})
            func(*args, **kwargs)
        except Exception as exc:
            print(repr(exc))

    def mostrar_resultados(self, data):
        for item_data in data:
            for path, value in item_data.items():
                name = path.split(".")[-1]

                if not isinstance(value, str):
                    value = json.dumps(
                        value,
                        ensure_ascii=False,
                        default=str,
                    )

                item = QTreeWidgetItem(
                    self.ResultTab,
                    [
                        name,
                        value,
                        value,
                        path,
                    ],
                )

                self._rt_list_items.append(item)

        self.ScanButton.setEnabled(True)
        self.ClearButton.setEnabled(True)
        self.reanudar_lectura()

    @thread.ejecutar_protocolo_cdp
    async def buscar_por_nombre(self, name):
        await self.esperar_pausa_lectura()

        if not self.handler:
            return

        try:
            self._scan_history.append(str(name))
            start = time.perf_counter()

            data = await self.handler.evaluate(TyranoVars.F, True)
            data = self.aplanar(data, "stat.f.")

            tf_data = await self.handler.evaluate(TyranoVars.TF, True)
            tf_data = self.aplanar(tf_data, "variable.tf.")

            data.update(tf_data)

            found = []
            total = len(data)

            for index, key in enumerate(data, start=1):
                if name.lower() in key.rpartition(".")[-1].split("[")[0].lower():
                    found.append(key)

                self._spb_value = int(index / total * 100) if total else 100

            elapsed = time.perf_counter() - start
            self.FoundLabel.setText(
                f"Found: {len(found)} ({elapsed:.4f}s)"
            )

            self.mostrar_resultados(
                [{name: data[name]} for name in found]
            )

            self._spb_value = 0

        except Exception as exc:
            self.actualizar_interfaz(self.ScanButton.setEnabled, True)
            print(repr(exc))
            self.actualizar_interfaz(
                self.FoundLabel.setText,
                f"Error: {exc}",
            )
            self.reanudar_lectura()

    @thread.ejecutar_protocolo_cdp
    async def buscar_por_valor(self, value):
        await self.esperar_pausa_lectura()

        if not self.handler:
            return

        try:
            value = self.interpretar_valor(value)
            self._scan_history.append(str(value))
            start = time.perf_counter()

            data = await self.handler.evaluate(TyranoVars.F, True)
            data = self.aplanar(data, "stat.f.")

            tf_data = await self.handler.evaluate(TyranoVars.TF, True)
            tf_data = self.aplanar(tf_data, "variable.tf.")

            data.update(tf_data)

            found = []
            total = len(data)

            for index, (key, current) in enumerate(
                data.items(),
                start=1,
            ):
                if current == value:
                    found.append(key)

                self._spb_value = int(index / total * 100) if total else 100

            elapsed = time.perf_counter() - start

            self.FoundLabel.setText(
                f"Found: {len(found)} ({elapsed:.4f}s)"
            )

            self.mostrar_resultados(
                [{name: data[name]} for name in found]
            )

            self._spb_value = 0

        except Exception as exc:
            self.actualizar_interfaz(self.ScanButton.setEnabled, True)
            print(repr(exc))
            self.actualizar_interfaz(
                self.FoundLabel.setText,
                f"Error: {exc}",
            )
            self.reanudar_lectura()

    @staticmethod
    def interpretar_valor(value):
        value = value.strip()

        if value == "":
            return ""

        if value.lower() == "true":
            return True

        if value.lower() == "false":
            return False

        if value.lower() in ("null", "none"):
            return None

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return float(value)
        except ValueError:
            pass

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def esperar_pausa_lectura(self):
        while not self._polling_paused:
            await asyncio.sleep(0.05)

    def limpiar_resultados(self):
        self.ResultTab.clear()
        self._rt_list_items.clear()
        self.ClearButton.setEnabled(False)
        self._spb_value = 0

    def escanear(self):
        if not self._connected or not self.handler:
            QMessageBox.warning(self, self.tr("Not connected"), self.tr("Launch a Tyrano game before scanning."))
            return
        # Until rescan modes have data-history support, never pretend those modes work.
        if self.SearchTypeInput.currentIndex() != 0 and not self.NameRadioButton.isChecked():
            QMessageBox.information(self, self.tr("Not implemented"), self.tr("Only Exact value is currently supported; other scan types are planned."))
            return
        if self.NameRadioButton.isChecked() and not self.ScanInput.text().strip():
            QMessageBox.information(self, self.tr("Search"), self.tr("Enter a variable name (empty searches are disabled)."))
            return
        self.pausar_lectura()
        self.limpiar_resultados()
        self.ScanButton.setEnabled(False)
        if self.NameRadioButton.isChecked():
            self.buscar_por_nombre(self.ScanInput.text())
        else:
            self.buscar_por_valor(self.ScanInput.text())

    def aplanar(self, data, prefix=None):
        if not isinstance(data, dict):
            return {}

        result = {}

        for key, value in data.items():
            name = f"{prefix}{key}" if prefix else str(key)
            result.update(self._aplanar(name, value))

        return result

    def _aplanar(self, name, value):
        if isinstance(value, list):
            result = {}

            for index, item in enumerate(value):
                result.update(
                    self._aplanar(
                        f"{name}[{index}]",
                        item,
                    )
                )

            return result

        if isinstance(value, dict):
            result = {}

            for key, item in value.items():
                result.update(
                    self._aplanar(
                        f"{name}.{key}",
                        item,
                    )
                )

            return result

        return {name: value}

    def _obtener_datos_arbol(self, root):
        color = root.foreground(0).color().getRgb()[:3]

        data = {
            "name": root.text(0),
            "path": root.text(1),
            "value": root.text(2),
            "color": color,
            "children": [],
        }

        for index in range(root.childCount()):
            data["children"].append(
                self._obtener_datos_arbol(root.child(index))
            )

        return data

    def obtener_datos_arbol(self):
        data = []
        root = self.ValueListWidget.invisibleRootItem()

        for index in range(root.childCount()):
            data.append(
                self._obtener_datos_arbol(
                    root.child(index)
                )
            )

        return data

    def reanudar_lectura(self):
        self._pause_polling = False

    def pausar_lectura(self):
        self._pause_polling = True

    @thread.ejecutar_protocolo_cdp
    async def leer_periodicamente(self):
        general_items = []
        result_items = []
        paths = set()

        while True:
            if self._pause_polling:
                self._polling_paused = True
                await asyncio.sleep(0.1)
                continue

            if not self._connected or not self.handler:
                self._polling_paused = False
                await asyncio.sleep(0.1)
                continue

            self._polling_paused = False

            try:
                general_items = [
                    item.text(1)
                    for item in self._tree_list_items
                    if item.text(1)
                ]

                result_items = [
                    item.text(3)
                    for item in self._rt_list_items
                    if item.text(3)
                ]

                paths = set(
                    general_items + result_items
                )

                if not paths:
                    await asyncio.sleep(0.1)
                    continue

                expression_parts = []

                for path in paths:
                    safe_path = path.replace(
                        "\\",
                        "\\\\",
                    ).replace(
                        '"',
                        '\\"',
                    )

                    expression_parts.append(
                        f'"{safe_path}":TYRANO.kag.{path}'
                    )

                expression = "({" + ",".join(expression_parts) + "})"

                object_id = await self.handler.evaluate(
                    expression,
                    False,
                )

                response = await self.handler.get_properties(
                    object_id
                )

                data = {}

                for result in response:
                    if result["name"] in cdph.SKIP_PROPERTIES:
                        continue

                    value = result.get("value", {})

                    if value.get("type") == "undefined":
                        data[result["name"]] = "??"
                    else:
                        data[result["name"]] = value.get(
                            "value",
                            "??",
                        )

                for item in self._tree_list_items:
                    path = item.text(1)

                    if path in data:
                        value = data[path]

                        if not isinstance(value, str):
                            value = json.dumps(
                                value,
                                ensure_ascii=False,
                                default=str,
                            )

                        item.setText(2, value)

                for item in self._rt_list_items:
                    path = item.text(3)

                    if path not in data:
                        continue

                    previous = item.text(2)
                    current = data[path]

                    try:
                        previous_cmp = json.loads(previous)
                    except (json.JSONDecodeError, TypeError):
                        previous_cmp = previous

                    if isinstance(current, str):
                        item.setText(1, current)

                        try:
                            current_cmp = json.loads(current)
                        except (json.JSONDecodeError, TypeError):
                            current_cmp = current
                    else:
                        current_cmp = current
                        item.setText(
                            1,
                            json.dumps(
                                current,
                                ensure_ascii=False,
                                default=str,
                            ),
                        )

                    if current_cmp == previous_cmp:
                        color = QColor(255, 255, 255)
                    elif (
                        isinstance(current_cmp, (int, float))
                        and isinstance(previous_cmp, (int, float))
                    ):
                        color = (
                            QColor(255, 0, 0)
                            if current_cmp < previous_cmp
                            else QColor(96, 128, 255)
                        )
                    else:
                        color = QColor(255, 0, 0)

                    item.setForeground(
                        1,
                        QBrush(color),
                    )

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(repr(exc))

            await asyncio.sleep(0.1)

    @thread.ejecutar_protocolo_cdp
    async def conectar_juego(self):
        try:
            ws_url = await cdph.get_cdp_ws_url_async(
                self.game.port,
                self.game.game,
                wait=True,
            )

            if not ws_url:
                raise ConnectionError(
                    "No compatible CDP target was found."
                )

            self.handler = cdph.CDPHandler(ws_url)
            await self.handler.connect()

            self.actualizar_interfaz(
                self.InfoLabel.setText,
                self.game.game_name,
            )

            self._connected = True

            self.actualizar_interfaz(
                self.FoundLabel.setText,
                "Connected",
            )

        except Exception as exc:
            self._connected = False
            self.handler = None

            self.actualizar_interfaz(
                QMessageBox.warning,
                self,
                "Connection error",
                str(exc),
            )

    @thread.threaded
    def _iniciar_proceso_juego(self):
        return self.game.iniciar_juego()

    def iniciar_juego(self):
        game_loc, _ = QFileDialog.getOpenFileName(
            self,
            "Open Game",
            "",
            "Executable (*.exe);;All Files (*)",
        )

        if not game_loc:
            return

        try:
            if self.game is not None:
                self.game.detener()

            self.game = process.GameProcess(
                game_loc,
                port=config.obtener_valor_configuracion(
                    "websocket",
                    "port",
                ),
            )

            self._iniciar_proceso_juego()

            self.conectar_juego()
            self.leer_periodicamente()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Launch error",
                str(exc),
            )

    def detener_juego(self):
        self._pause_polling = True
        self._connected = False

        if self.handler is not None:
            self.close_websocket()

        if self.game is not None:
            try:
                self.game.detener()
            except Exception as exc:
                print(repr(exc))

        self.handler = None
        self.InfoLabel.setText("No game loaded")



    def alternar_tema(self):
        current = config.obtener_valor_configuracion("app", "theme")
        theme = "default-light" if current == "default-dark" else "default-dark"
        config.guardar_valor_configuracion("app", "theme", theme)
        self.aplicar_tema(theme)

    def alternar_idioma(self):
        lang = "en" if getattr(self, "language", "en") == "es" else "es"
        self.language = lang
        config.guardar_valor_configuracion("app", "language", lang)
        self.traducir_interfaz()

    def aplicar_tema(self, theme):
        path = os.path.join("theme", theme, "style.qss")
        if not os.path.exists(path):
            path = os.path.join("theme", theme, "dark.qss" if theme.endswith("dark") else "light.qss")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def mostrar_configuracion(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QSpinBox, QDialogButtonBox
        dialog = QDialog(self); dialog.setWindowTitle(self.tr("Settings"))
        layout = QFormLayout(dialog)
        port = QSpinBox(); port.setRange(1024, 65535)
        port.setValue(int(config.obtener_valor_configuracion("websocket", "port")))
        language = QComboBox(); language.addItems(["English", "Español"])
        language.setCurrentIndex(1 if getattr(self, "language", "en") == "es" else 0)
        layout.addRow(self.tr("WebSocket port"), port); layout.addRow(self.tr("Language"), language)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config.guardar_valor_configuracion("websocket", "port", port.value())
            self.language = "es" if language.currentIndex() else "en"
            config.guardar_valor_configuracion("app", "language", self.language)
            self.traducir_interfaz()

    def mostrar_tutorial(self):
        QMessageBox.information(self, self.tr("Tutorial"), self.tr("1. Launch a Tyrano game.\n2. Scan by exact value or variable name.\n3. Double-click a result to add it to the value table.\n4. Edit values and save/load tables."))

    def mostrar_acerca(self):
        QMessageBox.about(self, self.tr("About"), self.tr("Tyrano Cheat Engine\nTyrano game variable inspector and editor."))

    def guardar_registros(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save logs"), "", "Text files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.LogLineEdit.toPlainText())

    def volver_a_escanear(self):
        if not self._scan_history:
            QMessageBox.information(self, self.tr("Rescan"), self.tr("No previous scan is available.")); return
        self.ScanInput.setText(self._scan_history[-1])
        self.escanear()

    def cargar_lista_cruda(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Load raw list"), "", "JSON files (*.json);;Text files (*.txt);;All files (*)")
        if not path: return
        try:
            with open(path, encoding="utf-8") as f: content = f.read()
            try: data = json.loads(content)
            except json.JSONDecodeError: data = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            if isinstance(data, dict): data = [{"name": k, "path": k, "value": v} for k, v in data.items()]
            for entry in data:
                if isinstance(entry, str): name, route, value = entry, entry, "??"
                elif isinstance(entry, dict): name, route, value = entry.get("name", entry.get("path", "")), entry.get("path", ""), entry.get("value", "??")
                else: continue
                item = QTreeWidgetItem(self.RawListWidget, [str(name), str(route), str(value)])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)
            self._lpb_value = 100
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Load error"), str(exc))

    def descargar_lista_cruda(self):
        self.RawListWidget.clear(); self._lpb_value = 0


def check_config():
    config.crear_configuracion()

    theme = config.obtener_valor_configuracion(
        "app",
        "theme",
    )

    theme_root = config.THEME_DIRECTORY

    if not os.path.exists(theme_root):
        os.makedirs(
            theme_root,
            exist_ok=True,
        )

        QMessageBox.critical(
            None,
            "Error",
            "No themes found. The application will run "
            "without a theme.",
        )

    elif theme not in os.listdir(theme_root):
        QMessageBox.warning(
            None,
            "Warning",
            f"Theme {theme} not found. "
            "The default-dark theme will be used.",
        )


def main():
    app = QApplication(sys.argv)

    check_config()

    window = MotorJAca()
    window.aplicar_tema(config.obtener_valor_configuracion("app", "theme"))
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
