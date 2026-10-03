
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
import re
import logging


class MotorJAca(InterfazJAca):
    update_gui_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.language = config.obtener_valor_configuracion("app", "language")
        self._scan_timeout = int(config.obtener_valor_configuracion("scan", "timeout"))
        self._root_location = config.obtener_valor_configuracion("scan", "root")
        self._ignore_null = bool(config.obtener_valor_configuracion("scan", "ignore_null"))
        self._ignore_readonly = bool(config.obtener_valor_configuracion("scan", "ignore_readonly"))
        self._log_path = config.obtener_valor_configuracion("scan", "log_path")
        self.traducir_interfaz()

        self._spb_value = 0
        self._lpb_value = 0
        self._scan_history = []
        self._scan_snapshot = {}
        self._scan_candidates = None
        self._freeze_timer = QTimer(self)
        self._freeze_timer.timeout.connect(self._aplicar_congelado)
        self._frozen = {}
        self._scan_log = logging.getLogger("tyrano_scan")
        self._scan_log.setLevel(logging.INFO)
        self._scan_log.addHandler(logging.NullHandler())

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
        self.actionCustomTheme.triggered.connect(self.cargar_tema_personalizado)
        self.actionTutorial.triggered.connect(self.mostrar_tutorial)
        self.actionAbout.triggered.connect(self.mostrar_acerca)
        self.actionSave_Logs.triggered.connect(self.guardar_registros)
        self.ValueListWidget.itemChanged.connect(self.toggle_freeze)
        self.LoadButton.clicked.connect(self.cargar_lista_cruda)
        self.UnloadButton.clicked.connect(self.descargar_lista_cruda)
        self.ExportButton.clicked.connect(self.exportar_lista)
        self.RawListWidget.itemChanged.connect(self._raw_item_changed)

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
                self._cerrar_websocket_seguro()

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

            if self._ignore_readonly:
                check = await self.handler.evaluate(f"(()=>{{let p={json.dumps(expression_target)}.replace(/^TYRANO\\.kag\\./,'').split('.');let o=TYRANO.kag;for(let i=0;i<p.length-1;i++)o=o[p[i]];return Object.getOwnPropertyDescriptor(o,p[p.length-1])?.writable!==false}})()", True)
                if check is False:
                    self._log(f"Skipped read-only: {target}")
                    return
            await self.handler.set_value(expression_target, value)

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
        if not self.handler: return
        try:
            data = await asyncio.wait_for(self._obtener_variables(), timeout=self._scan_timeout)
            if self._ignore_null:
                data = {k:v for k,v in data.items() if v is not None and v != ""}
            found = {k:v for k,v in data.items() if name.lower() in k.rpartition(".")[-1].split("[")[0].lower()}
            self._finalizar_escaneo(found)
        except asyncio.TimeoutError: self._error_escaneo(TimeoutError(self.tr("Scan timed out")))
        except Exception as exc: self._error_escaneo(exc)

    async def _obtener_variables(self):
        roots = []
        mode = self._root_location
        if mode in ("f", "all"): roots.append((TyranoVars.F, "stat.f."))
        if mode in ("tf", "all"): roots.append((TyranoVars.TF, "variable.tf."))
        if mode in ("sf", "all"): roots.append((TyranoVars.SF, "variable.sf."))
        data = {}
        for expr, prefix in roots:
            try:
                value = await self.handler.evaluate(expr, True)
                data.update(self.aplanar(value, prefix))
            except Exception: continue
        return data

    def _finalizar_escaneo(self, found):
        self._scan_snapshot.update(found)
        self._scan_candidates = dict(found)
        self._scan_history.append(dict(found))
        elapsed = time.perf_counter() - getattr(self, "_scan_started", time.perf_counter())
        self.FoundLabel.setText(f"{self.tr('Found')}: {len(found)} ({elapsed:.3f}s)")
        self.mostrar_resultados([{k:v} for k,v in found.items()])
        self._log(f"Scan completed: {len(found)} candidate(s) in {elapsed:.3f}s")
        self._spb_value = 0

    def _error_escaneo(self, exc):
        self.actualizar_interfaz(self.ScanButton.setEnabled, True)
        self.actualizar_interfaz(self.FoundLabel.setText, f"{self.tr('Error')}: {exc}")
        self._log(f"Scan error: {exc}")
        self.reanudar_lectura()

    @thread.ejecutar_protocolo_cdp
    async def buscar_por_valor(self, value):
        await self.esperar_pausa_lectura()
        if not self.handler: return
        try:
            current = await asyncio.wait_for(self._obtener_variables(), timeout=self._scan_timeout)
            wanted = self.interpretar_valor(value)
            typ = self.SearchTypeInput.currentIndex()
            if typ in (4, 11) and self._scan_candidates is None:
                self._scan_candidates = dict(current)
                self._scan_history.append(dict(current))
                self.FoundLabel.setText(f"{self.tr('Found')}: {len(current)}")
                self.mostrar_resultados([{k:v} for k,v in current.items()])
                return
            if self._scan_candidates is None:
                candidates = current
                previous = {}
            else:
                candidates = {k:current[k] for k in self._scan_candidates if k in current}
                previous = self._scan_candidates
            found = {}
            bound = self.interpretar_valor(self.ScanInputB.text()) if typ == 3 else None
            for k,v in candidates.items():
                old = previous.get(k, v)
                if self._ignore_null and (v is None or v == "" or v == "??"): continue
                ok = False
                try:
                    if typ == 0: ok = v == wanted
                    elif typ == 1: ok = v > wanted
                    elif typ == 2: ok = v < wanted
                    elif typ == 3: ok = wanted <= v <= bound
                    elif typ == 4: ok = True
                    elif typ == 5: ok = isinstance(v,(int,float)) and isinstance(old,(int,float)) and v > old
                    elif typ == 6: ok = isinstance(v,(int,float)) and isinstance(old,(int,float)) and v-old == wanted
                    elif typ == 7: ok = isinstance(v,(int,float)) and isinstance(old,(int,float)) and v < old
                    elif typ == 8: ok = isinstance(v,(int,float)) and isinstance(old,(int,float)) and old-v == wanted
                    elif typ == 9: ok = v != old
                    elif typ == 10: ok = v == old
                    elif typ == 11: ok = False
                    elif typ == 12: ok = str(wanted) in str(v)
                    elif typ == 13: ok = str(v).startswith(str(wanted))
                    elif typ == 14: ok = str(v).endswith(str(wanted))
                    elif typ == 15: ok = bool(re.search(str(wanted), str(v)))
                except (TypeError, ValueError, re.error): ok = False
                if ok: found[k] = v
            self._finalizar_escaneo(found)
        except asyncio.TimeoutError: self._error_escaneo(TimeoutError(self.tr("Scan timed out")))
        except Exception as exc: self._error_escaneo(exc)

    @staticmethod
    def interpretar_valor(value):
        # Imported JSON may contain native numbers, booleans, or null; only
        # string inputs need trimming and textual parsing.
        if not isinstance(value, str):
            return value
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

    def escanear(self, rescan=False):
        if not self._connected or not self.handler:
            QMessageBox.warning(self, self.tr("Not connected"), self.tr("Launch a Tyrano game before scanning."))
            return
        if self.NameRadioButton.isChecked() and not self.ScanInput.text().strip():
            QMessageBox.information(self, self.tr("Search"), self.tr("Enter a variable name (empty searches are disabled)."))
            return
        self._scan_started = time.perf_counter()
        self._log(f"Scan started ({'name' if self.NameRadioButton.isChecked() else self.SearchTypeInput.currentText()})")
        if not rescan:
            self._scan_candidates = None
            self._scan_history.clear()
            self._scan_snapshot.clear()
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

    def _cerrar_websocket_seguro(self):
        """Close the active CDP/WebSocket handler if it provides a close method."""
        handler = getattr(self, "handler", None)
        if handler is None:
            return
        close = getattr(handler, "close", None) or getattr(handler, "close_websocket", None)
        if callable(close):
            try:
                result = close()
                if asyncio.iscoroutine(result):
                    asyncio.run_coroutine_threadsafe(result, self.persistent_async.loop)
            except Exception as exc:
                self._log(f"WebSocket close warning: {exc}")

    def detener_juego(self):
        self._pause_polling = True
        self._connected = False

        if self.handler is not None:
            self._cerrar_websocket_seguro()

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
        from core.themeloader import ThemeLoader
        path = theme if os.path.isdir(theme) else os.path.join("theme", theme)
        qss_files = [os.path.join(path, f) for f in os.listdir(path)] if os.path.isdir(path) else []
        qss_files = [f for f in qss_files if f.lower().endswith(".qss")]
        if qss_files:
            with open(qss_files[0], encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            config.guardar_valor_configuracion("app", "theme", theme)
        else:
            QMessageBox.warning(self, self.tr("Theme"), self.tr("No QSS stylesheet found in selected theme folder."))

    def cargar_tema_personalizado(self):
        path = QFileDialog.getExistingDirectory(self, self.tr("Select theme folder"), "")
        if path:
            self.aplicar_tema(path)

    def mostrar_configuracion(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QCheckBox, QComboBox, QLineEdit
        dialog = QDialog(self); dialog.setWindowTitle(self.tr("Settings")); layout = QFormLayout(dialog)
        port=QSpinBox(); port.setRange(1024,65535); port.setValue(int(config.obtener_valor_configuracion("websocket","port")))
        language=QComboBox(); language.addItems(["English","Español"]); language.setCurrentIndex(1 if self.language=="es" else 0)
        timeout=QSpinBox(); timeout.setRange(1,600); timeout.setValue(int(config.obtener_valor_configuracion("scan","timeout")))
        root=QComboBox(); root.addItems(["TF","F","SF","All"]); root.setCurrentIndex({"tf":0,"f":1,"sf":2,"all":3}.get(config.obtener_valor_configuracion("scan","root"),0))
        ignore_null=QCheckBox(); ignore_null.setChecked(bool(config.obtener_valor_configuracion("scan","ignore_null")))
        ignore_ro=QCheckBox(); ignore_ro.setChecked(bool(config.obtener_valor_configuracion("scan","ignore_readonly")))
        logpath=QLineEdit(str(config.obtener_valor_configuracion("scan","log_path") or ""))
        theme=QLineEdit(str(config.obtener_valor_configuracion("app","theme")))
        layout.addRow(self.tr("WebSocket port"),port); layout.addRow(self.tr("Language"),language); layout.addRow(self.tr("Scan timeout (seconds)"),timeout)
        layout.addRow(self.tr("Root scan location"),root); layout.addRow(self.tr("Ignore null/empty"),ignore_null); layout.addRow(self.tr("Ignore read-only (best effort)"),ignore_ro)
        layout.addRow(self.tr("Log file path (optional)"),logpath); layout.addRow(self.tr("Theme folder name"),theme)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addRow(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            config.guardar_valor_configuracion("websocket","port",port.value()); self.language="es" if language.currentIndex() else "en"; config.guardar_valor_configuracion("app","language",self.language)
            self._scan_timeout=timeout.value(); self._root_location=["tf","f","sf","all"][root.currentIndex()]; self._ignore_null=ignore_null.isChecked(); self._ignore_readonly=ignore_ro.isChecked(); self._log_path=logpath.text().strip() or None
            for k,v in [("timeout",self._scan_timeout),("root",self._root_location),("ignore_null",self._ignore_null),("ignore_readonly",self._ignore_readonly),("log_path",self._log_path)]: config.guardar_valor_configuracion("scan",k,v)
            self.traducir_interfaz(); self.aplicar_tema(theme.text().strip())

    def mostrar_tutorial(self):
        if self.language == "es":
            text = ("TUTORIAL — Tyrano Cheat Engine\n\n"
                    "1. Conectar un juego\nInicia el juego con «Iniciar juego…». La herramienta se conecta al juego para leer sus variables.\n\n"
                    "2. Buscar variables\nElige «Valor» para buscar un valor conocido o «Nombre de variable» para buscar por nombre. Pulsa «Escanear». Usa los tipos de búsqueda para acotar resultados.\n\n"
                    "3. Editar y congelar\nHaz doble clic en un resultado para añadirlo a la lista de valores. Edita el valor y confirma; marca la casilla para intentar mantenerlo fijo mientras el juego está conectado.\n\n"
                    "4. Importar / exportar lista\nEn «Lista sin procesar», pulsa «Importar lista» para leer JSON o TXT. Marca una fila para añadirla a la lista de valores. «Exportar lista» guarda las filas cargadas en JSON (con nombre, ruta y valor) o TXT (rutas).\n\n"
                    "5. Ajustes y ayuda\nEn Configuración puedes cambiar idioma, puerto, tiempo y opciones de escaneo. El menú Vista cambia tema e idioma. Detener juego cierra la conexión y el proceso iniciado.\n\n"
                    "Nota: una ruta importada debe corresponder a una variable válida del juego.")
        else:
            text = ("TUTORIAL — Tyrano Cheat Engine\n\n"
                    "1. Connect a game\nStart the game with “Launch Game…”. The tool connects to the game to read its variables.\n\n"
                    "2. Search variables\nChoose “Value” to search for a known value or “Variable name” to search by name. Press “Scan”. Use scan types to narrow results.\n\n"
                    "3. Edit and freeze\nDouble-click a result to add it to the value list. Edit its value and confirm; check the box to try to keep it fixed while the game is connected.\n\n"
                    "4. Import / export lists\nIn “Raw List”, click “Import list” to read JSON or TXT. Check a row to add it to the value list. “Export list” saves loaded rows as JSON (name, path, value) or TXT (paths).\n\n"
                    "5. Settings and help\nSettings lets you change language, port, timeout, and scan options. View switches theme and language. Stop Game closes the connection and launched process.\n\n"
                    "Note: an imported path must match a valid variable in the game.")
        QMessageBox.information(self, self.tr("Tutorial"), text)

    def mostrar_acerca(self):
        QMessageBox.about(self, self.tr("About"), self.tr("Tyrano Cheat Engine\nTyrano game variable inspector and editor."))

    def guardar_registros(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save logs"), "", "Text files (*.txt)")
        if path:
            self._log_path = path
            config.guardar_valor_configuracion("scan", "log_path", path)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.LogLineEdit.toPlainText())
            self._log(self.tr("Logging enabled"))

    def cargar_lista_cruda(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Import list"), "", "JSON files (*.json);;Text files (*.txt);;All files (*)")
        if not path: return
        try:
            with open(path, encoding="utf-8") as f: content = f.read()
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            if isinstance(data, dict):
                data = data.get("items", data)
                if isinstance(data, dict): data = [{"name": k, "path": k, "value": v} for k, v in data.items()]
            if not isinstance(data, list): raise ValueError(self.tr("The file must contain a JSON list, object, or text lines."))
            self.RawListWidget.clear()
            for entry in data:
                if isinstance(entry, str): name, route, value = entry, entry, "??"
                elif isinstance(entry, dict): name, route, value = entry.get("name", entry.get("description", entry.get("path", ""))), entry.get("path", entry.get("route", "")), entry.get("value", "??")
                else: continue
                if not route: continue
                item = QTreeWidgetItem(self.RawListWidget, [str(name), str(route), str(value)])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)
            self._lpb_value = 100
            QMessageBox.information(self, self.tr("Import list"), self.tr("List imported successfully."))
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Import error"), str(exc))

    def exportar_lista(self):
        # Export the actual tracked lists, not only the import staging widget.
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export list"), "tyrano_list.json", "JSON files (*.json);;Text files (*.txt)")
        if not path:
            return
        try:
            rows = []
            seen = set()
            def add_row(name, route, value):
                route = str(route or "").strip()
                if not route or route == "??" or route in seen:
                    return
                seen.add(route)
                rows.append({"name": str(name or route), "path": route, "value": str(value)})

            # Raw/imported rows, including unchecked rows, are explicitly part of the list.
            for i in range(self.RawListWidget.topLevelItemCount()):
                item = self.RawListWidget.topLevelItem(i)
                add_row(item.text(0), item.text(1), item.text(2))
            # Also include variables already added to the value list and scan results.
            for item in getattr(self, "_tree_list_items", []):
                add_row(item.text(0), item.text(1), item.text(2))
            for item in getattr(self, "_rt_list_items", []):
                add_row(item.text(0), item.text(3), item.text(1))
            if not rows:
                QMessageBox.warning(self, self.tr("Export list"), self.tr("The list is empty. Add or import variables before exporting."))
                return
            if path.lower().endswith(".txt"):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(row["path"] for row in rows) + "\n")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"format": "tyrano-cheat-engine-list", "version": 1, "items": rows}, f, ensure_ascii=False, indent=2)
            # Read back and validate the saved artifact so empty/bad exports are not reported as success.
            if path.lower().endswith(".txt"):
                with open(path, encoding="utf-8") as f:
                    saved_count = sum(1 for line in f if line.strip())
            else:
                with open(path, encoding="utf-8") as f:
                    saved = json.load(f)
                saved_count = len(saved.get("items", []))
            if saved_count != len(rows) or saved_count == 0:
                raise ValueError(f"Export verification failed: expected {len(rows)} entries, found {saved_count}.")
            QMessageBox.information(self, self.tr("Export list"), f"{self.tr('List exported successfully.')} ({saved_count})")
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Export error"), str(exc))

    def descargar_lista_cruda(self):
        self.RawListWidget.clear(); self._lpb_value = 0


    def _log(self, message):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{stamp}] {message}"
        if hasattr(self, "LogLineEdit"):
            self.LogLineEdit.append(line)
        if self._log_path:
            try:
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except OSError as exc:
                if hasattr(self, "LogLineEdit"):
                    self.LogLineEdit.append(f"Log file error: {exc}")

    def _raw_item_changed(self, item, column):
        if column != 0 or item.checkState(0) != Qt.CheckState.Checked: return
        route = item.text(1)
        if route and route != "??":
            self.agregar_variable_a_lista(item.text(0), route, item.text(2), self.ValueListWidget)

    def _aplicar_congelado(self):
        # Reapply each pinned value through the persistent asyncio loop. Do not
        # invoke the decorated slot directly from the Qt timer (that can block
        # the GUI or run it on the wrong event loop).
        if not self._frozen or not self._connected or not self.handler:
            return
        for path, value in list(self._frozen.items()):
            try:
                self.set_value(path, value)
            except Exception as exc:
                self._log(f"Freeze failed for {path}: {exc!r}")

    def toggle_freeze(self, item, column):
        if column != 0:
            return
        path = item.text(1).strip()
        if not path:
            return
        if item.checkState(0) == Qt.CheckState.Checked:
            try:
                # Capture the current displayed value as a typed Python value.
                self._frozen[path] = self.interpretar_valor(item.text(2))
                self._log(f"Frozen {path} = {self._frozen[path]!r}")
            except Exception as exc:
                item.setCheckState(0, Qt.CheckState.Unchecked)
                self._log(f"Could not freeze {path}: {exc!r}")
                return
        else:
            self._frozen.pop(path, None)
            self._log(f"Unfrozen {path}")
        if self._frozen:
            if not self._freeze_timer.isActive():
                self._freeze_timer.start(500)
        else:
            self._freeze_timer.stop()


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
