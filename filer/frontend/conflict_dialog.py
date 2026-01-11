"""
Conflict resolution dialog for file operations.
"""
from pathlib import Path
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QRadioButton, QButtonGroup, QCheckBox
)
from PyQt6.QtCore import Qt

from ..backend.filesystem import FileConflict, ConflictResolution


class ConflictDialog(QDialog):
    """Dialog for resolving file conflicts before operations."""
    
    def __init__(self, conflicts: List[FileConflict], operation: str = "copy", parent=None):
        super().__init__(parent)
        self.conflicts = conflicts
        self.operation = operation
        self.resolutions: Dict[str, ConflictResolution] = {}
        self.default_resolution: ConflictResolution = ConflictResolution.SKIP
        self.current_index = 0
        self.apply_to_all = False
        self.init_ui()
        self.show_current_conflict()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"File Conflicts - {self.operation.title()}")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Header with conflict count
        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(self.header_label)
        
        # Conflict details
        details_group = QGroupBox("Conflict Details")
        details_layout = QVBoxLayout()
        
        self.source_label = QLabel()
        self.dest_label = QLabel()
        self.source_info_label = QLabel()
        self.dest_info_label = QLabel()
        
        details_layout.addWidget(QLabel("<b>Source:</b>"))
        details_layout.addWidget(self.source_label)
        details_layout.addWidget(self.source_info_label)
        details_layout.addWidget(QLabel(""))
        details_layout.addWidget(QLabel("<b>Destination (existing):</b>"))
        details_layout.addWidget(self.dest_label)
        details_layout.addWidget(self.dest_info_label)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Resolution options
        options_group = QGroupBox("Choose Action")
        options_layout = QVBoxLayout()
        
        self.option_group = QButtonGroup()
        
        self.skip_radio = QRadioButton("Skip this file")
        self.skip_radio.setChecked(True)
        self.option_group.addButton(self.skip_radio, 0)
        options_layout.addWidget(self.skip_radio)
        
        self.overwrite_radio = QRadioButton("Overwrite (replace existing file)")
        self.option_group.addButton(self.overwrite_radio, 1)
        options_layout.addWidget(self.overwrite_radio)
        
        self.rename_radio = QRadioButton("Keep both (rename new file)")
        self.option_group.addButton(self.rename_radio, 2)
        options_layout.addWidget(self.rename_radio)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Apply to all checkbox
        self.apply_to_all_checkbox = QCheckBox("Apply this action to all remaining conflicts")
        layout.addWidget(self.apply_to_all_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.skip_all_button = QPushButton("Skip All")
        self.skip_all_button.clicked.connect(self.skip_all)
        button_layout.addWidget(self.skip_all_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        if len(self.conflicts) > 1:
            self.next_button = QPushButton("Next")
            self.next_button.clicked.connect(self.handle_next)
            button_layout.addWidget(self.next_button)
        
        self.ok_button = QPushButton("OK" if len(self.conflicts) == 1 else "Finish")
        self.ok_button.clicked.connect(self.handle_ok)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
    
    def show_current_conflict(self):
        """Display information about the current conflict."""
        if self.current_index >= len(self.conflicts):
            return
        
        conflict = self.conflicts[self.current_index]
        
        # Update header
        self.header_label.setText(
            f"File Conflict {self.current_index + 1} of {len(self.conflicts)}"
        )
        
        # Update source info
        self.source_label.setText(str(conflict.source))
        source_info = f"Size: {self._format_size(conflict.source_size)}"
        if conflict.source_modified:
            source_info += f", Modified: {conflict.source_modified.strftime('%Y-%m-%d %H:%M:%S')}"
        self.source_info_label.setText(source_info)
        self.source_info_label.setStyleSheet("color: gray; font-size: 10px;")
        
        # Update destination info
        self.dest_label.setText(str(conflict.destination))
        dest_info = f"Size: {self._format_size(conflict.dest_size)}"
        if conflict.dest_modified:
            dest_info += f", Modified: {conflict.dest_modified.strftime('%Y-%m-%d %H:%M:%S')}"
        self.dest_info_label.setText(dest_info)
        self.dest_info_label.setStyleSheet("color: gray; font-size: 10px;")
        
        # Reset radio button to default if not in apply-to-all mode
        if not self.apply_to_all:
            self.skip_radio.setChecked(True)
    
    def _format_size(self, size: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def get_current_resolution(self) -> ConflictResolution:
        """Get the selected resolution for current conflict."""
        if self.skip_radio.isChecked():
            return ConflictResolution.SKIP
        elif self.overwrite_radio.isChecked():
            return ConflictResolution.OVERWRITE
        elif self.rename_radio.isChecked():
            return ConflictResolution.RENAME
        return ConflictResolution.SKIP
    
    def handle_next(self):
        """Handle next button click."""
        # Save current resolution
        conflict = self.conflicts[self.current_index]
        resolution = self.get_current_resolution()
        self.resolutions[conflict.source.name] = resolution
        
        # Check if apply to all is selected
        if self.apply_to_all_checkbox.isChecked():
            self.apply_to_all = True
            self.default_resolution = resolution
            # Apply to all remaining conflicts
            for i in range(self.current_index + 1, len(self.conflicts)):
                self.resolutions[self.conflicts[i].source.name] = resolution
            self.accept()
            return
        
        # Move to next conflict
        self.current_index += 1
        if self.current_index >= len(self.conflicts):
            self.accept()
        else:
            self.show_current_conflict()
            # Update button text
            if hasattr(self, 'next_button') and self.current_index == len(self.conflicts) - 1:
                self.next_button.setText("Finish")
    
    def handle_ok(self):
        """Handle OK/Finish button click."""
        # Save current resolution
        conflict = self.conflicts[self.current_index]
        resolution = self.get_current_resolution()
        self.resolutions[conflict.source.name] = resolution
        
        # Check if apply to all is selected
        if self.apply_to_all_checkbox.isChecked():
            self.apply_to_all = True
            self.default_resolution = resolution
            # Apply to all remaining conflicts
            for i in range(self.current_index + 1, len(self.conflicts)):
                self.resolutions[self.conflicts[i].source.name] = resolution
        
        self.accept()
    
    def skip_all(self):
        """Skip all conflicts."""
        self.default_resolution = ConflictResolution.SKIP
        for conflict in self.conflicts:
            self.resolutions[conflict.source.name] = ConflictResolution.SKIP
        self.accept()
    
    def get_resolutions(self) -> tuple[Dict[str, ConflictResolution], ConflictResolution]:
        """Get the conflict resolutions."""
        return self.resolutions, self.default_resolution
