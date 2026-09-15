from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest

import platformdirs
from platformdirs.macos import MacOS

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_XDG_ENV_VARS = (
    "XDG_DATA_HOME",
    "XDG_DATA_DIRS",
    "XDG_CONFIG_HOME",
    "XDG_CONFIG_DIRS",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
    "XDG_RUNTIME_DIR",
    "XDG_DOCUMENTS_DIR",
    "XDG_DOWNLOAD_DIR",
    "XDG_PICTURES_DIR",
    "XDG_VIDEOS_DIR",
    "XDG_MUSIC_DIR",
    "XDG_DESKTOP_DIR",
)


@pytest.fixture(autouse=True)
def _fix_os_pathsep(mocker: MockerFixture) -> None:
    """If we're not running on macOS, set `os.pathsep` to what it should be on macOS."""
    if sys.platform != "darwin":  # pragma: darwin no cover
        mocker.patch("os.pathsep", ":")
        mocker.patch("os.path.pathsep", ":")


@pytest.fixture
def _clear_xdg_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _XDG_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def home() -> str:
    return str(Path("~").expanduser())


@pytest.fixture
def _homebrew_py_prefix(mocker: MockerFixture) -> None:
    mocker.patch("sys.base_prefix", "/opt/homebrew/opt/python@3.13/Frameworks/Python.framework/Versions/3.13")


@pytest.fixture
def _builtin_py_prefix(mocker: MockerFixture) -> None:
    """Keep ``sys.base_prefix`` off the ``/opt/python`` Homebrew heuristic so directories use the system defaults."""
    py_version = sys.version_info
    mocker.patch(
        "sys.base_prefix",
        "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework"
        f"/Versions/{py_version.major}.{py_version.minor}",
    )


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no_args"),
        pytest.param({"appname": "foo"}, id="app_name"),
        pytest.param({"appname": "foo", "version": "v1.0"}, id="app_name_version"),
    ],
)
@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
def test_macos(home: str, params: dict[str, Any], func: str) -> None:
    result = getattr(MacOS(**params), func)

    suffix_elements = tuple(params[i] for i in ("appname", "version") if i in params)
    suffix = os.sep.join(("", *suffix_elements)) if suffix_elements else ""  # ruff:ignore[os-path-join]

    expected_map = {
        "user_data_dir": f"{home}/Library/Application Support{suffix}",
        "site_data_dir": f"/Library/Application Support{suffix}",
        "user_config_dir": f"{home}/Library/Application Support{suffix}",
        "site_config_dir": f"/Library/Application Support{suffix}",
        "user_cache_dir": f"{home}/Library/Caches{suffix}",
        "site_cache_dir": f"/Library/Caches{suffix}",
        "user_state_dir": f"{home}/Library/Application Support{suffix}",
        "site_state_dir": f"/Library/Application Support{suffix}",
        "user_log_dir": f"{home}/Library/Logs{suffix}",
        "site_log_dir": f"/Library/Logs{suffix}",
        "user_documents_dir": f"{home}/Documents",
        "user_downloads_dir": f"{home}/Downloads",
        "user_pictures_dir": f"{home}/Pictures",
        "user_videos_dir": f"{home}/Movies",
        "user_music_dir": f"{home}/Music",
        "user_desktop_dir": f"{home}/Desktop",
        "user_projects_dir": f"{home}/Projects",
        "user_publicshare_dir": f"{home}/Public",
        "user_templates_dir": f"{home}/Templates",
        "user_fonts_dir": f"{home}/Library/Fonts",
        "user_preference_dir": f"{home}/Library/Preferences{suffix}",
        "user_bin_dir": f"{home}/.local/bin",
        "site_bin_dir": "/usr/local/bin",
        "user_applications_dir": f"{home}/Applications",
        "site_applications_dir": "/Applications",
        "user_runtime_dir": f"{home}/Library/Caches/TemporaryItems{suffix}",
        "site_runtime_dir": f"{home}/Library/Caches/TemporaryItems{suffix}",
    }
    expected = expected_map[func]

    assert result == expected


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no_args"),
        pytest.param({"appname": "foo"}, id="app_name"),
        pytest.param({"appname": "foo", "version": "v1.0"}, id="app_name_version"),
    ],
)
@pytest.mark.parametrize(
    "site_func",
    [
        "site_data_dir",
        "site_config_dir",
        "site_cache_dir",
        "site_runtime_dir",
        "site_cache_path",
        "site_data_path",
        "site_config_path",
    ],
)
@pytest.mark.parametrize("multipath", [pytest.param(True, id="multipath"), pytest.param(False, id="singlepath")])
@pytest.mark.usefixtures("_clear_xdg_env")
def test_macos_homebrew(
    mocker: MockerFixture, home: str, params: dict[str, Any], multipath: bool, site_func: str
) -> None:
    test_data = [
        {
            "sys_prefix": "/opt/homebrew/opt/python@3.13/Frameworks/Python.framework/Versions/3.13",
            "homebrew_prefix": "/opt/homebrew",
        },
        {
            "sys_prefix": "/usr/local/opt/python@3.13/Frameworks/Python.framework/Versions/3.13",
            "homebrew_prefix": "/usr/local",
        },
        {
            "sys_prefix": "/myown/arbitrary/prefix/opt/python@3.13/Frameworks/Python.framework/Versions/3.13",
            "homebrew_prefix": "/myown/arbitrary/prefix",
        },
    ]
    for prefix in test_data:
        mocker.patch("sys.base_prefix", prefix["sys_prefix"])

        result = getattr(MacOS(multipath=multipath, **params), site_func)

        suffix_elements = tuple(params[i] for i in ("appname", "version") if i in params)
        suffix = os.sep.join(("", *suffix_elements)) if suffix_elements else ""  # ruff:ignore[os-path-join]

        expected_path_map = {
            "site_cache_path": Path(f"{prefix['homebrew_prefix']}/var/cache{suffix}"),
            "site_data_path": Path(f"{prefix['homebrew_prefix']}/share{suffix}"),
            "site_config_path": Path(f"{prefix['homebrew_prefix']}/share{suffix}"),
        }
        expected_map = {
            "site_data_dir": f"{prefix['homebrew_prefix']}/share{suffix}",
            "site_config_dir": f"{prefix['homebrew_prefix']}/share{suffix}",
            "site_cache_dir": f"{prefix['homebrew_prefix']}/var/cache{suffix}",
            "site_runtime_dir": f"{home}/Library/Caches/TemporaryItems{suffix}",
        }
        if multipath:
            expected_map["site_data_dir"] += f":/Library/Application Support{suffix}"
            expected_map["site_config_dir"] += f":/Library/Application Support{suffix}"
            expected_map["site_cache_dir"] += f":/Library/Caches{suffix}"
        expected = expected_path_map[site_func] if site_func.endswith("_path") else expected_map[site_func]

        assert result == expected


