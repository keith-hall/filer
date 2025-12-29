"""
Qt models for file system data representation.
"""
import bisect
import logging
from pathlib import Path
from typing import Optional, List, Generator
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyle

from .filesystem import FileSystemBackend, FileEntry

logger = logging.getLogger(__name__)


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
        self.refresh_streaming()  # Use streaming by default
    
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
        responsiveness for large directories. Entries are inserted in
        sorted order as they arrive.
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
        
        new_entries = []
        try:
            for _ in range(batch_size):
                entry = next(self._loading_generator)
                new_entries.append(entry)
        except StopIteration:
            # Finished loading all entries
            if new_entries:
                self._insert_sorted_entries(new_entries)
            self._finish_loading()
            return
        except Exception as e:
            # Handle any errors during loading
            logger.error(f"Error during directory loading: {e}", exc_info=True)
            self._cancel_loading()
            self.loading_complete.emit()
            return
        
        # Insert new entries in sorted order
        if new_entries:
            self._insert_sorted_entries(new_entries)
    
    def _insert_sorted_entries(self, new_entries: List[FileEntry]):
        """Insert entries in their sorted position."""
        for entry in new_entries:
            # Find insertion position using binary search
            insert_pos = self._find_insert_position(entry)
            
            # Insert the entry
            self.beginInsertRows(QModelIndex(), insert_pos, insert_pos)
            self.entries.insert(insert_pos, entry)
            self.endInsertRows()
    
    def _find_insert_position(self, entry: FileEntry) -> int:
        """
        Find the position to insert an entry to maintain sorted order.
        Sort key: directories first, then by name (case-insensitive).
        """
        # Helper class for bisect to work with our sort key
        class KeyWrapper:
            def __init__(self, iterable, key):
                self.it = iterable
                self.key = key
            
            def __getitem__(self, i):
                return self.key(self.it[i])
            
            def __len__(self):
                return len(self.it)
        
        # Create a key for the entry we're inserting
        entry_key = (not entry.is_dir, entry.name.lower())
        
        # Use bisect to find the insertion position
        wrapped = KeyWrapper(self.entries, lambda e: (not e.is_dir, e.name.lower()))
        return bisect.bisect_left(wrapped, entry_key)
    
    def _finish_loading(self):
        """Finish the loading process."""
        # Stop the timer and clear the generator
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None
        self._loading_generator = None
        self._temp_entries = []
        
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
    
    def add_entry(self, path: Path) -> bool:
        """
        Add a single entry to the model incrementally.
        
        Args:
            path: Path to the file/directory to add
            
        Returns:
            True if entry was added, False if it already exists or path is invalid
        """
        try:
            # Check if entry already exists
            if any(e.path == path for e in self.entries):
                logger.debug(f"Entry already exists: {path}")
                return False
            
            # Create new entry
            entry = FileEntry(path)
            
            # Insert in sorted order
            self._insert_sorted_entries([entry])
            logger.debug(f"Added entry: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add entry {path}: {e}", exc_info=True)
            return False
    
    def remove_entry(self, path: Path) -> bool:
        """
        Remove a single entry from the model incrementally.
        
        Args:
            path: Path to the file/directory to remove
            
        Returns:
            True if entry was removed, False if not found
        """
        try:
            # Find the entry
            for i, entry in enumerate(self.entries):
                if entry.path == path:
                    # Remove the entry
                    self.beginRemoveRows(QModelIndex(), i, i)
                    self.entries.pop(i)
                    self.endRemoveRows()
                    logger.debug(f"Removed entry: {path}")
                    return True
            
            logger.debug(f"Entry not found for removal: {path}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove entry {path}: {e}", exc_info=True)
            return False
    
    def update_entry(self, path: Path) -> bool:
        """
        Update a single entry in the model incrementally.
        
        This refreshes the metadata (size, modified time) for an existing entry.
        
        Args:
            path: Path to the file/directory to update
            
        Returns:
            True if entry was updated, False if not found
        """
        try:
            # Find the entry
            for i, entry in enumerate(self.entries):
                if entry.path == path:
                    # Clear the stat cache to force reload
                    entry._stat_cache = None
                    
                    # Emit dataChanged signal for the row
                    top_left = self.index(i, 0)
                    bottom_right = self.index(i, self.columnCount() - 1)
                    self.dataChanged.emit(top_left, bottom_right)
                    logger.debug(f"Updated entry: {path}")
                    return True
            
            logger.debug(f"Entry not found for update: {path}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update entry {path}: {e}", exc_info=True)
            return False
    
    def move_entry(self, from_path: Path, to_path: Path) -> bool:
        """
        Handle a file/directory move/rename incrementally.
        
        Args:
            from_path: Original path
            to_path: New path
            
        Returns:
            True if move was handled successfully
        """
        try:
            # If both paths are in the same directory (rename), update in place
            if from_path.parent == to_path.parent:
                # Find and update the entry
                for i, entry in enumerate(self.entries):
                    if entry.path == from_path:
                        # Remove old entry
                        self.beginRemoveRows(QModelIndex(), i, i)
                        self.entries.pop(i)
                        self.endRemoveRows()
                        
                        # Add new entry in sorted position
                        new_entry = FileEntry(to_path)
                        self._insert_sorted_entries([new_entry])
                        logger.debug(f"Moved entry: {from_path} -> {to_path}")
                        return True
                
                # Entry not found, might be a new file moving in
                return self.add_entry(to_path)
            else:
                # Moving between directories - handle as remove + add
                removed = self.remove_entry(from_path)
                added = self.add_entry(to_path)
                return removed or added
                
        except Exception as e:
            logger.error(f"Failed to move entry {from_path} -> {to_path}: {e}", exc_info=True)
            return False
