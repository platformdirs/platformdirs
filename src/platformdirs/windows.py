import ctypes
import os
import sys
from functools import lru_cache
from typing import Callable, Optional

from .api import PlatformDirsABC


class Windows(PlatformDirsABC):
    """`MSDN on where to store app data files
    <http://support.microsoft.com/default.aspx?scid=kb;en-us;310294#XSLTH3194121123120121120120>`_.
    Makes use of the
    `appname <platformdirs.api.PlatformDirsABC.appname>`,
    `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`,
    `version <platformdirs.api.PlatformDirsABC.version>`,
    `roaming <platformdirs.api.PlatformDirsABC.roaming>`,
    `opinion <platformdirs.api.PlatformDirsABC.opinion>`."""

    @classmethod
    def is_active(cls) -> bool:
        """:return: a check to detect if Windows platform is currently active"""
        return sys.platform == "win32"

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname`` (not roaming) or
         ``%USERPROFILE%\\AppData\\Roaming\\$appauthor\\$appname`` (roaming)
        """
        const = "CSIDL_APPDATA" if self.roaming else "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(get_win_folder(const))
        return self._path_with_app_version(path)

    def _path_with_app_version(self, path: str, *, opinion_value: Optional[str] = None) -> str:
        if self.appname:
            assert self.appname is not None
            if self.appauthor is not False:
                author = self.appauthor or self.appname
                path = os.path.join(path, author, self.appname)
            else:
                path = os.path.join(path, self.appname)
            if opinion_value is not None and self.opinion:
                path = os.path.join(path, "Cache")
            if self.version:
                path = os.path.join(path, self.version)
        return path

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._path_with_app_version(path)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user (if opinionated with ``Cache`` folder within ``$appname``) e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname\\Cache\\$version``
        """
        path = os.path.normpath(get_win_folder("CSIDL_LOCAL_APPDATA"))
        return self._path_with_app_version(path, opinion_value="Cache")

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """
        :return: log directory tied to the user, same as `user_data_dir` if not opinionated else ``Logs`` in it
        """
        path = self.user_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")
        return path


def get_win_folder_from_env_vars(csidl_name: str) -> str:
    """Get folder from environment variables."""
    env_var_name = {
        "CSIDL_APPDATA": "APPDATA",
        "CSIDL_COMMON_APPDATA": "ALLUSERSPROFILE",
        "CSIDL_LOCAL_APPDATA": "LOCALAPPDATA",
    }.get(csidl_name)
    if env_var_name is None:
        raise ValueError(f"Unknown CSIDL name: {csidl_name}")
    result = os.environ.get(env_var_name)
    if result is None:
        raise ValueError(f"Unset environment variable: {env_var_name}")
    return result


def get_win_folder_from_registry(csidl_name: str) -> str:
    """Get folder from the registry.

    This is a fallback technique at best. I'm not sure if using the
    registry for this guarantees us the correct answer for all CSIDL_*
    names.
    """
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }.get(csidl_name)
    if shell_folder_name is None:
        raise ValueError(f"Unknown CSIDL name: {csidl_name}")

    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
    return str(directory)


def get_win_folder_via_ctypes(csidl_name: str) -> str:
    """Get folder with ctypes."""
    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }.get(csidl_name)
    if csidl_const is None:
        raise ValueError(f"Unknown CSIDL name: {csidl_name}")

    buf = ctypes.create_unicode_buffer(1024)
    windll = getattr(ctypes, "windll")  # noqa: B009 # using getattr to avoid false positive with mypy type checker
    windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    has_high_char = False  # Downgrade to short path name if it has highbit chars.
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value


def _pick_get_win_folder() -> Callable[[str], str]:
    if hasattr(ctypes, "windll"):
        return get_win_folder_via_ctypes
    try:
        import winreg  # noqa: F401
    except ImportError:
        return get_win_folder_from_env_vars
    else:
        return get_win_folder_from_registry


get_win_folder = lru_cache(maxsize=None)(_pick_get_win_folder())

__all__ = [
    "Windows",
]