@pytest.mark.usefixtures("_clear_xdg_env", "_homebrew_py_prefix")
@pytest.mark.parametrize("suffix", ["dir", "path"])
@pytest.mark.parametrize("name", ["site_data", "site_config", "site_cache", "site_applications"])
def test_multipath_reaches_the_module_function(mocker: MockerFixture, name: str, suffix: str) -> None:
    mocker.patch("platformdirs.PlatformDirs", MacOS)
    function = getattr(platformdirs, f"{name}_{suffix}")
    expected = getattr(MacOS(appname="foo", multipath=True), f"{name}_{suffix}")
    assert function(appname="foo", multipath=True) == expected


@pytest.mark.parametrize(
    ("env_var", "prop", "xdg_path"),
    [
        pytest.param("XDG_DATA_HOME", "user_data_dir", "/custom/data", id="user_data_dir"),
        pytest.param("XDG_CONFIG_HOME", "user_config_dir", "/custom/config", id="user_config_dir"),
        pytest.param("XDG_CACHE_HOME", "user_cache_dir", "/custom/cache", id="user_cache_dir"),
        pytest.param("XDG_STATE_HOME", "user_state_dir", "/custom/state", id="user_state_dir"),
        pytest.param("XDG_RUNTIME_DIR", "user_runtime_dir", "/custom/runtime", id="user_runtime_dir"),
        pytest.param("XDG_RUNTIME_DIR", "site_runtime_dir", "/custom/runtime", id="site_runtime_dir"),
    ],
)
@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no_args"),
        pytest.param({"appname": "foo"}, id="app_name"),
        pytest.param({"appname": "foo", "version": "v1.0"}, id="app_name_version"),
    ],
)
def test_macos_xdg_env_vars(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    prop: str,
    xdg_path: str,
    params: dict[str, Any],
) -> None:
    monkeypatch.setenv(env_var, xdg_path)
    result = getattr(MacOS(**params), prop)
    suffix_elements = tuple(params[i] for i in ("appname", "version") if i in params)
    suffix = os.sep.join(("", *suffix_elements)) if suffix_elements else ""  # ruff:ignore[os-path-join]
    assert result == f"{xdg_path}{suffix}"


