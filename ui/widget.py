from typing import Union

from PySide6.QtWidgets import (
    QTreeWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QStyleOptionButton,
    QApplication,
)
from PySide6.QtCore import Qt, QRect


class CustomCheckboxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        # Let Qt's native item-view style draw and hit-test the checkbox consistently.
        super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if index.column() != 0 or index.data(Qt.ItemDataRole.CheckStateRole) is None:
            return False
        if event.type() in (event.Type.MouseButtonRelease, event.Type.MouseButtonDblClick):
            if event.type() == event.Type.MouseButtonDblClick:
                return True
            state = index.data(Qt.ItemDataRole.CheckStateRole)
            new_state = Qt.CheckState.Unchecked if state == Qt.CheckState.Checked else Qt.CheckState.Checked
            return model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
        if event.type() == event.Type.KeyPress and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Select):
            state = index.data(Qt.ItemDataRole.CheckStateRole)
            new_state = Qt.CheckState.Unchecked if state == Qt.CheckState.Checked else Qt.CheckState.Checked
            return model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
        return False

    def createEditor(self, parent, option, index):
        return None


class NoEditDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None


class CustomEditTreeWidget(QTreeWidget):
    def __init__(
        self,
        non_editable_columns: Union[list, tuple],
        parent=None,
    ):
        super().__init__(parent)

        for column in non_editable_columns:
            self.setItemDelegateForColumn(
                column,
                NoEditDelegate(self),
            )


class CustomTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def dropEvent(self, event):
        super().dropEvent(event)

        item = self.currentItem()

        if item is not None:
            self.itemChanged.emit(item, 1)

    def takeTopLevelItem(self, index):
        item = super().takeTopLevelItem(index)

        if item is not None:
            self.itemChanged.emit(item, 1)

        return item

    def removeChildItem(self, parent, item):
        parent.removeChild(item)

        if item is not None:
            self.itemChanged.emit(item, 1)
