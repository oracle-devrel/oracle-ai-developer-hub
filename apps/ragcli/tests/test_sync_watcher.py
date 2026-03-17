"""Test file watcher and sync scheduler."""
import time
from unittest.mock import MagicMock, patch, call
from ragcli.sync.watcher import FileChangeHandler, DirectoryWatcher, GitPoller, URLPoller
from ragcli.sync.scheduler import SyncScheduler


# --- FileChangeHandler tests ---

def test_file_change_handler_matches_pattern():
    handler = FileChangeHandler(callback=MagicMock(), glob_patterns=["*.md", "*.txt"])
    assert handler._matches_pattern("/some/path/readme.md") is True
    assert handler._matches_pattern("/some/path/notes.txt") is True


def test_file_change_handler_rejects_pattern():
    handler = FileChangeHandler(callback=MagicMock(), glob_patterns=["*.md"])
    assert handler._matches_pattern("/some/path/photo.jpg") is False
    assert handler._matches_pattern("/some/path/data.csv") is False


def test_file_change_handler_no_patterns_matches_all():
    handler = FileChangeHandler(callback=MagicMock(), glob_patterns=None)
    assert handler._matches_pattern("/any/file.xyz") is True


def test_debounce_skips_rapid_events():
    callback = MagicMock()
    handler = FileChangeHandler(callback=callback, glob_patterns=None, debounce_seconds=2)

    # Simulate first event
    event = MagicMock()
    event.src_path = "/some/path/file.md"
    event.is_directory = False
    handler.on_modified(event)
    assert callback.call_count == 1

    # Simulate second event within debounce window (should be skipped)
    handler.on_modified(event)
    assert callback.call_count == 1


def test_debounce_allows_after_window():
    callback = MagicMock()
    handler = FileChangeHandler(callback=callback, glob_patterns=None, debounce_seconds=0.1)

    event = MagicMock()
    event.src_path = "/some/path/file.md"
    event.is_directory = False
    handler.on_modified(event)
    assert callback.call_count == 1

    # Wait for debounce window to pass
    time.sleep(0.15)
    handler.on_modified(event)
    assert callback.call_count == 2


def test_on_created_calls_callback():
    callback = MagicMock()
    handler = FileChangeHandler(callback=callback, glob_patterns=None, debounce_seconds=0)

    event = MagicMock()
    event.src_path = "/some/path/new_file.md"
    event.is_directory = False
    handler.on_created(event)
    callback.assert_called_once_with("created", "/some/path/new_file.md")


def test_on_deleted_calls_callback():
    callback = MagicMock()
    handler = FileChangeHandler(callback=callback, glob_patterns=None, debounce_seconds=0)

    event = MagicMock()
    event.src_path = "/some/path/old_file.md"
    event.is_directory = False
    handler.on_deleted(event)
    callback.assert_called_once_with("deleted", "/some/path/old_file.md")


def test_directory_events_ignored():
    callback = MagicMock()
    handler = FileChangeHandler(callback=callback, glob_patterns=None, debounce_seconds=0)

    event = MagicMock()
    event.src_path = "/some/path/subdir"
    event.is_directory = True
    handler.on_created(event)
    callback.assert_not_called()


# --- GitPoller tests ---

@patch("ragcli.sync.watcher.subprocess.run")
def test_git_poller_detects_change(mock_run):
    callback = MagicMock()
    poller = GitPoller("/fake/repo", callback=callback, glob_patterns=["*.md"])

    # First poll: set baseline commit
    mock_run.return_value = MagicMock(
        stdout="abc123\n", returncode=0
    )
    poller.poll()
    callback.assert_not_called()  # First poll just sets baseline

    # Second poll: new commit with changed files
    mock_run.side_effect = [
        MagicMock(stdout="def456\n", returncode=0),  # git log
        MagicMock(stdout="docs/readme.md\nimg/photo.png\n", returncode=0),  # git diff
    ]
    poller.poll()
    # Only readme.md matches *.md pattern
    callback.assert_called_once_with("modified", "docs/readme.md")


