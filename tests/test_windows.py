from __future__ import annotations

import ctypes
import importlib
import os
import pathlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from platformdirs import windows
from platformdirs.windows import (
    _KF_FLAG_DONT_VERIFY,
    _KNOWN_FOLDER_GUIDS,
    Windows,
    get_win_folder,
    get_win_folder_from_env_vars,
    get_win_folder_from_registry,
    get_win_folder_if_csidl_name_not_env_var,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_WIN_FOLDERS: dict[str, str] = {
    "CSIDL_APPDATA": r"C:\Users\Test\AppData\Roaming",
    "CSIDL_LOCAL_APPDATA": r"C:\Users\Test\AppData\Local",
    "CSIDL_COMMON_APPDATA": r"C:\ProgramData",
    "CSIDL_PERSONAL": r"C:\Users\Test\Documents",
    "CSIDL_DOWNLOADS": r"C:\Users\Test\Downloads",
    "CSIDL_MYPICTURES": r"C:\Users\Test\Pictures",
    "CSIDL_MYVIDEO": r"C:\Users\Test\Videos",
    "CSIDL_MYMUSIC": r"C:\Users\Test\Music",
    "CSIDL_DESKTOPDIRECTORY": r"C:\Users\Test\Desktop",
    "CSIDL_PROGRAMS": r"C:\Users\Test\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
    "CSIDL_COMMON_PROGRAMS": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
}

_LOCAL = os.path.normpath(_WIN_FOLDERS["CSIDL_LOCAL_APPDATA"])
_COMMON = os.path.normpath(_WIN_FOLDERS["CSIDL_COMMON_APPDATA"])


@pytest.fixture(autouse=True)
def _mock_get_win_folder(mocker: MockerFixture) -> None:
    mocker.patch("platformdirs.windows.get_win_folder", side_effect=lambda csidl: _WIN_FOLDERS[csidl])


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no_args"),
        pytest.param({"appname": "foo"}, id="app_name"),
        pytest.param({"appname": "foo", "version": "v1.0"}, id="app_name_version"),
    ],
)
def test_windows(params: dict[str, Any], func: str) -> None:
    result = getattr(Windows(**params), func)

    suffix_parts = []
    if appname := params.get("appname"):
        suffix_parts.extend((appname, appname))
        if version := params.get("version"):
            suffix_parts.append(version)
    local = os.path.join(_LOCAL, *suffix_parts) if suffix_parts else _LOCAL  # ruff:ignore[os-path-join]
    common = os.path.join(_COMMON, *suffix_parts) if suffix_parts else _COMMON  # ruff:ignore[os-path-join]
    temp = os.path.join(_LOCAL, "Temp", *suffix_parts) if suffix_parts else os.path.join(_LOCAL, "Temp")  # ruff:ignore[os-path-join]
    cache_local = os.path.join(  # ruff:ignore[os-path-join]
        _LOCAL, *suffix_parts[:2], *(["Cache"] if suffix_parts else []), *suffix_parts[2:]
    )
    cache_common = os.path.join(  # ruff:ignore[os-path-join]
        _COMMON, *suffix_parts[:2], *(["Cache"] if suffix_parts else []), *suffix_parts[2:]
    )
    log = os.path.join(_LOCAL, *suffix_parts, "Logs")  # ruff:ignore[os-path-join]
    log_common = os.path.join(_COMMON, *suffix_parts, "Logs")  # ruff:ignore[os-path-join]

    expected_map = {
        "user_data_dir": local,
        "site_data_dir": common,
        "user_config_dir": local,
        "site_config_dir": common,
        "user_cache_dir": cache_local,
        "site_cache_dir": cache_common,
        "user_state_dir": local,
        "site_state_dir": common,
        "user_log_dir": log,
        "site_log_dir": log_common,
        "user_documents_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_PERSONAL"]),
        "user_downloads_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_DOWNLOADS"]),
        "user_pictures_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_MYPICTURES"]),
        "user_videos_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_MYVIDEO"]),
        "user_music_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_MYMUSIC"]),
        "user_desktop_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_DESKTOPDIRECTORY"]),
        "user_projects_dir": os.path.normpath(pathlib.Path("~/Projects").expanduser()),
        "user_publicshare_dir": os.path.normpath(
            os.environ.get("PUBLIC", str(Path("~").expanduser().parent / "Public"))
        ),
        "user_templates_dir": os.path.normpath(
            str(Path(_WIN_FOLDERS["CSIDL_APPDATA"]) / "Microsoft" / "Windows" / "Templates")
        ),
        "user_fonts_dir": os.path.normpath(str(Path(_LOCAL) / "Microsoft" / "Windows" / "Fonts")),
        "user_preference_dir": local,
        "user_bin_dir": os.path.join(_LOCAL, "Programs"),  # ruff:ignore[os-path-join]
        "site_bin_dir": os.path.join(_COMMON, "bin"),  # ruff:ignore[os-path-join]
        "user_applications_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_PROGRAMS"]),
        "site_applications_dir": os.path.normpath(_WIN_FOLDERS["CSIDL_COMMON_PROGRAMS"]),
        "user_runtime_dir": temp,
        "site_runtime_dir": temp,
    }
    assert result == expected_map[func]


