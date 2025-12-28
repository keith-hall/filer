"""
File system backend for directory operations.
Provides clean abstraction for file system operations.
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


class FileEntry:
    """Represents a file or directory entry."""
    
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.is_dir = path.is_dir()
        self._stat_cache: Optional[os.stat_result] = None
    
    @property
    def stat(self) -> os.stat_result:
        """Lazy load stat information."""
        if self._stat_cache is None:
            try:
                self._stat_cache = self.path.stat()
            except (OSError, PermissionError):
                # Return a dummy stat for inaccessible files
                class DummyStat:
                    st_size = 0
                    st_mtime = 0
                    st_mode = 0
                self._stat_cache = DummyStat()
        return self._stat_cache
    
    @property
    def size(self) -> int:
        """Get file size in bytes."""
        if self.is_dir:
            return 0
        return self.stat.st_size
    
    @property
    def modified_time(self) -> datetime:
        """Get last modified time."""
        return datetime.fromtimestamp(self.stat.st_mtime)
    
    @property
    def type_str(self) -> str:
        """Get file type as string."""
        if self.is_dir:
            return "Directory"
        suffix = self.path.suffix
        return suffix.upper()[1:] if suffix else "File"
    
    def format_size(self) -> str:
        """Format size in human-readable format."""
        if self.is_dir:
            return "<DIR>"
        
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class FileSystemBackend:
    """Backend for file system operations."""
    
    def __init__(self, initial_path: Optional[Path] = None):
        """Initialize with an optional starting path."""
        self.current_path = initial_path or Path.home()
        if not self.current_path.exists():
            self.current_path = Path.home()
    
    def list_directory(self, path: Optional[Path] = None) -> List[FileEntry]:
        """
        List contents of a directory.
        
        Args:
            path: Directory path to list. Uses current_path if None.
            
        Returns:
            List of FileEntry objects sorted by name (directories first).
        """
        target_path = path or self.current_path
        
        try:
            entries = []
            for item in target_path.iterdir():
                try:
                    entries.append(FileEntry(item))
                except (OSError, PermissionError):
                    # Skip files we can't access
                    pass
            
            # Sort: directories first, then by name (case-insensitive)
            entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
            return entries
            
        except (OSError, PermissionError) as e:
            raise PermissionError(f"Cannot access directory: {target_path}") from e
    
    def change_directory(self, path: Path) -> bool:
        """
        Change current directory.
        
        Args:
            path: New directory path.
            
        Returns:
            True if successful, False otherwise.
        """
        if path.exists() and path.is_dir():
            self.current_path = path.resolve()
            return True
        return False
    
    def go_up(self) -> bool:
        """
        Navigate to parent directory.
        
        Returns:
            True if successful, False if already at root.
        """
        parent = self.current_path.parent
        if parent != self.current_path:
            self.current_path = parent
            return True
        return False
    
    def get_current_path(self) -> Path:
        """Get current directory path."""
        return self.current_path
