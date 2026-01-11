"""
File system backend for directory operations.
Provides clean abstraction for file system operations.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Generator, Tuple
from datetime import datetime
from enum import Enum


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
    
    def list_directory_streaming(self, path: Optional[Path] = None) -> Generator[FileEntry, None, None]:
        """
        List contents of a directory as a stream (generator).
        
        This yields entries as they are discovered, allowing for progressive
        display in the UI without blocking on large directories.
        
        Args:
            path: Directory path to list. Uses current_path if None.
            
        Yields:
            FileEntry objects as they are discovered.
            
        Raises:
            PermissionError: If the directory cannot be accessed.
        """
        target_path = path or self.current_path
        
        try:
            for item in target_path.iterdir():
                try:
                    yield FileEntry(item)
                except (OSError, PermissionError):
                    # Skip files we can't access
                    pass
                    
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


class ConflictResolution(Enum):
    """Enumeration of conflict resolution options."""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    CANCEL = "cancel"


class FileConflict:
    """Represents a file that already exists at the destination."""
    
    def __init__(self, source: Path, destination: Path):
        self.source = source
        self.destination = destination
        
        # Cache stat results to avoid redundant filesystem operations
        source_exists = source.exists()
        dest_exists = destination.exists()
        
        source_stat = source.stat() if source_exists else None
        dest_stat = destination.stat() if dest_exists else None
        
        self.source_size = source_stat.st_size if source_stat else 0
        self.dest_size = dest_stat.st_size if dest_stat else 0
        self.source_modified = datetime.fromtimestamp(source_stat.st_mtime) if source_stat else None
        self.dest_modified = datetime.fromtimestamp(dest_stat.st_mtime) if dest_stat else None


class FileOperations:
    """Handles file copy and move operations with conflict detection."""
    
    @staticmethod
    def detect_conflicts(sources: List[Path], destination_dir: Path) -> List[FileConflict]:
        """
        Detect files that would conflict with existing files at destination.
        
        Args:
            sources: List of source file/directory paths to copy/move
            destination_dir: Destination directory
            
        Returns:
            List of FileConflict objects for files that already exist at destination
        """
        conflicts = []
        
        for source in sources:
            if not source.exists():
                continue
                
            dest_path = destination_dir / source.name
            if dest_path.exists():
                conflicts.append(FileConflict(source, dest_path))
        
        return conflicts
    
    @staticmethod
    def copy_files(
        sources: List[Path],
        destination_dir: Path,
        conflict_resolutions: Optional[Dict[Path, ConflictResolution]] = None,
        default_resolution: ConflictResolution = ConflictResolution.SKIP
    ) -> Tuple[int, int, List[str]]:
        """
        Copy files to destination directory.
        
        Args:
            sources: List of source paths to copy
            destination_dir: Destination directory
            conflict_resolutions: Dict mapping source paths to their resolution
            default_resolution: Default resolution for unspecified conflicts
            
        Returns:
            Tuple of (successful_count, skipped_count, error_messages)
        """
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True, exist_ok=True)
        
        conflict_resolutions = conflict_resolutions or {}
        successful = 0
        skipped = 0
        errors = []
        
        for source in sources:
            if not source.exists():
                errors.append(f"Source not found: {source}")
                continue
            
            dest_path = destination_dir / source.name
            resolution = conflict_resolutions.get(source, default_resolution)
            
            # Handle conflicts
            if dest_path.exists():
                if resolution == ConflictResolution.SKIP:
                    skipped += 1
                    continue
                elif resolution == ConflictResolution.RENAME:
                    dest_path = FileOperations._get_unique_name(dest_path)
                elif resolution == ConflictResolution.CANCEL:
                    errors.append(f"Operation cancelled for: {source.name}")
                    break
                elif resolution == ConflictResolution.OVERWRITE:
                    # Remove destination before copying for directories
                    if dest_path.is_dir():
                        try:
                            shutil.rmtree(dest_path)
                        except Exception as e:
                            errors.append(f"Failed to remove {dest_path.name}: {str(e)}")
                            continue
                    # For files, shutil.copy2 will overwrite automatically
            
            try:
                if source.is_dir():
                    shutil.copytree(source, dest_path)
                else:
                    shutil.copy2(source, dest_path)
                successful += 1
            except Exception as e:
                errors.append(f"Failed to copy {source.name}: {str(e)}")
        
        return successful, skipped, errors
    
    @staticmethod
    def move_files(
        sources: List[Path],
        destination_dir: Path,
        conflict_resolutions: Optional[Dict[Path, ConflictResolution]] = None,
        default_resolution: ConflictResolution = ConflictResolution.SKIP
    ) -> Tuple[int, int, List[str]]:
        """
        Move files to destination directory.
        
        Args:
            sources: List of source paths to move
            destination_dir: Destination directory
            conflict_resolutions: Dict mapping source paths to their resolution
            default_resolution: Default resolution for unspecified conflicts
            
        Returns:
            Tuple of (successful_count, skipped_count, error_messages)
        """
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True, exist_ok=True)
        
        conflict_resolutions = conflict_resolutions or {}
        successful = 0
        skipped = 0
        errors = []
        
        for source in sources:
            if not source.exists():
                errors.append(f"Source not found: {source}")
                continue
            
            dest_path = destination_dir / source.name
            resolution = conflict_resolutions.get(source, default_resolution)
            
            # Handle conflicts
            if dest_path.exists():
                if resolution == ConflictResolution.SKIP:
                    skipped += 1
                    continue
                elif resolution == ConflictResolution.RENAME:
                    dest_path = FileOperations._get_unique_name(dest_path)
                elif resolution == ConflictResolution.CANCEL:
                    errors.append(f"Operation cancelled for: {source.name}")
                    break
                elif resolution == ConflictResolution.OVERWRITE:
                    # Remove destination before moving
                    try:
                        if dest_path.is_dir():
                            shutil.rmtree(dest_path)
                        else:
                            dest_path.unlink()
                    except Exception as e:
                        errors.append(f"Failed to remove {dest_path.name}: {str(e)}")
                        continue
            
            try:
                shutil.move(str(source), str(dest_path))
                successful += 1
            except Exception as e:
                errors.append(f"Failed to move {source.name}: {str(e)}")
        
        return successful, skipped, errors
    
    @staticmethod
    def _get_unique_name(path: Path) -> Path:
        """
        Generate a unique filename by appending a number.
        
        Args:
            path: Original path
            
        Returns:
            A path that doesn't exist
        """
        if not path.exists():
            return path
        
        parent = path.parent
        stem = path.stem
        suffix = path.suffix
        counter = 1
        
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
