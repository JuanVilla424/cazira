"""Tests for cazira's main CLI module."""

import logging
import sys
from unittest import mock

import pytest

import main


def _fake_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    """Build a stand-in ``requests.Response``."""
    resp = mock.Mock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    return resp


# --- parse_arguments ---------------------------------------------------------


def test_parse_arguments_defaults(monkeypatch):
    """Without flags, defaults are returned and no repos are set."""
    monkeypatch.setattr(sys, "argv", ["main"])
    args = main.parse_arguments()
    assert args.output_dir == "output"
    assert args.log_level == "INFO"
    assert args.repos is None
    assert args.repos_file is None


def test_parse_arguments_with_repos(monkeypatch):
    """The repos and log-level flags are parsed."""
    monkeypatch.setattr(sys, "argv", ["main", "--repos", "a/b,c/d", "--log-level", "DEBUG"])
    args = main.parse_arguments()
    assert args.repos == "a/b,c/d"
    assert args.log_level == "DEBUG"


# --- load_repositories -------------------------------------------------------


def test_load_repositories_from_inline():
    """Inline list is split and stripped of blanks."""
    assert main.load_repositories("a/b, c/d ,", None) == ["a/b", "c/d"]


def test_load_repositories_from_file(tmp_path):
    """A file is read, ignoring blank and '#' lines."""
    repos_file = tmp_path / "repos.txt"
    repos_file.write_text("# comment\na/b\n\n c/d \n", encoding="utf-8")
    assert main.load_repositories(None, str(repos_file)) == ["a/b", "c/d"]


def test_load_repositories_empty():
    """No source means an empty list."""
    assert main.load_repositories(None, None) == []


# --- configure_logger --------------------------------------------------------


def test_configure_logger_invalid_level(tmp_path, monkeypatch):
    """An unknown level raises ValueError."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        main.configure_logger("LOUD")


def test_configure_logger_valid(tmp_path, monkeypatch):
    """A valid level sets the logger level."""
    monkeypatch.chdir(tmp_path)
    main.configure_logger("DEBUG")
    assert main.logger.level == logging.DEBUG


# --- _request_get ------------------------------------------------------------


def test_request_get_success():
    """A successful GET passes the configured timeout."""
    with mock.patch("main.requests.get", return_value=_fake_response(200)) as getter:
        resp = main._request_get("http://x", {})
    assert resp.status_code == 200
    getter.assert_called_once()
    assert getter.call_args.kwargs["timeout"] == main.REQUEST_TIMEOUT


def test_request_get_rate_limit_retries():
    """A 403 rate-limit response is retried after a backoff."""
    limited = _fake_response(403, text="API rate limit exceeded")
    ok = _fake_response(200)
    with (
        mock.patch("main.requests.get", side_effect=[limited, ok]) as getter,
        mock.patch("main.time.sleep") as sleeper,
    ):
        resp = main._request_get("http://x", {})
    assert resp.status_code == 200
    assert getter.call_count == 2
    sleeper.assert_called()


def test_request_get_network_error_returns_none():
    """A network error returns None instead of raising."""
    with mock.patch("main.requests.get", side_effect=main.requests.exceptions.Timeout("boom")):
        assert main._request_get("http://x", {}) is None


# --- get_repo_info / download_readme -----------------------------------------


def test_get_repo_info_ok():
    """A 200 returns the parsed JSON."""
    data = {"license": {"name": "MIT License"}, "default_branch": "main"}
    with mock.patch("main._request_get", return_value=_fake_response(200, json_data=data)):
        assert main.get_repo_info("o", "r") == data


def test_get_repo_info_fail():
    """A non-200 returns None."""
    with mock.patch("main._request_get", return_value=_fake_response(404)):
        assert main.get_repo_info("o", "r") is None


def test_download_readme_ok():
    """A 200 returns the README text."""
    with mock.patch("main._request_get", return_value=_fake_response(200, text="# hi")):
        assert main.download_readme("o", "r", "main") == "# hi"


def test_download_readme_fail():
    """A non-200 returns None."""
    with mock.patch("main._request_get", return_value=_fake_response(404)):
        assert main.download_readme("o", "r", "main") is None


# --- save_readme -------------------------------------------------------------


def test_save_readme(tmp_path):
    """The content is written and the filename is sanitized."""
    main.save_readme("# content", "owner/repo", str(tmp_path))
    out = tmp_path / "owner_repo.md"
    assert out.read_text(encoding="utf-8") == "# content"


# --- process_repositories ----------------------------------------------------


def test_process_repositories_allowed_license_saves(tmp_path):
    """A permissive license leads to a saved README."""
    info = {"license": {"name": "MIT License"}, "default_branch": "main"}
    with (
        mock.patch("main.get_repo_info", return_value=info),
        mock.patch("main.download_readme", return_value="# readme"),
    ):
        main.process_repositories(["o/r"], str(tmp_path))
    assert (tmp_path / "r.md").exists()


def test_process_repositories_disallowed_license_skips(tmp_path):
    """A disallowed license skips the download."""
    info = {"license": {"name": "GPL-3.0"}, "default_branch": "main"}
    with (
        mock.patch("main.get_repo_info", return_value=info),
        mock.patch("main.download_readme") as downloader,
    ):
        main.process_repositories(["o/r"], str(tmp_path))
    downloader.assert_not_called()


def test_process_repositories_no_license_skips(tmp_path):
    """A repo without a license is skipped."""
    with (
        mock.patch("main.get_repo_info", return_value={"default_branch": "main"}),
        mock.patch("main.download_readme") as downloader,
    ):
        main.process_repositories(["o/r"], str(tmp_path))
    downloader.assert_not_called()


def test_process_repositories_invalid_format_skips(tmp_path):
    """Invalid and empty entries never reach the API."""
    with mock.patch("main.get_repo_info") as getter:
        main.process_repositories(["not-a-repo", ""], str(tmp_path))
    getter.assert_not_called()


# --- main --------------------------------------------------------------------


def test_main_no_repos(tmp_path, monkeypatch):
    """Without repos, main exits early without processing."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main"])
    with mock.patch("main.process_repositories") as processor:
        main.main()
    processor.assert_not_called()


