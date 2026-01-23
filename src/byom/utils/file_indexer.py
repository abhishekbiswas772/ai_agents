import os
import json
from pathlib import Path
from typing import List, Dict, Set
import threading
import time

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = object  # type: ignore

class FileChangeHandler(FileSystemEventHandler):
    """
    Watchdog event handler to trigger index updates on file changes.
    """
    def __init__(self, callback, ignore_patterns):
        self.callback = callback
        self.ignore_patterns = ignore_patterns
        self._timer = None
        self._debounce_interval = 2.0  # 2 second debounce

    def _trigger_update(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self._debounce_interval, self.callback)
        self._timer.start()

    def on_created(self, event):
        self._trigger_update()

    def on_deleted(self, event):
        self._trigger_update()

    def on_moved(self, event):
        self._trigger_update()

class FileIndexer:
    """
    Handles indexing of files in the workspace for quick access and suggestions.
    Maintains a file_index.json in .byom-ai directory.
    """
    
    INDEX_DIR_NAME = ".byom-ai"
    INDEX_FILE_NAME = "file_index.json"
    
    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path).resolve()
        self.index_dir = self.root_path / self.INDEX_DIR_NAME
        self.index_file = self.index_dir / self.INDEX_FILE_NAME
        self.file_list: List[str] = []
        
        # Files/Dirs to ignore
        self.ignore_patterns: Set[str] = {
            ".git", ".env", ".venv", "venv", "__pycache__", 
            "node_modules", ".idea", ".vscode", ".DS_Store",
            self.INDEX_DIR_NAME, "site-packages", "dist", "build", "coverage"
        }
        
        self.observer = None
        self.handler = None

    def start_watching(self):
        """Start watching for file changes."""
        if Observer and not self.observer:
            self.handler = FileChangeHandler(self.scan_workspace, self.ignore_patterns)
            self.observer = Observer()
            self.observer.schedule(self.handler, str(self.root_path), recursive=True)
            self.observer.start()

    def stop_watching(self):
        """Stop watching for file changes."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

    def ensure_byom_dir(self) -> None:
        """Ensure the .byom-ai directory exists."""
        if not self.index_dir.exists():
            try:
                self.index_dir.mkdir(parents=True, exist_ok=True)
                # On Windows, we might want to hide it, but starting with . is standard enough
            except Exception as e:
                # If we can't create it, we just won't cache, but shouldn't crash app
                pass

    def scan_workspace(self) -> List[str]:
        """
        Scans the workspace for files and returns a list of relative paths.
        Also updates the persistent index.
        """
        files_found = []
        
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Modify dirs in-place to skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns and not d.startswith('.')]
                
                for d in dirs:
                    abs_path = Path(root) / d
                    try:
                        rel_path = abs_path.relative_to(self.root_path)
                        # Add trailing slash for directories
                        files_found.append(str(rel_path).replace('\\', '/') + '/')
                    except ValueError:
                        continue

                for file in files:
                    if file in self.ignore_patterns or file.startswith('.'):
                        continue
                        
                    abs_path = Path(root) / file
                    try:
                        rel_path = abs_path.relative_to(self.root_path)
                        files_found.append(str(rel_path).replace('\\', '/'))
                    except ValueError:
                        continue
        except Exception:
            # Fallback to empty list on error
            pass
            
        self.file_list = sorted(files_found)
        self.update_index()
        return self.file_list

    def update_index(self) -> None:
        """Writes the current file list to the index JSON file."""
        self.ensure_byom_dir()
        if not self.index_dir.exists():
            return
            
        try:
            data = {
                "root": str(self.root_path),
                "files": self.file_list,
                # we could add more metadata later like timestamps
            }
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_files(self) -> List[str]:
        """Returns the list of indexed files."""
        if not self.file_list:
            # Try to load from disk if memory is empty
            if self.index_file.exists():
                try:
                    with open(self.index_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.file_list = data.get("files", [])
                except Exception:
                    # If load fails, rescan
                    return self.scan_workspace()
            else:
                return self.scan_workspace()
        
        return self.file_list

try:
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    
    class FileCompleter(Completer):
        """
        Completer that suggests files when the user types '@'.
        """
        def __init__(self, indexer: FileIndexer):
            self.indexer = indexer

        def get_completions(self, document: Document, complete_event):
            text = document.text_before_cursor
            
            # Simple heuristic: look at the last word
            words = text.split()
            if not words:
                return
                
            last_word = words[-1]
            
            # Check if we are typing a file reference starting with @
            if last_word.startswith('@'):
                search_term = last_word[1:].lower()
                files = self.indexer.get_files()
                
                matches = []
                
                for file_path in files:
                    # Fuzzy match: search_term characters must appear in order in file_path
                    qp_idx = 0
                    fp_idx = 0
                    match = True
                    search_term_lower = search_term.lower()
                    file_path_lower = file_path.lower()
                    
                    first_match_idx = -1
                    last_match_idx = -1
                    
                    while qp_idx < len(search_term_lower):
                        found_idx = file_path_lower.find(search_term_lower[qp_idx], fp_idx)
                        if found_idx == -1:
                            match = False
                            break
                        
                        if first_match_idx == -1:
                            first_match_idx = found_idx
                        last_match_idx = found_idx
                        
                        fp_idx = found_idx + 1
                        qp_idx += 1
                    
                    if match:
                        # Score: smaller span is better
                        score = last_match_idx - first_match_idx
                        matches.append((score, file_path))
                
                # Sort by score (ascending span)
                matches.sort(key=lambda x: x[0])
                
                for _, file_path in matches:
                    # The start_position is relative to the cursor.
                    # We want to replace the whole '@search_term' with the file path
                    # so we go back the length of last_word
                    is_dir = file_path.endswith('/')
                    yield Completion(
                        file_path, 
                        start_position=-len(last_word),
                        display=file_path,
                        display_meta="Dir" if is_dir else "File"
                    )

except ImportError:
    # Fallback if prompt_toolkit is not installed (though it should be)
    class FileCompleter:  # type: ignore
        def __init__(self, indexer): pass
        def get_completions(self, *args): yield from []
