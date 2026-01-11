"""
Main window for the file manager application.
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QPushButton, QSplitter, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QKeySequence

from .file_pane import FilePane
from .command_palette import CommandPalette
from .conflict_dialog import ConflictDialog
from ..backend.filesystem import FileOperations, ConflictResolution


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Filer", "FileManager")
        self.clipboard_files: List[Path] = []
        self.clipboard_operation: Optional[str] = None  # "copy" or "move"
        self.init_ui()
        self.setup_command_palette()
        self.restore_settings()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Filer - File Manager")
        self.setMinimumSize(800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create splitter for dual pane layout
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create file panes
        self.left_pane = FilePane(Path.home())
        self.right_pane = FilePane(Path.home())
        
        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.right_pane)
        
        # Set equal sizes initially
        self.splitter.setSizes([400, 400])
        
        main_layout.addWidget(self.splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Track active pane
        self.active_pane = self.left_pane
        self.left_pane.setFocus()
        
        # Style the panes to show which is active
        self.left_pane.setStyleSheet("QWidget { border: 2px solid #4A90E2; }")
        self.right_pane.setStyleSheet("QWidget { border: 2px solid #E0E0E0; }")
        
        # Connect focus events
        self.left_pane.file_view.clicked.connect(lambda: self.set_active_pane(self.left_pane))
        self.right_pane.file_view.clicked.connect(lambda: self.set_active_pane(self.right_pane))
    
    def create_toolbar(self):
        """Create the toolbar with action buttons."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh_active_pane)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Copy action
        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.triggered.connect(self.copy_selected)
        toolbar.addAction(copy_action)
        
        # Cut/Move action
        cut_action = QAction("Cut", self)
        cut_action.setShortcut(QKeySequence("Ctrl+X"))
        cut_action.triggered.connect(self.cut_selected)
        toolbar.addAction(cut_action)
        
        # Paste action
        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence("Ctrl+V"))
        paste_action.triggered.connect(self.paste_files)
        toolbar.addAction(paste_action)
        
        toolbar.addSeparator()
        
        # Toggle pane layout
        toggle_layout_action = QAction("Single Pane", self)
        toggle_layout_action.setShortcut(QKeySequence("Ctrl+D"))
        toggle_layout_action.triggered.connect(self.toggle_pane_layout)
        toolbar.addAction(toggle_layout_action)
        self.toggle_layout_action = toggle_layout_action
        
        toolbar.addSeparator()
        
        # Command palette
        palette_action = QAction("Command Palette", self)
        palette_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        palette_action.triggered.connect(self.show_command_palette)
        toolbar.addAction(palette_action)
        
        toolbar.addSeparator()
        
        # About
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
    
    def setup_command_palette(self):
        """Setup command palette with available commands."""
        self.command_palette = CommandPalette(self)
        
        # Add commands
        self.command_palette.add_command(
            "Refresh",
            "Refresh current pane",
            self.refresh_active_pane
        )
        self.command_palette.add_command(
            "Toggle Layout",
            "Switch between single and dual pane layout",
            self.toggle_pane_layout
        )
        self.command_palette.add_command(
            "Copy Files",
            "Copy selected files to clipboard",
            self.copy_selected
        )
        self.command_palette.add_command(
            "Cut Files",
            "Cut selected files to clipboard (for moving)",
            self.cut_selected
        )
        self.command_palette.add_command(
            "Paste Files",
            "Paste files from clipboard to current directory",
            self.paste_files
        )
        self.command_palette.add_command(
            "Go to Home",
            "Navigate to home directory",
            lambda: self.navigate_to(Path.home())
        )
        self.command_palette.add_command(
            "Go to Root",
            "Navigate to root directory",
            lambda: self.navigate_to(Path.home().anchor if hasattr(Path.home(), 'anchor') else Path("/"))
        )
        self.command_palette.add_command(
            "Focus Left Pane",
            "Set focus to left pane",
            lambda: self.set_active_pane(self.left_pane)
        )
        self.command_palette.add_command(
            "Focus Right Pane",
            "Set focus to right pane",
            lambda: self.set_active_pane(self.right_pane)
        )
    
    def show_command_palette(self):
        """Show the command palette."""
        self.command_palette.show_palette()
    
    def set_active_pane(self, pane: FilePane):
        """Set the active pane."""
        self.active_pane = pane
        
        # Update visual feedback
        if pane == self.left_pane:
            self.left_pane.setStyleSheet("QWidget { border: 2px solid #4A90E2; }")
            self.right_pane.setStyleSheet("QWidget { border: 2px solid #E0E0E0; }")
        else:
            self.left_pane.setStyleSheet("QWidget { border: 2px solid #E0E0E0; }")
            self.right_pane.setStyleSheet("QWidget { border: 2px solid #4A90E2; }")
        
        pane.setFocus()
    
    def refresh_active_pane(self):
        """Refresh the active pane."""
        self.active_pane.refresh()
        self.statusBar().showMessage("Refreshed", 2000)
    
    def toggle_pane_layout(self):
        """Toggle between single and dual pane layout."""
        if self.right_pane.isVisible():
            # Hide right pane (single pane mode)
            self.right_pane.hide()
            self.toggle_layout_action.setText("Dual Pane")
            self.set_active_pane(self.left_pane)
        else:
            # Show right pane (dual pane mode)
            self.right_pane.show()
            self.toggle_layout_action.setText("Single Pane")
    
    def navigate_to(self, path: Path):
        """Navigate active pane to specified path."""
        if self.active_pane.backend.change_directory(path):
            self.active_pane.refresh()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Filer",
            "<h3>Filer File Manager</h3>"
            "<p>A cross-platform GUI file manager inspired by XYplorer, "
            "FMan and Sublime Text.</p>"
            "<p>Version 0.1.0</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Dual pane layout (configurable)</li>"
            "<li>Clean UI with toolbar</li>"
            "<li>Command palette (Ctrl+Shift+P)</li>"
            "<li>Sortable column headings</li>"
            "<li>Keyboard navigation</li>"
            "</ul>"
        )
    
    def restore_settings(self):
        """Restore window settings from previous session."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        splitter_state = self.settings.value("splitter_state")
        if splitter_state:
            self.splitter.restoreState(splitter_state)
    
    def closeEvent(self, event):
        """Save settings before closing."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter_state", self.splitter.saveState())
        event.accept()
    
    def copy_selected(self):
        """Copy selected files to clipboard."""
        selected_files = self.active_pane.get_selected_files()
        if not selected_files:
            self.statusBar().showMessage("No files selected", 2000)
            return
        
        self.clipboard_files = selected_files
        self.clipboard_operation = "copy"
        self.statusBar().showMessage(f"{len(selected_files)} file(s) copied to clipboard", 2000)
    
    def cut_selected(self):
        """Cut selected files to clipboard (for moving)."""
        selected_files = self.active_pane.get_selected_files()
        if not selected_files:
            self.statusBar().showMessage("No files selected", 2000)
            return
        
        self.clipboard_files = selected_files
        self.clipboard_operation = "move"
        self.statusBar().showMessage(f"{len(selected_files)} file(s) cut to clipboard", 2000)
    
    def paste_files(self):
        """Paste files from clipboard to current directory."""
        if not self.clipboard_files:
            self.statusBar().showMessage("Clipboard is empty", 2000)
            return
        
        if not self.clipboard_operation:
            self.statusBar().showMessage("No operation specified", 2000)
            return
        
        destination = self.active_pane.get_current_path()
        
        # Detect conflicts before proceeding
        conflicts = FileOperations.detect_conflicts(self.clipboard_files, destination)
        
        conflict_resolutions = {}
        default_resolution = ConflictResolution.SKIP
        
        # If there are conflicts, show dialog
        if conflicts:
            dialog = ConflictDialog(conflicts, self.clipboard_operation, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                conflict_resolutions, default_resolution = dialog.get_resolutions()
            else:
                self.statusBar().showMessage("Operation cancelled", 2000)
                return
        
        # Perform the operation
        try:
            if self.clipboard_operation == "copy":
                successful, skipped, errors = FileOperations.copy_files(
                    self.clipboard_files,
                    destination,
                    conflict_resolutions,
                    default_resolution
                )
                operation_name = "copied"
            else:  # move
                successful, skipped, errors = FileOperations.move_files(
                    self.clipboard_files,
                    destination,
                    conflict_resolutions,
                    default_resolution
                )
                operation_name = "moved"
                # Clear clipboard after move
                self.clipboard_files = []
                self.clipboard_operation = None
            
            # Refresh both panes
            self.active_pane.refresh()
            if self.active_pane == self.left_pane:
                self.right_pane.refresh()
            else:
                self.left_pane.refresh()
            
            # Show results
            message = f"{successful} file(s) {operation_name}"
            if skipped > 0:
                message += f", {skipped} skipped"
            if errors:
                message += f", {len(errors)} errors"
                # Show errors in a message box
                error_msg = "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    error_msg += f"\n... and {len(errors) - 10} more errors"
                QMessageBox.warning(self, "Operation Errors", error_msg)
            
            self.statusBar().showMessage(message, 5000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to {self.clipboard_operation} files: {str(e)}")
            self.statusBar().showMessage(f"Operation failed: {str(e)}", 5000)
