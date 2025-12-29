"""
File system watcher for monitoring directory changes.
"""
import logging
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class FileSystemWatcher(QObject, FileSystemEventHandler):
    """
    Watches a directory for file system changes and emits Qt signals.
    
    Signals:
        file_added: Emitted when a file/directory is created
        file_removed: Emitted when a file/directory is deleted
        file_modified: Emitted when a file/directory is modified
        file_moved: Emitted when a file/directory is moved (from_path, to_path)
    """
    
    # Qt signals for file system events
    file_added = pyqtSignal(Path)
    file_removed = pyqtSignal(Path)
    file_modified = pyqtSignal(Path)
    file_moved = pyqtSignal(Path, Path)  # from_path, to_path
    
    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        FileSystemEventHandler.__init__(self)
        self.observer: Optional[Observer] = None
        self.watched_path: Optional[Path] = None
    
    def watch_directory(self, path: Path) -> bool:
        """
        Start watching a directory for changes.
        
        Args:
            path: Directory path to watch
            
        Returns:
            True if watching started successfully, False otherwise
        """
        # Stop watching previous directory if any
        self.stop_watching()
        
        if not path.exists() or not path.is_dir():
            logger.warning(f"Cannot watch non-existent or non-directory path: {path}")
            return False
        
        try:
            self.watched_path = path
            self.observer = Observer()
            self.observer.schedule(self, str(path), recursive=False)
            self.observer.start()
            logger.info(f"Started watching directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to start watching directory {path}: {e}", exc_info=True)
            self.observer = None
            self.watched_path = None
            return False
    
    def stop_watching(self):
        """Stop watching the current directory."""
        if self.observer is not None:
            try:
                self.observer.stop()
                self.observer.join(timeout=1.0)
                logger.info(f"Stopped watching directory: {self.watched_path}")
            except Exception as e:
                logger.error(f"Error stopping file watcher: {e}", exc_info=True)
            finally:
                self.observer = None
                self.watched_path = None
    
    def is_watching(self) -> bool:
        """Check if currently watching a directory."""
        return self.observer is not None and self.observer.is_alive()
    
    def get_watched_path(self) -> Optional[Path]:
        """Get the currently watched directory path."""
        return self.watched_path
    
    # FileSystemEventHandler methods
    def on_created(self, event: FileSystemEvent):
        """Handle file/directory creation events."""
        if not event.is_directory or event.src_path != str(self.watched_path):
            # Emit signal for files and subdirectories (not the watched dir itself)
            path = Path(event.src_path)
            logger.debug(f"File created: {path}")
            self.file_added.emit(path)
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file/directory deletion events."""
        path = Path(event.src_path)
        logger.debug(f"File deleted: {path}")
        self.file_removed.emit(path)
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file/directory modification events."""
        if not event.is_directory:
            # Only emit for file modifications (directories emit too many events)
            path = Path(event.src_path)
            logger.debug(f"File modified: {path}")
            self.file_modified.emit(path)
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file/directory move/rename events."""
        from_path = Path(event.src_path)
        to_path = Path(event.dest_path) if hasattr(event, 'dest_path') else None
        
        if to_path:
            logger.debug(f"File moved: {from_path} -> {to_path}")
            self.file_moved.emit(from_path, to_path)
        else:
            # Treat as deletion if destination is unknown
            logger.debug(f"File moved/deleted: {from_path}")
            self.file_removed.emit(from_path)
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_watching()