@pytest.mark.parametrize(
    ("env_var", "prop"),
    [
        pytest.param("XDG_DATA_DIRS", "site_data_dir", id="site_data_dir"),
        pytest.param("XDG_CONFIG_DIRS", "site_config_dir", id="site_config_dir"),
    ],
)
@pytest.mark.parametrize("multipath", [pytest.param(True, id="multipath"), pytest.param(False, id="singlepath")])
def test_macos_xdg_site_dirs(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    prop: str,
    multipath: bool,
) -> None:
    monkeypatch.setenv(env_var, "/custom/first:/custom/second")
    result = getattr(MacOS(multipath=multipath), prop)
    if multipath:
        assert result == "/custom/first:/custom/second"
    else:
        assert result == "/custom/first"


@pytest.mark.parametrize(
    ("env_var", "prop"),
    [
        pytest.param("XDG_DOCUMENTS_DIR", "user_documents_dir", id="user_documents_dir"),
        pytest.param("XDG_DOWNLOAD_DIR", "user_downloads_dir", id="user_downloads_dir"),
        pytest.param("XDG_PICTURES_DIR", "user_pictures_dir", id="user_pictures_dir"),
        pytest.param("XDG_VIDEOS_DIR", "user_videos_dir", id="user_videos_dir"),
        pytest.param("XDG_MUSIC_DIR", "user_music_dir", id="user_music_dir"),
        pytest.param("XDG_DESKTOP_DIR", "user_desktop_dir", id="user_desktop_dir"),
    ],
)
def test_macos_xdg_media_dirs(monkeypatch: pytest.MonkeyPatch, env_var: str, prop: str) -> None:
    monkeypatch.setenv(env_var, "/custom/media")
    assert getattr(MacOS(), prop) == "/custom/media"


@pytest.mark.parametrize(
    ("env_var", "prop"),
    [
        pytest.param("XDG_DATA_HOME", "user_data_dir", id="user_data_dir"),
        pytest.param("XDG_CONFIG_HOME", "user_config_dir", id="user_config_dir"),
        pytest.param("XDG_CACHE_HOME", "user_cache_dir", id="user_cache_dir"),
        pytest.param("XDG_STATE_HOME", "user_state_dir", id="user_state_dir"),
        pytest.param("XDG_RUNTIME_DIR", "user_runtime_dir", id="user_runtime_dir"),
        pytest.param("XDG_DOCUMENTS_DIR", "user_documents_dir", id="user_documents_dir"),
        pytest.param("XDG_DOWNLOAD_DIR", "user_downloads_dir", id="user_downloads_dir"),
        pytest.param("XDG_PICTURES_DIR", "user_pictures_dir", id="user_pictures_dir"),
        pytest.param("XDG_VIDEOS_DIR", "user_videos_dir", id="user_videos_dir"),
        pytest.param("XDG_MUSIC_DIR", "user_music_dir", id="user_music_dir"),
        pytest.param("XDG_DESKTOP_DIR", "user_desktop_dir", id="user_desktop_dir"),
    ],
)
@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
def test_macos_xdg_empty_falls_back(monkeypatch: pytest.MonkeyPatch, home: str, env_var: str, prop: str) -> None:
    monkeypatch.setenv(env_var, "")
    expected_map = {
        "user_data_dir": f"{home}/Library/Application Support",
        "user_config_dir": f"{home}/Library/Application Support",
        "user_cache_dir": f"{home}/Library/Caches",
        "user_state_dir": f"{home}/Library/Application Support",
        "user_runtime_dir": f"{home}/Library/Caches/TemporaryItems",
        "user_documents_dir": f"{home}/Documents",
        "user_downloads_dir": f"{home}/Downloads",
        "user_pictures_dir": f"{home}/Pictures",
        "user_videos_dir": f"{home}/Movies",
        "user_music_dir": f"{home}/Music",
        "user_desktop_dir": f"{home}/Desktop",
        "user_projects_dir": f"{home}/Projects",
        "user_publicshare_dir": f"{home}/Public",
        "user_templates_dir": f"{home}/Templates",
        "user_fonts_dir": f"{home}/Library/Fonts",
        "user_preference_dir": f"{home}/Library/Preferences",
        "user_bin_dir": f"{home}/.local/bin",
        "site_bin_dir": "/usr/local/bin",
        "user_applications_dir": f"{home}/Applications",
    }
    assert getattr(MacOS(), prop) == expected_map[prop]


