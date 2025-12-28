"""
File pane widget for displaying directory contents.
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QTableView, QHeaderView, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex
from PyQt6.QtGui import QKeyEvent

from ..backend.filesystem import FileSystemBackend
from ..backend.models import FileListModel


class FilePane(QWidget):
    """Widget displaying a file browser pane."""
    
    # Signal emitted when directory changes
    directory_changed = pyqtSignal(Path)
    
    def __init__(self, initial_path: Path = None, parent=None):
        super().__init__(parent)
        self.backend = FileSystemBackend(initial_path)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Path bar
        path_layout = QHBoxLayout()
        
        self.up_button = QPushButton("↑")
        self.up_button.setMaximumWidth(30)
        self.up_button.setToolTip("Go to parent directory")
        self.up_button.clicked.connect(self.go_up)
        path_layout.addWidget(self.up_button)
        
        self.path_edit = QLineEdit()
        self.path_edit.setText(str(self.backend.get_current_path()))
        self.path_edit.returnPressed.connect(self.on_path_entered)
        path_layout.addWidget(self.path_edit)
        
        layout.addLayout(path_layout)
        
        # File list view
        self.file_view = QTableView()
        self.file_view.setShowGrid(False)
        self.file_view.setAlternatingRowColors(True)
        self.file_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.file_view.setSortingEnabled(True)
        self.file_view.verticalHeader().setVisible(False)
        
        # Set up the model
        self.model = FileListModel(self.backend)
        self.file_view.setModel(self.model)
        
        # Configure column widths
        header = self.file_view.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect double-click signal
        self.file_view.doubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.file_view)
        
        # Status bar
        self.status_label = QLabel()
        self.update_status()
        layout.addWidget(self.status_label)
    
    def refresh(self):
        """Refresh the file list."""
        self.model.refresh()
        self.path_edit.setText(str(self.backend.get_current_path()))
        self.update_status()
        self.directory_changed.emit(self.backend.get_current_path())
    
    def update_status(self):
        """Update status label with file count."""
        count = len(self.model.entries)
        dir_count = sum(1 for e in self.model.entries if e.is_dir)
        file_count = count - dir_count
        self.status_label.setText(f"{dir_count} directories, {file_count} files")
    
    def on_item_double_clicked(self, index: QModelIndex):
        """Handle double-click on an item."""
        entry = self.model.get_entry(index)
        if entry and entry.is_dir:
            if self.backend.change_directory(entry.path):
                self.refresh()
    
    def on_path_entered(self):
        """Handle manual path entry."""
        path_text = self.path_edit.text()
        try:
            path = Path(path_text).expanduser().resolve()
            if path.exists() and path.is_dir():
                if self.backend.change_directory(path):
                    self.refresh()
            else:
                # Revert to current path
                self.path_edit.setText(str(self.backend.get_current_path()))
        except Exception:
            # Revert to current path on error
            self.path_edit.setText(str(self.backend.get_current_path()))
    
    def go_up(self):
        """Navigate to parent directory."""
        if self.backend.go_up():
            self.refresh()
    
    def get_current_path(self) -> Path:
        """Get current directory path."""
        return self.backend.get_current_path()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Backspace:
            self.go_up()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            index = self.file_view.currentIndex()
            if index.isValid():
                self.on_item_double_clicked(index)
        else:
            super().keyPressEvent(event)
