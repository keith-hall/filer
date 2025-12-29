"""
Qt models for file system data representation.
"""
from pathlib import Path
from typing import Optional, List, Generator
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant, QTimer, pyqtSignal
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
    
    # Signal emitted when loading is complete
    loading_complete = pyqtSignal()
    
    def __init__(self, backend: FileSystemBackend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.entries: List[FileEntry] = []
        self._loading_generator: Optional[Generator[FileEntry, None, None]] = None
        self._loading_timer: Optional[QTimer] = None
        self._temp_entries: List[FileEntry] = []
        self.refresh()
    
    def refresh(self):
        """Refresh the file list from backend."""
        self.beginResetModel()
        try:
            self.entries = self.backend.list_directory()
        except PermissionError:
            self.entries = []
        self.endResetModel()
    
    def refresh_streaming(self):
        """
        Refresh the file list using streaming mode.
        
        This method initiates a streaming refresh that progressively adds
        entries to the model as they are discovered, providing better
        responsiveness for large directories.
        """
        # Cancel any ongoing loading
        self._cancel_loading()
        
        # Clear current entries
        self.beginResetModel()
        self.entries = []
        self._temp_entries = []
        self.endResetModel()
        
        # Start streaming
        try:
            self._loading_generator = self.backend.list_directory_streaming()
            self._loading_timer = QTimer()
            self._loading_timer.timeout.connect(self._load_next_batch)
            self._loading_timer.start(0)  # Process as fast as possible
        except PermissionError:
            self.entries = []
            self.loading_complete.emit()
    
    def _load_next_batch(self):
        """Load next batch of entries from the generator."""
        if self._loading_generator is None:
            return
        
        # Process multiple entries per timer tick for better performance
        batch_size = 50  # Adjust based on performance needs
        
        try:
            for _ in range(batch_size):
                entry = next(self._loading_generator)
                self._temp_entries.append(entry)
        except StopIteration:
            # Finished loading all entries
            self._finish_loading()
        except Exception as e:
            # Handle any errors during loading
            self._cancel_loading()
            print(f"Error during directory loading: {e}")
    
    def _finish_loading(self):
        """Finish the loading process and sort entries."""
        # Stop the timer and clear the generator (but don't clear temp_entries yet)
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self._loading_generator = None
        
        if self._temp_entries:
            # Sort entries: directories first, then by name (case-insensitive)
            self._temp_entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
            
            # Add all sorted entries to the model
            self.beginInsertRows(QModelIndex(), 0, len(self._temp_entries) - 1)
            self.entries = self._temp_entries
            self._temp_entries = []
            self.endInsertRows()
        
        self.loading_complete.emit()
    
    def _cancel_loading(self):
        """Cancel ongoing loading operation."""
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self._loading_generator = None
        self._temp_entries = []
    
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
