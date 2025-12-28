"""
Main application entry point for Filer file manager.
"""
import sys
from PyQt6.QtWidgets import QApplication
from filer.frontend.main_window import MainWindow


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Filer")
    app.setOrganizationName("Filer")
    
    # Set application style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