def test_main_with_repos(tmp_path, monkeypatch):
    """With repos, main delegates to process_repositories."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main", "--repos", "o/r"])
    with mock.patch("main.process_repositories") as processor:
        main.main()
    processor.assert_called_once()


# --- extra branch coverage ---------------------------------------------------


def test_request_get_exhausts_retries():
    """When every attempt is rate-limited, the last response is returned."""
    limited = _fake_response(403, text="API rate limit exceeded")
    with mock.patch("main.requests.get", return_value=limited), mock.patch("main.time.sleep"):
        resp = main._request_get("http://x", {})
    assert resp.status_code == 403


def test_get_repo_info_sends_token_header():
    """A token is forwarded as an Authorization header."""
    with mock.patch(
        "main._request_get", return_value=_fake_response(200, json_data={"a": 1})
    ) as getter:
        main.get_repo_info("o", "r", token="TKN")
    assert getter.call_args.args[1]["Authorization"] == "token TKN"


def test_download_readme_sends_token_header():
    """A token is forwarded as an Authorization header."""
    with mock.patch("main._request_get", return_value=_fake_response(200, text="# x")) as getter:
        main.download_readme("o", "r", "main", token="TKN")
    assert getter.call_args.args[1]["Authorization"] == "token TKN"


def test_save_readme_creates_directory(tmp_path):
    """A missing target directory is created before writing."""
    target = tmp_path / "new" / "nested"
    main.save_readme("# x", "r", str(target))
    assert (target / "r.md").read_text(encoding="utf-8") == "# x"


def test_save_readme_logs_on_oserror(tmp_path):
    """An OSError while writing is caught and logged, not raised."""
    # Make the target file path a directory so open() fails with an OSError.
    (tmp_path / "r.md").mkdir()
    main.save_readme("# x", "r", str(tmp_path))
    assert (tmp_path / "r.md").is_dir()


def test_process_repositories_failed_info_skips(tmp_path):
    """A failed info fetch skips the repo before checking the license."""
    with (
        mock.patch("main.get_repo_info", return_value=None),
        mock.patch("main.download_readme") as downloader,
    ):
        main.process_repositories(["o/r"], str(tmp_path))
    downloader.assert_not_called()


def test_process_repositories_no_readme_skips(tmp_path):
    """An allowed repo without a downloadable README is skipped without saving."""
    info = {"license": {"name": "MIT License"}, "default_branch": "main"}
    with (
        mock.patch("main.get_repo_info", return_value=info),
        mock.patch("main.download_readme", return_value=None),
    ):
        main.process_repositories(["o/r"], str(tmp_path))
    assert not (tmp_path / "r.md").exists()