@pytest.mark.parametrize(
    ("env_var", "prop"),
    [
        pytest.param("XDG_DATA_HOME", "user_data_dir", id="user_data_dir"),
        pytest.param("XDG_CONFIG_HOME", "user_config_dir", id="user_config_dir"),
        pytest.param("XDG_CACHE_HOME", "user_cache_dir", id="user_cache_dir"),
        pytest.param("XDG_STATE_HOME", "user_state_dir", id="user_state_dir"),
        pytest.param("XDG_RUNTIME_DIR", "user_runtime_dir", id="user_runtime_dir"),
    ],
)
@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("relative/dir", id="relative"),
        pytest.param("~/dir", id="tilde"),
        pytest.param("$HOME/dir", id="unexpanded-home"),
        pytest.param("C:/dir", id="windows-drive"),
    ],
)
def test_macos_xdg_relative_falls_back(
    monkeypatch: pytest.MonkeyPatch, home: str, env_var: str, prop: str, value: str
) -> None:
    monkeypatch.setenv(env_var, value)
    expected_map = {
        "user_data_dir": f"{home}/Library/Application Support",
        "user_config_dir": f"{home}/Library/Application Support",
        "user_cache_dir": f"{home}/Library/Caches",
        "user_state_dir": f"{home}/Library/Application Support",
        "user_runtime_dir": f"{home}/Library/Caches/TemporaryItems",
    }
    assert getattr(MacOS(), prop) == expected_map[prop]


@pytest.mark.parametrize(
    ("env_var_1", "prop_1", "env_var_2", "prop_2"),
    [
        pytest.param("XDG_DATA_HOME", "user_data_dir", "XDG_CONFIG_HOME", "user_config_dir", id="data/config"),
        pytest.param("XDG_DATA_HOME", "user_data_dir", "XDG_STATE_HOME", "user_state_dir", id="data/state"),
        pytest.param("XDG_CONFIG_HOME", "user_config_dir", "XDG_STATE_HOME", "user_state_dir", id="config/state"),
    ],
)
@pytest.mark.usefixtures("_clear_xdg_env")
def test_no_xdg_vars_leak(
    monkeypatch: pytest.MonkeyPatch, env_var_1: str, prop_1: str, env_var_2: str, prop_2: str
) -> None:
    value_1, value_2 = ("/foo/bar", "/xyz/jkl")

    monkeypatch.setenv(env_var_1, value_1)
    monkeypatch.setenv(env_var_2, "")
    assert getattr(MacOS(), prop_1) == value_1
    assert getattr(MacOS(), prop_1) != getattr(MacOS(), prop_2)

    monkeypatch.setenv(env_var_1, "")
    monkeypatch.setenv(env_var_2, value_2)
    assert getattr(MacOS(), prop_2) == value_2
    assert getattr(MacOS(), prop_1) != getattr(MacOS(), prop_2)

    monkeypatch.setenv(env_var_1, value_1)
    monkeypatch.setenv(env_var_2, value_2)
    assert getattr(MacOS(), prop_1) == value_1
    assert getattr(MacOS(), prop_2) == value_2


