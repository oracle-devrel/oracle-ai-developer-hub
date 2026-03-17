"""File system watcher and pollers for sync sources."""

import fnmatch
import subprocess
import time
from typing import Callable, List, Optional

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """Watchdog event handler with glob filtering and debounce."""

    def __init__(self, callback: Callable, glob_patterns: Optional[List[str]] = None,
                 debounce_seconds: float = 2):
        super().__init__()
        self._callback = callback
        self._glob_patterns = glob_patterns
        self._debounce_seconds = debounce_seconds
        self._last_event_times: dict[str, float] = {}

    def _matches_pattern(self, path: str) -> bool:
        """Check if file matches any glob pattern."""
        if not self._glob_patterns:
            return True
        return any(fnmatch.fnmatch(path, pat) for pat in self._glob_patterns)

    def _debounce(self, path: str) -> bool:
        """Return True if the event should be skipped (within debounce window)."""
        now = time.monotonic()
        last = self._last_event_times.get(path)
        if last is not None and (now - last) < self._debounce_seconds:
            return True
        self._last_event_times[path] = now
        return False

    def _handle_event(self, event_type: str, event) -> None:
        """Common handler for all event types."""
        if event.is_directory:
            return
        path = event.src_path
        if not self._matches_pattern(path):
            return
        if self._debounce(path):
            return
        logger.debug("File %s: %s", event_type, path)
        self._callback(event_type, path)

    def on_created(self, event) -> None:
        self._handle_event("created", event)

    def on_modified(self, event) -> None:
        self._handle_event("modified", event)

    def on_deleted(self, event) -> None:
        self._handle_event("deleted", event)


class DirectoryWatcher:
    """Watch a directory for file changes using watchdog."""

    def __init__(self, path: str, callback: Callable,
                 glob_patterns: Optional[List[str]] = None,
                 debounce_seconds: float = 2):
        self._path = path
        self._handler = FileChangeHandler(callback, glob_patterns, debounce_seconds)
        self._observer = Observer()
        self._observer.schedule(self._handler, path, recursive=True)

    def start(self) -> None:
        """Start watching the directory."""
        logger.info("Starting directory watcher on %s", self._path)
        self._observer.start()

    def stop(self) -> None:
        """Stop watching the directory."""
        logger.info("Stopping directory watcher on %s", self._path)
        self._observer.stop()
        self._observer.join()

    def is_alive(self) -> bool:
        """Check if the observer thread is running."""
        return self._observer.is_alive()


class GitPoller:
    """Poll a git repository for new commits and changed files."""

    def __init__(self, repo_path: str, callback: Callable,
                 glob_patterns: Optional[List[str]] = None):
        self._repo_path = repo_path
        self._callback = callback
        self._glob_patterns = glob_patterns
        self._last_commit: Optional[str] = None

    def _get_latest_commit(self) -> Optional[str]:
        """Get the latest commit hash."""
        result = subprocess.run(
            ["git", "-C", self._repo_path, "log", "-1", "--format=%H"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logger.warning("Failed to get latest commit from %s: %s",
                           self._repo_path, result.stderr)
            return None
        return result.stdout.strip()

    def _get_changed_files(self, since_commit: str) -> List[str]:
        """Get list of files changed since a commit."""
        result = subprocess.run(
            ["git", "-C", self._repo_path, "diff", "--name-only", since_commit, "HEAD"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logger.warning("Failed to get changed files from %s: %s",
                           self._repo_path, result.stderr)
            return []
        return [f for f in result.stdout.strip().split("\n") if f]

    def _matches_pattern(self, path: str) -> bool:
        """Check if file matches any glob pattern."""
        if not self._glob_patterns:
            return True
        return any(fnmatch.fnmatch(path, pat) for pat in self._glob_patterns)

    def poll(self) -> None:
        """Poll for changes since last known commit."""
        current_commit = self._get_latest_commit()
        if current_commit is None:
            return

        if self._last_commit is None:
            # First poll, just record the baseline
            self._last_commit = current_commit
            logger.debug("Git poller baseline set to %s", current_commit)
            return

        if current_commit == self._last_commit:
            return

        logger.info("Git poller detected new commit %s (was %s)",
                     current_commit, self._last_commit)
        changed_files = self._get_changed_files(self._last_commit)
        for file_path in changed_files:
            if self._matches_pattern(file_path):
                self._callback("modified", file_path)

        self._last_commit = current_commit


class URLPoller:
    """Poll a URL for changes using HTTP HEAD requests."""

    def __init__(self, url: str, callback: Callable):
        self._url = url
        self._callback = callback
        self._last_modified: Optional[str] = None
        self._etag: Optional[str] = None

    def poll(self) -> None:
        """Check if the URL content has changed."""
        headers = {}
        if self._last_modified:
            headers["If-Modified-Since"] = self._last_modified
        if self._etag:
            headers["If-None-Match"] = self._etag

        try:
            response = requests.head(self._url, headers=headers, timeout=30)
        except requests.RequestException as e:
            logger.warning("Failed to poll URL %s: %s", self._url, e)
            return

        if response.status_code == 304:
            # Not modified
            return

        new_last_modified = response.headers.get("Last-Modified")
        new_etag = response.headers.get("ETag")

        # Check if anything actually changed
        if (new_last_modified == self._last_modified and
                new_etag == self._etag and
                self._last_modified is not None):
            return

        if response.status_code == 200:
            logger.info("URL change detected: %s", self._url)
            self._callback("modified", self._url)

        self._last_modified = new_last_modified
        self._etag = new_etag
