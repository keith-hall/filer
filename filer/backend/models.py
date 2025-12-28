"""
Qt models for file system data representation.
"""
from pathlib import Path
from typing import Optional, List
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyle

from .filesystem import FileSystemBackend, FileEntry


class FileListModel(QAbstractTableModel):
    """Model for displaying file list in a table view."""
    
    # Column definitions
    COL_NAME = 0
    COL_SIZE = 1
    COL_TYPE = 2
    COL_MODIFIED = 3
    
    COLUMN_HEADERS = ["Name", "Size", "Type", "Modified"]
    
    def __init__(self, backend: FileSystemBackend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.entries: List[FileEntry] = []
        self.refresh()
    
    def refresh(self):
        """Refresh the file list from backend."""
        self.beginResetModel()
        try:
            self.entries = self.backend.list_directory()
        except PermissionError:
            self.entries = []
        self.endResetModel()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return number of rows."""
        if parent.isValid():
            return 0
        return len(self.entries)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self.COLUMN_HEADERS)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid() or not (0 <= index.row() < len(self.entries)):
            return QVariant()
        
        entry = self.entries[index.row()]
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_NAME:
                return entry.name
            elif col == self.COL_SIZE:
                return entry.format_size()
            elif col == self.COL_TYPE:
                return entry.type_str
            elif col == self.COL_MODIFIED:
                return entry.modified_time.strftime("%Y-%m-%d %H:%M:%S")
        
        elif role == Qt.ItemDataRole.DecorationRole:
            if col == self.COL_NAME:
                # Use system icons for files and folders
                style = QApplication.style()
                if entry.is_dir:
                    icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
                else:
                    icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
                return icon
        
        elif role == Qt.ItemDataRole.UserRole:
            # Store the FileEntry object for easy access
            return entry
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.COLUMN_HEADERS):
                return self.COLUMN_HEADERS[section]
        return QVariant()
    
    def get_entry(self, index: QModelIndex) -> Optional[FileEntry]:
        """Get FileEntry for a given index."""
        if not index.isValid() or not (0 <= index.row() < len(self.entries)):
            return None
        return self.entries[index.row()]
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort the model by the given column."""
        self.beginResetModel()
        
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        if column == self.COL_NAME:
            self.entries.sort(key=lambda e: (not e.is_dir, e.name.lower()), reverse=reverse)
        elif column == self.COL_SIZE:
            self.entries.sort(key=lambda e: (not e.is_dir, e.size), reverse=reverse)
        elif column == self.COL_TYPE:
            self.entries.sort(key=lambda e: (not e.is_dir, e.type_str), reverse=reverse)
        elif column == self.COL_MODIFIED:
            self.entries.sort(key=lambda e: (not e.is_dir, e.modified_time), reverse=reverse)
        
        self.endResetModel()