def test_iter_data_dirs_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/xdg/data")
    monkeypatch.setenv("XDG_DATA_DIRS", "/xdg/share1:/xdg/share2")
    dirs = list(MacOS().iter_data_dirs())
    assert dirs == ["/xdg/data", "/xdg/share1", "/xdg/share2"]


def test_iter_config_dirs_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg/config")
    monkeypatch.setenv("XDG_CONFIG_DIRS", "/xdg/etc1:/xdg/etc2")
    dirs = list(MacOS().iter_config_dirs())
    assert dirs == ["/xdg/config", "/xdg/etc1", "/xdg/etc2"]


@pytest.mark.usefixtures("_clear_xdg_env", "_homebrew_py_prefix")
def test_iter_data_dirs_homebrew(home: str) -> None:
    dirs = list(MacOS().iter_data_dirs())
    assert dirs == [f"{home}/Library/Application Support", "/opt/homebrew/share", "/Library/Application Support"]


@pytest.mark.usefixtures("_clear_xdg_env", "_homebrew_py_prefix")
def test_iter_config_dirs_homebrew(home: str) -> None:
    dirs = list(MacOS().iter_config_dirs())
    assert dirs == [f"{home}/Library/Application Support", "/opt/homebrew/share", "/Library/Application Support"]


@pytest.mark.usefixtures("_clear_xdg_env")
def test_site_applications_path_multipath_returns_first_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_DIRS", f"/custom/first{os.pathsep}/custom/second")
    assert MacOS(multipath=True).site_applications_path == Path("/custom/first/applications")


@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(":", id="single"),
        pytest.param("::", id="double"),
        pytest.param(" : ", id="padded"),
        pytest.param(": :", id="spaced"),
        pytest.param("relative/dir", id="relative"),
        pytest.param("relative/dir:another/dir", id="all-relative"),
    ],
)
@pytest.mark.parametrize("prop", ["site_data_dir", "site_config_dir", "site_applications_dir"])
def test_site_dirs_fall_back_when_xdg_var_has_no_absolute_paths(
    monkeypatch: pytest.MonkeyPatch, prop: str, value: str
) -> None:
    monkeypatch.setenv("XDG_CONFIG_DIRS" if prop == "site_config_dir" else "XDG_DATA_DIRS", value)
    expected = {
        "site_data_dir": os.path.join("/Library/Application Support", "foo"),  # ruff:ignore[os-path-join]
        "site_config_dir": os.path.join("/Library/Application Support", "foo"),  # ruff:ignore[os-path-join]
        "site_applications_dir": "/Applications",
    }[prop]
    assert getattr(MacOS(appname="foo"), prop) == expected


@pytest.mark.usefixtures("_clear_xdg_env", "_homebrew_py_prefix")
@pytest.mark.parametrize("multipath", [True, False])
def test_iter_cache_dirs_homebrew(home: str, multipath: bool) -> None:
    dirs = list(MacOS(multipath=multipath).iter_cache_dirs())
    assert dirs == [f"{home}/Library/Caches", "/opt/homebrew/var/cache", "/Library/Caches"]


@pytest.mark.usefixtures("_clear_xdg_env", "_homebrew_py_prefix")
def test_iter_cache_paths_homebrew_multipath(home: str) -> None:
    paths = list(MacOS(multipath=True).iter_cache_paths())
    assert paths == [Path(f"{home}/Library/Caches"), Path("/opt/homebrew/var/cache"), Path("/Library/Caches")]


@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
def test_iter_data_dirs_no_homebrew(home: str) -> None:
    dirs = list(MacOS().iter_data_dirs())
    assert dirs == [f"{home}/Library/Application Support", "/Library/Application Support"]


