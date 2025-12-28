"""
Command palette widget for quick actions.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, 
    QListWidgetItem, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from typing import List, Tuple, Callable


class Command:
    """Represents a command in the palette."""
    
    def __init__(self, name: str, description: str, callback: Callable):
        self.name = name
        self.description = description
        self.callback = callback
    
    def __str__(self):
        return f"{self.name}: {self.description}"


class CommandPalette(QDialog):
    """Command palette dialog for quick actions."""
    
    command_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commands: List[Command] = []
        self.init_ui()
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setMinimumWidth(500)
        self.setMaximumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a command...")
        self.search_input.textChanged.connect(self.filter_commands)
        layout.addWidget(self.search_input)
        
        # Command list
        self.command_list = QListWidget()
        self.command_list.itemActivated.connect(self.execute_command)
        layout.addWidget(self.command_list)
        
        # Help text
        help_label = QLabel("Press Enter to execute, Esc to cancel")
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(help_label)
    
    def add_command(self, name: str, description: str, callback: Callable):
        """Add a command to the palette."""
        self.commands.append(Command(name, description, callback))
    
    def show_palette(self):
        """Show the command palette and populate with commands."""
        self.search_input.clear()
        self.filter_commands("")
        self.search_input.setFocus()
        self.show()
        
        # Center on parent
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + 100
            self.move(x, y)
    
    def filter_commands(self, text: str):
        """Filter commands based on search text."""
        self.command_list.clear()
        
        search_lower = text.lower()
        for cmd in self.commands:
            if search_lower in cmd.name.lower() or search_lower in cmd.description.lower():
                item = QListWidgetItem(str(cmd))
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                self.command_list.addItem(item)
        
        # Select first item if available
        if self.command_list.count() > 0:
            self.command_list.setCurrentRow(0)
    
    def execute_command(self, item: QListWidgetItem):
        """Execute the selected command."""
        cmd = item.data(Qt.ItemDataRole.UserRole)
        if cmd:
            self.hide()
            cmd.callback()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.command_list.currentItem()
            if current_item:
                self.execute_command(current_item)
        elif event.key() == Qt.Key.Key_Down:
            self.command_list.setFocus()
            current = self.command_list.currentRow()
            if current < self.command_list.count() - 1:
                self.command_list.setCurrentRow(current + 1)
        elif event.key() == Qt.Key.Key_Up:
            self.command_list.setFocus()
            current = self.command_list.currentRow()
            if current > 0:
                self.command_list.setCurrentRow(current - 1)
        else:
            super().keyPressEvent(event)
