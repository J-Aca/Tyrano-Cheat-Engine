import json
import os

from ui.widget import (
    CustomEditTreeWidget,
    CustomCheckboxDelegate,
    CustomTreeWidget,
)
from ui.dialog import EditValueDialog

from PySide6.QtWidgets import (
    QMainWindow,
    QDialog,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QLineEdit,
    QTreeWidgetItem,
    QProgressBar,
    QSizePolicy,
    QAbstractItemView,
    QPushButton,
    QSpacerItem,
    QRadioButton,
    QTabWidget,
    QGridLayout,
    QComboBox,
    QMenuBar,
    QMenu,
    QLayout,
    QTextEdit,
    QStackedWidget,
    QColorDialog,
    QMessageBox,
)
from PySide6.QtCore import (
    QMetaObject,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QFont,
    QBrush,
    QColor,
    QIcon,
)


class InterfazJAca(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1111, 874)

        font = QFont()
        font.setPointSize(9)
        self.setFont(font)

        icon_path = os.path.join(
            "resources",
            "app-icon.ico",
        )

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)

        self._crear_barra_menu(font)
        self._crear_interfaz_principal(font)

        QMetaObject.connectSlotsByName(self)

        self._rt_list_items = []
        self._tree_list_items = []

        self._pause_polling = False
        self._polling_paused = False
        self._connected = False

        self.traducir_interfaz()

    def _crear_barra_menu(self, font):
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(
            QRect(0, 0, 1111, 21)
        )

        self.menuFile = QMenu(self.menubar)
        self.menuSettings = QMenu(self.menubar)
        self.menuHelp = QMenu(self.menubar)
        self.menuView = QMenu(self.menubar)

        self.setMenuBar(self.menubar)

        self.actionLaunch_Game = QAction(self)
        self.actionStop_Game = QAction(self)
        self.actionSave_Logs = QAction(self)

        self.actionTutorial = QAction(self)
        self.actionAbout = QAction(self)
        self.actionTheme = QAction(self)
        self.actionLanguage = QAction(self)
        self.actionSettings = QAction(self)

        self.menubar.addAction(
            self.menuFile.menuAction()
        )
        self.menubar.addAction(
            self.menuSettings.menuAction()
        )
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menuSettings.addAction(self.actionSettings)
        self.menuView.addAction(self.actionTheme)
        self.menuView.addAction(self.actionLanguage)

        self.menuFile.addAction(
            self.actionLaunch_Game
        )
        self.menuFile.addAction(
            self.actionStop_Game
        )

        self.menuFile.addSeparator()
        self.menuFile.addAction(
            self.actionSave_Logs
        )

        self.menuHelp.addAction(self.actionTutorial)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionAbout)

    def _crear_interfaz_principal(self, font):
        base_layout = QVBoxLayout(
            self.centralwidget
        )
        base_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.BaseVLayoutWidget = QWidget(
            self.centralwidget
        )

        base_layout.addWidget(
            self.BaseVLayoutWidget
        )

        self.MainContainer = QVBoxLayout(
            self.BaseVLayoutWidget
        )
        self.MainContainer.setContentsMargins(
            0,
            8,
            0,
            0,
        )

        self.InfoLabel = QLabel(
            self.BaseVLayoutWidget
        )
        self.InfoLabel.setFont(font)
        self.InfoLabel.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.MainContainer.addWidget(
            self.InfoLabel
        )

        self._crear_seccion_busqueda(font)
        self._crear_seccion_variables(font)

    def _crear_seccion_busqueda(self, font):
        self.ActionsSection = QTabWidget(
            self.BaseVLayoutWidget
        )
        self.ActionsSection.setFont(font)

        self.ScanTab = QWidget()
        scan_layout = QVBoxLayout(
            self.ScanTab
        )
        scan_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.ScanProgressBar = QProgressBar()
        self.ScanProgressBar.setTextVisible(False)

        scan_layout.addWidget(
            self.ScanProgressBar
        )

        widgets_layout = QGridLayout()

        self.ResultTab = QTreeWidget()
        self.ResultTab.setMinimumSize(
            QSize(700, 0)
        )
        self.ResultTab.setFont(font)
        self.ResultTab.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )
        self.ResultTab.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.ResultTab.setSortingEnabled(False)
        self.ResultTab.setIndentation(0)
        self.ResultTab.setItemsExpandable(False)
        self.ResultTab.setExpandsOnDoubleClick(False)
        self.ResultTab.setAllColumnsShowFocus(True)
        self.ResultTab.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.ResultTab.doubleClicked.connect(
            self.mover_resultado_a_variables
        )
        self.ResultTab.customContextMenuRequested.connect(
            self.menu_contextual_resultados
        )

        widgets_layout.addWidget(
            self.ResultTab,
            0,
            0,
        )

        controls = QVBoxLayout()
        controls.setSizeConstraint(
            QLayout.SizeConstraint.SetFixedSize
        )

        buttons = QGridLayout()
        buttons.setHorizontalSpacing(15)

        self.ScanButton = QPushButton()
        self.ClearButton = QPushButton()
        self.UndoButton = QPushButton()

        self.ClearButton.setEnabled(False)
        self.UndoButton.setEnabled(False)

        buttons.addWidget(
            self.ScanButton,
            0,
            0,
        )
        buttons.addWidget(
            self.ClearButton,
            0,
            1,
        )
        buttons.addWidget(
            self.UndoButton,
            0,
            2,
        )

        controls.addLayout(buttons)

        self.ScanInputContainer = QStackedWidget()

        normal_page = QWidget()
        normal_layout = QVBoxLayout(
            normal_page
        )
        normal_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.ScanInput = QLineEdit()
        self.ScanInput.returnPressed.connect(
            self.ScanButton.click
        )

        normal_layout.addWidget(
            self.ScanInput
        )

        self.ScanInputContainer.addWidget(
            normal_page
        )

        double_page = QWidget()
        double_layout = QGridLayout(
            double_page
        )
        double_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.ScanInputA = QLineEdit()
        self.SearchAndLabel = QLabel()
        self.ScanInputB = QLineEdit()

        self.SearchAndLabel.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        double_layout.addWidget(
            self.ScanInputA,
            0,
            0,
        )
        double_layout.addWidget(
            self.SearchAndLabel,
            0,
            1,
        )
        double_layout.addWidget(
            self.ScanInputB,
            0,
            2,
        )

        self.ScanInputA.returnPressed.connect(
            self.ScanInputB.setFocus
        )
        self.ScanInputB.returnPressed.connect(
            self.ScanButton.click
        )

        self.ScanInputContainer.addWidget(
            double_page
        )

        self.IgnoreInputScanPage = QWidget()

        self.ScanInputContainer.addWidget(
            self.IgnoreInputScanPage
        )

        controls.addWidget(
            self.ScanInputContainer
        )

        search_by = QHBoxLayout()

        self.SearchByLabel = QLabel()
        self.ValueRadioButton = QRadioButton()
        self.NameRadioButton = QRadioButton()

        self.ValueRadioButton.setChecked(True)

        self.ValueRadioButton.toggled.connect(
            self._actualizar_modo_busqueda
        )

        search_by.addWidget(
            self.SearchByLabel
        )
        search_by.addWidget(
            self.ValueRadioButton
        )
        search_by.addWidget(
            self.NameRadioButton
        )
        search_by.addStretch()

        controls.addLayout(search_by)

        constraints = QGridLayout()

        self.SearchTypeLabel = QLabel()
        self.SearchTypeInput = QComboBox()

        self.SearchTypeInput.currentIndexChanged.connect(
            self._actualizar_tipo_busqueda
        )

        constraints.addWidget(
            self.SearchTypeLabel,
            0,
            0,
        )
        constraints.addWidget(
            self.SearchTypeInput,
            0,
            1,
        )

        controls.addLayout(
            constraints
        )

        controls.addStretch()

        self.FoundLabel = QLabel()
        controls.addWidget(
            self.FoundLabel
        )

        widgets_layout.addLayout(
            controls,
            0,
            1,
        )

        widgets_layout.setColumnStretch(
            0,
            1,
        )

        scan_layout.addLayout(
            widgets_layout
        )

        self.ActionsSection.addTab(
            self.ScanTab,
            "Scan",
        )

        self.LogTab = QWidget()

        log_layout = QVBoxLayout(
            self.LogTab
        )
        log_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.LogLineEdit = QTextEdit()
        self.LogLineEdit.setReadOnly(True)
        self.LogLineEdit.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        log_layout.addWidget(
            self.LogLineEdit
        )

        self.ActionsSection.addTab(
            self.LogTab,
            "Logs",
        )

        self.MainContainer.addWidget(
            self.ActionsSection
        )

    def _crear_seccion_variables(self, font):
        self.ValueListsSection = QTabWidget(
            self.BaseVLayoutWidget
        )
        self.ValueListsSection.setFont(font)

        self.ValueListTab = QWidget()

        value_layout = QVBoxLayout(
            self.ValueListTab
        )
        value_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.ValueListWidget = CustomTreeWidget()

        self.ValueListWidget.setSortingEnabled(False)
        self.ValueListWidget.setDragEnabled(True)
        self.ValueListWidget.setAcceptDrops(True)
        self.ValueListWidget.setDropIndicatorShown(True)
        self.ValueListWidget.setAllColumnsShowFocus(True)

        self.ValueListWidget.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.ValueListWidget.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )
        self.ValueListWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.ValueListWidget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.ValueListWidget.setItemDelegateForColumn(
            0,
            CustomCheckboxDelegate(
                self.ValueListWidget
            ),
        )

        self.ValueListWidget.customContextMenuRequested.connect(
            self.menu_contextual_variables
        )
        self.ValueListWidget.itemDoubleClicked.connect(
            self.editar_variable_emergente
        )

        value_layout.addWidget(
            self.ValueListWidget
        )

        self.ValueListsSection.addTab(
            self.ValueListTab,
            "Value List",
        )

        self.RawListTab = QWidget()

        raw_layout = QVBoxLayout(
            self.RawListTab
        )
        raw_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.LoadProgressBar = QProgressBar()
        self.LoadProgressBar.setTextVisible(False)

        raw_layout.addWidget(
            self.LoadProgressBar
        )

        self.LoadButton = QPushButton()

        raw_layout.addWidget(
            self.LoadButton
        )

        self.UnloadButton = QPushButton()

        raw_layout.addWidget(
            self.UnloadButton
        )

        self.RawListWidget = CustomEditTreeWidget(
            [0]
        )

        self.RawListWidget.setExpandsOnDoubleClick(False)
        self.RawListWidget.setAllColumnsShowFocus(True)
        self.RawListWidget.setItemDelegateForColumn(
            0,
            CustomCheckboxDelegate(
                self.RawListWidget
            ),
        )

        raw_layout.addWidget(
            self.RawListWidget
        )

        self.ValueListsSection.addTab(
            self.RawListTab,
            "Raw List",
        )

        self.MainContainer.addWidget(
            self.ValueListsSection
        )

    def traducir_interfaz(self):
        es = getattr(self, "language", "en") == "es"
        tr = lambda en, es_text: es_text if es else en
        self.setWindowTitle("Tyrano Cheat Engine")
        self.menuFile.setTitle(tr("File", "Archivo")); self.menuSettings.setTitle(tr("Settings", "Configuración")); self.menuView.setTitle(tr("View", "Vista")); self.menuHelp.setTitle(tr("Help", "Ayuda"))
        labels = [(self.actionLaunch_Game,"Launch Game...","Iniciar juego..."),(self.actionStop_Game,"Stop Game","Detener juego"),(self.actionSave_Logs,"Save Logs...","Guardar registros..."),(self.actionTheme,"Toggle light/dark theme","Cambiar tema claro/oscuro"),(self.actionLanguage,"Switch English / Spanish","Cambiar inglés / español"),(self.actionSettings,"Settings...","Configuración..."),(self.actionTutorial,"Tutorial / Help","Tutorial / Ayuda"),(self.actionAbout,"About","Acerca de")]
        for action,en,es_text in labels: action.setText(tr(en,es_text))
        self.InfoLabel.setText(tr("No game loaded","Ningún juego cargado"))
        for widget,en,es_text in [(self.ScanButton,"Scan","Escanear"),(self.ClearButton,"Clear","Limpiar"),(self.UndoButton,"Rescan","Reescanear"),(self.SearchAndLabel,"and","y"),(self.SearchByLabel,"Scan by","Buscar por"),(self.ValueRadioButton,"Value","Valor"),(self.NameRadioButton,"Variable name","Nombre de variable"),(self.SearchTypeLabel,"Scan type","Tipo de escaneo"),(self.LoadButton,"Load raw list","Cargar lista"),(self.UnloadButton,"Unload","Descargar")]: widget.setText(tr(en,es_text))
        self.SearchTypeInput.clear()
        for en,es_text in [("Exact value","Valor exacto"),("Bigger than...","Mayor que..."),("Smaller than...","Menor que..."),("Between...","Entre..."),("Unknown","Desconocido"),("Increased value","Valor aumentado"),("Increased by...","Aumentado en..."),("Decreased value","Valor reducido"),("Decreased by...","Reducido en..."),("Changed value","Valor cambiado"),("Unchanged value","Valor sin cambios"),("Ignore","Ignorar"),("Contains ...","Contiene..."),("Starts with...","Empieza con..."),("Ends with...","Termina con..."),("Regex","Expresión regular")]: self.SearchTypeInput.addItem(tr(en,es_text))
        self.FoundLabel.setText(tr("Found: 0","Encontrados: 0"))
        self.ResultTab.setHeaderLabels([tr("Variable","Variable"),tr("Value","Valor"),tr("Previous","Anterior"),tr("Path","Ruta")])
        self.ValueListWidget.setHeaderLabels([tr("Description","Descripción"),tr("Path","Ruta"),tr("Value","Valor")])
        self.RawListWidget.setHeaderLabels([tr("Description","Descripción"),tr("Path","Ruta"),tr("Value","Valor")])
        self.ActionsSection.setTabText(0,tr("Scan","Escaneo")); self.ActionsSection.setTabText(1,tr("Logs","Registros"))
        self.ValueListsSection.setTabText(0,tr("Value List","Lista de valores")); self.ValueListsSection.setTabText(1,tr("Raw List","Lista sin procesar"))

    def _actualizar_modo_busqueda(self):
        if self.ValueRadioButton.isChecked():
            self.SearchTypeInput.setEnabled(True)
            self._actualizar_tipo_busqueda()
        else:
            self.SearchTypeInput.setEnabled(False)
            self.ScanInputContainer.setCurrentIndex(0)

    def _actualizar_tipo_busqueda(self):
        no_input = {
            "Unknown",
            "Ignore",
            "Increased value",
            "Decreased value",
            "Changed value",
            "Unchanged value",
        }

        current = self.SearchTypeInput.currentText()

        if current in no_input or current in {"Desconocido", "Ignorar", "Valor aumentado", "Valor reducido", "Valor cambiado", "Valor sin cambios"}:
            self.ScanInputContainer.setCurrentIndex(2)
        elif current in {"Between...", "Entre..."}:
            self.ScanInputContainer.setCurrentIndex(1)
        else:
            self.ScanInputContainer.setCurrentIndex(0)

    def agregar_variable_a_lista(
        self,
        name,
        path,
        value,
        parent,
    ):
        if not isinstance(value, str):
            value = json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )

        item = QTreeWidgetItem(
            parent,
            [
                name,
                path,
                value,
            ],
        )

        item.setFlags(
            item.flags()
            & ~Qt.ItemFlag.ItemIsDropEnabled
            | Qt.ItemFlag.ItemIsUserCheckable
        )

        item.setCheckState(
            0,
            Qt.CheckState.Unchecked,
        )

        item.setForeground(
            0,
            QBrush(
                QColor(
                    255,
                    255,
                    255,
                )
            ),
        )

        self._tree_list_items.append(item)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)

    def mover_resultado_a_variables(self, index):
        item = self.ResultTab.itemFromIndex(index)

        if item is None:
            return

        self.agregar_variable_a_lista(
            item.text(0),
            item.text(3),
            item.text(1),
            self.ValueListWidget,
        )

    def editar_variable_emergente(self, item, column):
        header = self.ValueListWidget.headerItem().text(
            column
        )
        value = item.text(column)

        if not item.text(1) and column:
            return

        dialog = EditValueDialog(
            f"Change {header}",
            value,
            self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not dialog.new_value:
                return

            item.setText(
                column,
                dialog.new_value,
            )

            if column == 2:
                self.set_value(
                    item.text(1),
                    item.text(2),
                )

    def menu_contextual_resultados(self, position):
        items = self.ResultTab.selectedItems()

        if not items:
            return

        menu = QMenu(self)

        add_selected = menu.addAction(
            "Add selected variables to value list"
        )
        change_value = menu.addAction(
            "Change value of selected variables"
        )
        change_previous = menu.addAction(
            "Change value of selected variables to previous value"
        )
        remove_selected = menu.addAction(
            "Remove selected variables"
        )

        action = menu.exec(
            self.ResultTab.viewport().mapToGlobal(
                position
            )
        )

        if action == add_selected:
            for item in items:
                self.agregar_variable_a_lista(
                    item.text(0),
                    item.text(3),
                    item.text(1),
                    self.ValueListWidget,
                )

        elif action == change_value:
            dialog = EditValueDialog(
                "Change Value",
                items[0].text(1),
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                for item in items:
                    item.setText(
                        1,
                        dialog.new_value,
                    )
                    self.set_value(
                        item.text(3),
                        dialog.new_value,
                    )

        elif action == change_previous:
            for item in items:
                item.setText(
                    1,
                    item.text(2),
                )
                self.set_value(
                    item.text(3),
                    item.text(2),
                )

        elif action == remove_selected:
            for item in items:
                if item in self._rt_list_items:
                    self._rt_list_items.remove(item)

                index = self.ResultTab.indexOfTopLevelItem(
                    item
                )

                if index >= 0:
                    self.ResultTab.takeTopLevelItem(
                        index
                    )

    def menu_contextual_variables(self, position):
        items = self.ValueListWidget.selectedItems()

        if not items:
            self._menu_variables_vacio(position)
        else:
            self._menu_contextual_variable(
                items,
                position,
            )

    def _menu_variables_vacio(self, position):
        menu = QMenu(self)

        create_item = menu.addAction(
            "Create Item"
        )

        menu.addSeparator()

        create_header = menu.addAction(
            "Create Header"
        )

        action = menu.exec(
            self.ValueListWidget.viewport().mapToGlobal(
                position
            )
        )

        if action == create_item:
            dialog = EditValueDialog(
                "Create Item",
                "",
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                self.agregar_variable_a_lista(
                    dialog.new_value,
                    "path",
                    "??",
                    self.ValueListWidget,
                )

        elif action == create_header:
            dialog = EditValueDialog(
                "Create Header",
                "",
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                item = QTreeWidgetItem(
                    self.ValueListWidget,
                    [
                        dialog.new_value,
                        "",
                        "",
                    ],
                )

                item.setForeground(
                    0,
                    QBrush(
                        QColor(
                            255,
                            255,
                            255,
                        )
                    ),
                )

    def _eliminar_variables(self, items):
        for item in list(items):
            parent = item.parent()
            children = item.takeChildren()

            is_group = (
                not item.text(1)
                and not item.text(2)
            )

            if children:
                self._eliminar_variables(
                    children
                )

            if parent is None:
                index = self.ValueListWidget.indexOfTopLevelItem(
                    item
                )

                if index >= 0:
                    self.ValueListWidget.takeTopLevelItem(
                        index
                    )
            else:
                self.ValueListWidget.removeChildItem(
                    parent,
                    item,
                )

            if not is_group and item in self._tree_list_items:
                self._tree_list_items.remove(item)

    def _menu_contextual_variable(
        self,
        items,
        position,
    ):
        menu = QMenu(self)

        item_text = (
            "Item"
            if len(items) == 1
            else "Items"
        )

        delete_item = menu.addAction(
            f"Delete {item_text}"
        )

        edit_sub_menu = menu.addMenu(
            "Change"
        )

        edit_name = edit_sub_menu.addAction(
            "Name"
        )
        edit_path = edit_sub_menu.addAction(
            "Path"
        )
        edit_value = edit_sub_menu.addAction(
            "Value"
        )

        change_color = menu.addAction(
            "Change Color"
        )
        create_item = menu.addAction(
            "Create Item"
        )

        menu.addSeparator()

        create_header = menu.addAction(
            "Create Header"
        )

        action = menu.exec(
            self.ValueListWidget.viewport().mapToGlobal(
                position
            )
        )

        if action == delete_item:
            confirmation = QMessageBox.question(
                self,
                "Confirm",
                f"Are you sure you want to delete "
                f"{len(items)} {item_text}?",
            )

            if confirmation != QMessageBox.StandardButton.Yes:
                return

            self._eliminar_variables(items)

        elif action == edit_name:
            dialog = EditValueDialog(
                "Change Name",
                items[0].text(0),
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                for item in items:
                    item.setText(
                        0,
                        dialog.new_value,
                    )

        elif action == edit_path:
            dialog = EditValueDialog(
                "Change Path",
                items[0].text(1),
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                for item in items:
                    if not item.text(1) and not item.text(2):
                        continue

                    item.setText(
                        1,
                        dialog.new_value,
                    )

        elif action == edit_value:
            dialog = EditValueDialog(
                "Change Value",
                items[0].text(2),
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                for item in items:
                    if not item.text(1) and not item.text(2):
                        continue

                    item.setText(
                        2,
                        dialog.new_value,
                    )

                    self.set_value(
                        item.text(1),
                        item.text(2),
                    )

        elif action == change_color:
            color = QColorDialog.getColor(
                parent=self
            )

            if color.isValid():
                for item in items:
                    for column in range(3):
                        item.setForeground(
                            column,
                            QBrush(color),
                        )

        elif action == create_item:
            dialog = EditValueDialog(
                "Create Item",
                "",
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                self.agregar_variable_a_lista(
                    dialog.new_value,
                    "path",
                    "??",
                    self.ValueListWidget,
                )

        elif action == create_header:
            dialog = EditValueDialog(
                "Create Header",
                "",
                self,
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not dialog.new_value:
                    return

                item = QTreeWidgetItem(
                    self.ValueListWidget,
                    [
                        dialog.new_value,
                        "",
                        "",
                    ],
                )

                item.setForeground(
                    0,
                    QBrush(
                        QColor(
                            255,
                            255,
                            255,
                        )
                    ),
                )