@pytest.mark.usefixtures("_clear_xdg_env")
def test_no_xdg_site_dirs_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    data_value, config_value = ("/foo/bar/data", "/xyz/jkl/config")

    monkeypatch.setenv("XDG_DATA_DIRS", data_value)
    monkeypatch.setenv("XDG_CONFIG_DIRS", "")
    data_dirs = list(MacOS().iter_data_dirs())
    config_dirs = list(MacOS().iter_config_dirs())
    assert data_value in data_dirs
    assert data_value not in config_dirs

    monkeypatch.setenv("XDG_DATA_DIRS", "")
    monkeypatch.setenv("XDG_CONFIG_DIRS", config_value)
    data_dirs = list(MacOS().iter_data_dirs())
    config_dirs = list(MacOS().iter_config_dirs())
    assert config_value in config_dirs
    assert config_value not in data_dirs

    monkeypatch.setenv("XDG_DATA_DIRS", data_value)
    monkeypatch.setenv("XDG_CONFIG_DIRS", config_value)
    data_dirs = list(MacOS().iter_data_dirs())
    config_dirs = list(MacOS().iter_config_dirs())
    assert data_value in data_dirs
    assert config_value in config_dirs
    assert config_value not in data_dirs
    assert data_value not in config_dirs


@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
def test_macos_site_runtime_path(home: str) -> None:
    result = MacOS(appname="foo").site_runtime_path
    assert result == Path(f"{home}/Library/Caches/TemporaryItems/foo")


@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
def test_macos_ensure_exists_preexisting_dir(mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch("platformdirs.macos.os.path.expanduser", lambda p: str(tmp_path / p.lstrip("~/")))
    dirs = MacOS(appname="foo", ensure_exists=True)
    first = dirs.user_data_dir
    assert Path(first).exists()
    # Calling again with an already-existing directory must not raise.
    second = dirs.user_data_dir
    assert first == second


@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
def test_macos_iter_runtime_dirs_no_duplicate(home: str) -> None:
    # site_runtime_dir is defined as user_runtime_dir.
    expected = os.path.join(f"{home}/Library/Caches/TemporaryItems", "foo")  # ruff:ignore[os-path-join]
    assert list(MacOS(appname="foo").iter_runtime_dirs()) == [expected]


@pytest.mark.usefixtures("_clear_xdg_env")
@pytest.mark.parametrize(
    "homebrew_prefix",
    [
        pytest.param("/opt/homebrew", id="apple-silicon"),
        pytest.param("/usr/local", id="intel"),
        pytest.param("/custom/brew", id="custom-prefix"),
    ],
)
@pytest.mark.parametrize("multipath", [pytest.param(True, id="multipath"), pytest.param(False, id="singlepath")])
@pytest.mark.parametrize(
    "prop",
    [
        "site_data_dir",
        "site_config_dir",
        "site_cache_dir",
        "site_state_dir",
        "site_data_path",
        "site_config_path",
        "site_cache_path",
        "site_state_path",
    ],
)
def test_homebrew_virtual_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, homebrew_prefix: str, prop: str, multipath: bool
) -> None:
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    monkeypatch.setattr(
        sys, "base_prefix", f"{homebrew_prefix}/opt/python@3.13/Frameworks/Python.framework/Versions/3.13"
    )
    suffix: Final = "var/cache" if "cache" in prop else "share"
    expected: str | Path = f"{homebrew_prefix}/{suffix}{os.sep}Example{os.sep}1.0"
    if prop.endswith("_path"):
        expected = Path(expected)
    elif multipath and prop != "site_state_dir":
        fallback: Final = "Caches" if "cache" in prop else "Application Support"
        expected += f":/Library/{fallback}{os.sep}Example{os.sep}1.0"
    assert getattr(MacOS(appname="Example", version="1.0", multipath=multipath), prop) == expected


@pytest.mark.usefixtures("_clear_xdg_env", "_builtin_py_prefix")
@pytest.mark.parametrize(
    ("prop", "expected"),
    [
        pytest.param("site_data_dir", "/Library/Application Support", id="data"),
        pytest.param("site_config_dir", "/Library/Application Support", id="config"),
        pytest.param("site_cache_dir", "/Library/Caches", id="cache"),
        pytest.param("site_state_dir", "/Library/Application Support", id="state"),
    ],
)
def test_non_homebrew_base_ignores_virtual_environment_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, prop: str, expected: str
) -> None:
    monkeypatch.setattr(sys, "prefix", (tmp_path / "opt/python/.venv").as_posix())
    assert getattr(MacOS(), prop) == expected