@patch("ragcli.sync.watcher.subprocess.run")
def test_git_poller_no_change(mock_run):
    callback = MagicMock()
    poller = GitPoller("/fake/repo", callback=callback)

    mock_run.return_value = MagicMock(stdout="abc123\n", returncode=0)
    poller.poll()  # Baseline
    poller.poll()  # Same commit
    callback.assert_not_called()


# --- URLPoller tests ---

@patch("ragcli.sync.watcher.requests.head")
def test_url_poller_detects_change(mock_head):
    callback = MagicMock()
    poller = URLPoller("https://example.com/doc.pdf", callback=callback)

    mock_head.return_value = MagicMock(
        status_code=200,
        headers={"Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
    )
    poller.poll()
    callback.assert_called_once_with("modified", "https://example.com/doc.pdf")


@patch("ragcli.sync.watcher.requests.head")
def test_url_poller_no_change(mock_head):
    callback = MagicMock()
    poller = URLPoller("https://example.com/doc.pdf", callback=callback)

    mock_head.return_value = MagicMock(
        status_code=200,
        headers={
            "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            "ETag": '"abc123"'
        }
    )
    poller.poll()  # First poll triggers callback
    callback.reset_mock()

    # Same headers, should not trigger
    mock_head.return_value = MagicMock(
        status_code=200,
        headers={
            "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            "ETag": '"abc123"'
        }
    )
    poller.poll()
    callback.assert_not_called()


# --- SyncScheduler tests ---

def test_add_source():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = SyncScheduler(mock_conn)
    source_id = scheduler.add_source("directory", "/data/docs", glob_pattern="*.pdf")

    assert source_id is not None
    assert len(source_id) == 36  # UUID format
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    # Verify the SQL contains INSERT INTO SYNC_SOURCES
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO SYNC_SOURCES" in sql_arg


def test_list_sources():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [
        ("source_id",), ("source_type",), ("source_path",),
        ("glob_pattern",), ("poll_interval",), ("enabled",),
        ("last_sync",), ("metadata_json",), ("created_at",),
    ]
    mock_cursor.fetchall.return_value = [
        ("id-1", "directory", "/data/docs", "*.pdf", 300, 1, None, None, None),
        ("id-2", "git", "/repo", "*.md", 600, 1, None, None, None),
    ]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = SyncScheduler(mock_conn)
    sources = scheduler.list_sources()

    assert len(sources) == 2
    assert sources[0]["source_id"] == "id-1"
    assert sources[0]["source_type"] == "directory"
    assert sources[1]["source_path"] == "/repo"


def test_log_event():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = SyncScheduler(mock_conn)
    scheduler.log_event("src-1", "/data/docs/file.pdf", "created",
                        document_id="doc-1", chunks_added=5)

    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO SYNC_EVENTS" in sql_arg

    params = mock_cursor.execute.call_args[0][1]
    assert params["source_id"] == "src-1"
    assert params["file_path"] == "/data/docs/file.pdf"
    assert params["event_type"] == "created"
    assert params["chunks_added"] == 5


def test_remove_source():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = SyncScheduler(mock_conn)
    scheduler.remove_source("src-1")

    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "DELETE FROM SYNC_SOURCES" in sql_arg
    mock_conn.commit.assert_called_once()


def test_get_source_found():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [
        ("source_id",), ("source_type",), ("source_path",),
        ("glob_pattern",), ("poll_interval",), ("enabled",),
        ("last_sync",), ("metadata_json",), ("created_at",),
    ]
    mock_cursor.fetchone.return_value = (
        "id-1", "directory", "/data/docs", "*.pdf", 300, 1, None, None, None
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = SyncScheduler(mock_conn)
    source = scheduler.get_source("id-1")

    assert source is not None
    assert source["source_id"] == "id-1"
    assert source["source_type"] == "directory"


def test_get_source_not_found():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = SyncScheduler(mock_conn)
    source = scheduler.get_source("nonexistent")

    assert source is None