def test_publicshare_dir_with_unavailable_home(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.setenv("PUBLIC", r"C:\Users\Shared")
    mocker.patch.object(Path, "expanduser", side_effect=RuntimeError("Could not determine home directory."))
    assert Windows().user_publicshare_dir == os.path.normpath(r"C:\Users\Shared")


def test_publicshare_dir_fallback(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.delenv("PUBLIC", raising=False)
    mocker.patch.object(Path, "expanduser", return_value=Path("C:/Users/Test"))
    assert Windows().user_publicshare_dir == os.path.normpath("C:/Users/Public")


def test_roaming_uses_appdata(mocker: MockerFixture) -> None:
    mock = mocker.patch("platformdirs.windows.get_win_folder", side_effect=lambda csidl: _WIN_FOLDERS[csidl])
    _result = Windows(appname="foo", roaming=True).user_data_dir
    mock.assert_called_with("CSIDL_APPDATA")


def test_non_roaming_uses_local_appdata(mocker: MockerFixture) -> None:
    mock = mocker.patch("platformdirs.windows.get_win_folder", side_effect=lambda csidl: _WIN_FOLDERS[csidl])
    _result = Windows(appname="foo", roaming=False).user_data_dir
    mock.assert_called_with("CSIDL_LOCAL_APPDATA")


def test_appauthor_false_skips_author() -> None:
    result = Windows(appname="foo", appauthor=False).user_data_dir
    assert result == os.path.join(_LOCAL, "foo")  # ruff:ignore[os-path-join]


def test_appauthor_explicit() -> None:
    result = Windows(appname="foo", appauthor="bar").user_data_dir
    assert result == os.path.join(_LOCAL, "bar", "foo")  # ruff:ignore[os-path-join]


@pytest.mark.parametrize(
    ("csidl_name", "env_var", "value"),
    [
        pytest.param("CSIDL_APPDATA", "APPDATA", r"C:\Users\Test\AppData\Roaming", id="appdata"),
        pytest.param("CSIDL_LOCAL_APPDATA", "LOCALAPPDATA", r"C:\Users\Test\AppData\Local", id="local_appdata"),
        pytest.param("CSIDL_COMMON_APPDATA", "ALLUSERSPROFILE", r"C:\ProgramData", id="common_appdata"),
    ],
)
def test_get_win_folder_from_env_vars_direct(
    monkeypatch: pytest.MonkeyPatch, csidl_name: str, env_var: str, value: str
) -> None:
    monkeypatch.setenv(env_var, value)
    assert get_win_folder_from_env_vars(csidl_name) == value


_USERPROFILE_CSIDL_PARAMS = [
    pytest.param("CSIDL_PERSONAL", "Documents", id="personal"),
    pytest.param("CSIDL_DOWNLOADS", "Downloads", id="downloads"),
    pytest.param("CSIDL_MYPICTURES", "Pictures", id="pictures"),
    pytest.param("CSIDL_MYVIDEO", "Videos", id="video"),
    pytest.param("CSIDL_MYMUSIC", "Music", id="music"),
    pytest.param("CSIDL_DESKTOPDIRECTORY", "Desktop", id="desktop"),
]


@pytest.mark.parametrize(("csidl_name", "subfolder"), _USERPROFILE_CSIDL_PARAMS)
def test_get_win_folder_from_env_vars_user_folders(
    monkeypatch: pytest.MonkeyPatch, csidl_name: str, subfolder: str
) -> None:
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Test")
    assert get_win_folder_from_env_vars(csidl_name).endswith(subfolder)


def test_get_win_folder_from_env_vars_programs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
    result = get_win_folder_from_env_vars("CSIDL_PROGRAMS")
    assert result.endswith("Programs")


def test_get_win_folder_from_env_vars_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown CSIDL name"):
        get_win_folder_from_env_vars("CSIDL_BOGUS")


def test_get_win_folder_from_env_vars_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    with pytest.raises(ValueError, match="Unset environment variable"):
        get_win_folder_from_env_vars("CSIDL_APPDATA")


def test_get_win_folder_if_csidl_name_not_env_var_returns_none() -> None:
    assert get_win_folder_if_csidl_name_not_env_var("CSIDL_APPDATA") is None


@pytest.mark.parametrize(("csidl_name", "subfolder"), _USERPROFILE_CSIDL_PARAMS)
def test_get_win_folder_if_csidl_name_not_env_var(
    monkeypatch: pytest.MonkeyPatch, csidl_name: str, subfolder: str
) -> None:
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Test")
    result = get_win_folder_if_csidl_name_not_env_var(csidl_name)
    assert result is not None
    assert result.endswith(subfolder)


def test_get_win_folder_if_csidl_name_not_env_var_programs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
    result = get_win_folder_if_csidl_name_not_env_var("CSIDL_PROGRAMS")
    assert result is not None
    assert result.endswith("Programs")


def _setup_ctypes_mocks(mocker: MockerFixture, *, win_dll: MagicMock | None = None) -> None:
    """Mock ctypes internals so get_win_folder_via_ctypes can be tested on non-Windows."""
    for attr in ("HRESULT", "WinDLL"):
        if not hasattr(ctypes, attr):
            setattr(ctypes, attr, MagicMock())
    if win_dll is not None:
        mocker.patch.object(ctypes, "WinDLL", win_dll)
    mocker.patch("sys.platform", "win32")
    mocker.patch("ctypes.POINTER", return_value=MagicMock())


def _cleanup_ctypes_mocks() -> None:
    for attr in ("HRESULT", "WinDLL"):
        if isinstance(getattr(ctypes, attr, None), MagicMock):
            delattr(ctypes, attr)


@pytest.mark.skipif(sys.platform != "win32", reason="real ctypes test only runs on Windows")
@pytest.mark.parametrize("csidl_name", list(_KNOWN_FOLDER_GUIDS.keys()), ids=list(_KNOWN_FOLDER_GUIDS.keys()))
def test_get_win_folder_via_ctypes_real(csidl_name: str) -> None:
    importlib.reload(windows)
    from platformdirs.windows import get_win_folder_via_ctypes as fresh_fn  # ruff:ignore[import-outside-top-level]

    result = fresh_fn(csidl_name)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.skipif(sys.platform == "win32", reason="mock-based flag inspection only runs on non-Windows")
def test_get_win_folder_via_ctypes_passes_dont_verify_flag(mocker: MockerFixture) -> None:
    _setup_ctypes_mocks(mocker)

    mock_ole32 = MagicMock()
    mock_shell32 = MagicMock()
    mock_kernel32 = MagicMock()
    mocker.patch.object(
        ctypes,
        "WinDLL",
        MagicMock(
            side_effect=lambda name: {"ole32": mock_ole32, "shell32": mock_shell32, "kernel32": mock_kernel32}[name],
        ),
    )

    mocker.patch("ctypes.byref", side_effect=lambda x: x)

    mock_path_ptr = MagicMock()
    mock_path_ptr.value = r"C:\Users\Test\AppData\Local"
    mocker.patch("ctypes.wintypes.LPWSTR", return_value=mock_path_ptr)

    try:
        importlib.reload(windows)
        from platformdirs.windows import get_win_folder_via_ctypes as fresh_fn  # ruff:ignore[import-outside-top-level]

        result = fresh_fn("CSIDL_LOCAL_APPDATA")
    finally:
        _cleanup_ctypes_mocks()

    assert result == r"C:\Users\Test\AppData\Local"
    mock_shell32.SHGetKnownFolderPath.assert_called_once()
    flags_arg = mock_shell32.SHGetKnownFolderPath.call_args[0][1]
    assert flags_arg == _KF_FLAG_DONT_VERIFY


def test_get_win_folder_via_ctypes_unknown_csidl(mocker: MockerFixture) -> None:
    if sys.platform != "win32":
        _setup_ctypes_mocks(mocker, win_dll=MagicMock(side_effect=lambda _name: MagicMock()))

    try:
        importlib.reload(windows)
        from platformdirs.windows import get_win_folder_via_ctypes as fresh_fn  # ruff:ignore[import-outside-top-level]

        with pytest.raises(ValueError, match="Unknown CSIDL name"):
            fresh_fn("CSIDL_BOGUS")
    finally:
        if sys.platform != "win32":
            _cleanup_ctypes_mocks()


@pytest.mark.skipif(sys.platform == "win32", reason="mock-based call counting only runs on non-Windows")
def test_get_win_folder_via_ctypes_builds_once(mocker: MockerFixture) -> None:
    """Repeated calls must reuse one resolver so ctypes pointer types are not leaked (issue #501)."""
    _setup_ctypes_mocks(mocker)

    win_dll = MagicMock(side_effect=lambda _name: MagicMock())
    mocker.patch.object(ctypes, "WinDLL", win_dll)
    mocker.patch("ctypes.byref", side_effect=lambda x: x)
    mocker.patch("ctypes.wintypes.LPWSTR", return_value=MagicMock(value=r"C:\Users\Test\AppData\Local"))

    try:
        importlib.reload(windows)
        from platformdirs.windows import get_win_folder_via_ctypes as fresh_fn  # ruff:ignore[import-outside-top-level]

        for _ in range(5):
            fresh_fn("CSIDL_LOCAL_APPDATA")
    finally:
        _cleanup_ctypes_mocks()

    assert win_dll.call_count == 3  # ole32, shell32, kernel32 loaded once total, not once per call


@pytest.mark.skipif(sys.platform == "win32", reason="cannot force NULL from real SHGetKnownFolderPath")
def test_get_win_folder_via_ctypes_null_result(mocker: MockerFixture) -> None:
    _setup_ctypes_mocks(mocker)

    mock_ole32 = MagicMock()
    mock_shell32 = MagicMock()
    mock_kernel32 = MagicMock()
    mocker.patch.object(
        ctypes,
        "WinDLL",
        MagicMock(
            side_effect=lambda name: {"ole32": mock_ole32, "shell32": mock_shell32, "kernel32": mock_kernel32}[name],
        ),
    )

    mocker.patch("ctypes.byref", side_effect=lambda x: x)

    mock_path_ptr = MagicMock()
    mock_path_ptr.value = None
    mocker.patch("ctypes.wintypes.LPWSTR", return_value=mock_path_ptr)

    try:
        importlib.reload(windows)
        from platformdirs.windows import get_win_folder_via_ctypes as fresh_fn  # ruff:ignore[import-outside-top-level]

        with pytest.raises(ValueError, match="SHGetKnownFolderPath returned NULL"):
            fresh_fn("CSIDL_LOCAL_APPDATA")
    finally:
        _cleanup_ctypes_mocks()


def test_get_win_folder_from_registry_unknown() -> None:
    # The lookup table is consulted before the platform guard, so this holds off Windows too.
    with pytest.raises(ValueError, match="Unknown CSIDL name: CSIDL_NOT_A_FOLDER"):
        get_win_folder_from_registry("CSIDL_NOT_A_FOLDER")


@pytest.mark.skipif(sys.platform == "win32", reason="on Windows the resolver reads the registry instead of raising")
@pytest.mark.parametrize("csidl_name", sorted(_KNOWN_FOLDER_GUIDS))
def test_get_win_folder_from_registry_knows_every_known_folder(csidl_name: str) -> None:
    # Reaching the platform guard proves the name is in the lookup table; a missing one raises ValueError instead.
    with pytest.raises(NotImplementedError):
        get_win_folder_from_registry(csidl_name)


@pytest.mark.skipif(sys.platform != "win32", reason="reads the live registry")
@pytest.mark.parametrize("csidl_name", sorted(_KNOWN_FOLDER_GUIDS))
def test_get_win_folder_from_registry_real(csidl_name: str) -> None:
    assert Path(get_win_folder_from_registry(csidl_name)).is_absolute()


@pytest.mark.parametrize("csidl_name", sorted(_KNOWN_FOLDER_GUIDS))
def test_get_win_folder_from_env_vars_knows_every_known_folder(
    monkeypatch: pytest.MonkeyPatch, csidl_name: str
) -> None:
    # Every folder the ctypes resolver finds must also be reachable without it; desktop was missing from both
    # fallbacks, so user_desktop_dir raised ValueError on a Windows build without ctypes.
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Test")
    monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Test\AppData\Local")
    monkeypatch.setenv("ALLUSERSPROFILE", r"C:\ProgramData")
    assert get_win_folder_from_env_vars(csidl_name).startswith("C:")


def test_known_folder_guids_has_all_csidl_names() -> None:
    expected = {
        "CSIDL_APPDATA",
        "CSIDL_COMMON_APPDATA",
        "CSIDL_LOCAL_APPDATA",
        "CSIDL_PERSONAL",
        "CSIDL_MYPICTURES",
        "CSIDL_MYVIDEO",
        "CSIDL_MYMUSIC",
        "CSIDL_DOWNLOADS",
        "CSIDL_DESKTOPDIRECTORY",
        "CSIDL_PROGRAMS",
        "CSIDL_COMMON_PROGRAMS",
    }
    assert set(_KNOWN_FOLDER_GUIDS.keys()) == expected


def test_pick_get_win_folder_ctypes(mocker: MockerFixture) -> None:
    if sys.platform != "win32":
        _setup_ctypes_mocks(mocker, win_dll=MagicMock())

    try:
        importlib.reload(windows)
        assert windows._pick_get_win_folder() is windows.get_win_folder_via_ctypes  # ruff:ignore[private-member-access]
    finally:
        if sys.platform != "win32":
            _cleanup_ctypes_mocks()


@pytest.mark.parametrize(
    ("csidl_name", "env_suffix"),
    [
        pytest.param("CSIDL_APPDATA", "APPDATA", id="appdata"),
        pytest.param("CSIDL_LOCAL_APPDATA", "LOCAL_APPDATA", id="local_appdata"),
        pytest.param("CSIDL_COMMON_APPDATA", "COMMON_APPDATA", id="common_appdata"),
        pytest.param("CSIDL_PERSONAL", "PERSONAL", id="personal"),
        pytest.param("CSIDL_DOWNLOADS", "DOWNLOADS", id="downloads"),
        pytest.param("CSIDL_MYPICTURES", "MYPICTURES", id="mypictures"),
        pytest.param("CSIDL_MYVIDEO", "MYVIDEO", id="myvideo"),
        pytest.param("CSIDL_MYMUSIC", "MYMUSIC", id="mymusic"),
        pytest.param("CSIDL_DESKTOPDIRECTORY", "DESKTOPDIRECTORY", id="desktop"),
        pytest.param("CSIDL_PROGRAMS", "PROGRAMS", id="programs"),
    ],
)
def test_get_win_folder_override(monkeypatch: pytest.MonkeyPatch, csidl_name: str, env_suffix: str) -> None:
    override_path = r"X:\custom\override"
    monkeypatch.setattr("platformdirs.windows._resolve_win_folder", lambda _csidl: _WIN_FOLDERS[_csidl])
    monkeypatch.setenv(f"WIN_PD_OVERRIDE_{env_suffix}", override_path)
    assert get_win_folder(csidl_name) == override_path


def test_get_win_folder_override_whitespace_only_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platformdirs.windows._resolve_win_folder", lambda csidl: _WIN_FOLDERS[csidl])
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", "   ")
    assert get_win_folder("CSIDL_LOCAL_APPDATA") == _WIN_FOLDERS["CSIDL_LOCAL_APPDATA"]


def test_get_win_folder_override_not_set_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platformdirs.windows._resolve_win_folder", lambda csidl: _WIN_FOLDERS[csidl])
    monkeypatch.delenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", raising=False)
    assert get_win_folder("CSIDL_LOCAL_APPDATA") == _WIN_FOLDERS["CSIDL_LOCAL_APPDATA"]


def test_get_win_folder_override_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platformdirs.windows._resolve_win_folder", lambda csidl: _WIN_FOLDERS[csidl])
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", "  X:\\custom  ")
    assert get_win_folder("CSIDL_LOCAL_APPDATA") == r"X:\custom"


def test_windows_iter_runtime_dirs_no_duplicate() -> None:
    # site_runtime_dir is defined as user_runtime_dir.
    expected = os.path.join(_LOCAL, "Temp", "bar", "foo")  # ruff:ignore[os-path-join]
    assert list(Windows(appname="foo", appauthor="bar").iter_runtime_dirs()) == [expected]
