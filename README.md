# Filer - Cross-Platform File Manager

A modern, cross-platform GUI file manager built with Python and Qt, inspired by XYplorer, FMan, and Sublime Text.

## Features

- **Dual Pane Layout**: Work with two directories simultaneously (configurable to single pane)
- **Clean UI**: Intuitive interface with toolbar buttons for common actions
- **Command Palette**: Quick access to commands with Ctrl+Shift+P (Sublime Text style)
- **Sortable Columns**: Click column headers to sort by name, size, type, or modified date
- **Keyboard Navigation**: Navigate efficiently with keyboard shortcuts
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

1. Clone the repository:
```bash
git clone https://github.com/keith-hall/filer.git
cd filer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

### Keyboard Shortcuts

- **Ctrl+Shift+P**: Open command palette
- **F5**: Refresh current pane
- **Ctrl+D**: Toggle between single and dual pane layout
- **Backspace**: Navigate to parent directory
- **Enter**: Open selected directory or file
- **Double-click**: Navigate into directory

### Navigation

- Use the path bar at the top of each pane to manually enter a directory path
- Click the ↑ button to go to the parent directory
- Double-click on folders in the list to navigate into them
- Click column headers to sort the list

## Architecture

The project follows a clean separation between frontend and backend:

- **Backend** (`filer/backend/`):
  - `filesystem.py`: File system operations and abstractions
  - `models.py`: Qt models for data representation

- **Frontend** (`filer/frontend/`):
  - `main_window.py`: Main application window
  - `file_pane.py`: Individual file browser pane widget
  - `command_palette.py`: Command palette for quick actions

This architecture ensures:
- Clear boundaries between UI and business logic
- Easy testing of backend components
- Flexibility to swap UI frameworks if needed
- Maintainable and extensible codebase

## License

See LICENSE file for details.
