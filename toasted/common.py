# MIT License
# 
# Copyright (c) 2022 ysfchn
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = [
    "resolve_uri"
]

from toasted.enums import _ToastElementType, ToastDismissReason, _ToastXMLTag

from abc import ABC, abstractmethod
from typing import (
    Dict,
    NamedTuple,
    Any,
    Optional,
    Sequence,
    Set, 
    Tuple, 
    Type, 
    List,
    Union,
    Literal
)
from os import environ
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl
from pathlib import Path
from base64 import b64decode
import string
from io import BytesIO
from xml.etree import ElementTree as ET

from PIL import Image, ImageFont, ImageDraw, ImageColor

if sys.platform == "win32":
    import winreg
    from winrt.windows.storage import SystemDataPaths # pyright: ignore[reportMissingImports]
else:
    class Proxy:
        def __getattribute__(self, _): raise Exception("Toasted is not supported on non-Windows platforms.") # noqa: E501
    winreg = SystemDataPaths = Proxy()


class ToastThemeInfo(NamedTuple):
    contrast : Literal["high", "standard"]
    lang : str
    theme : Literal["dark", "light"]
    
    def as_params(self):
        return {
            "ms-contrast": self.contrast,
            "ms-lang": self.lang,
            "ms-theme": self.theme
        }


class URIResult(NamedTuple):
    value: str
    type: Literal["local", "remote", "hex", "resource"]


def resolve_uri(
    uri : str
) -> URIResult:
    """
    Resolve a local file path or an URI locating a file or remote source.
    """
    split = urlsplit(uri, allow_fragments = False)

    # See here for all file path formats on Windows:
    # https://learn.microsoft.com/en-us/dotnet/standard/io/file-path-formats
    # UNC and DOS paths are not supported.

    # Relative file path.
    # e.g. "./myfolder/myfile"
    if not split.scheme:
        return URIResult(
            value = str(Path(split.path).resolve().absolute()),
            type = "local"
        )

    # Drive letters as a scheme, should also work on mixed slashes due to URL normalization above.
    # e.g. "C:\Users\ysfchn\Desktop"
    elif (len(split.scheme) == 1) and (ord(split.scheme) in range(97, 123)):
        return URIResult(
            value = str(Path(f"{split.scheme}:{split.path}").resolve().absolute()),
            type = "local"
        )

    # UWP apps has additional schemes:
    # https://learn.microsoft.com/en-us/windows/uwp/app-resources/uri-schemes

    # "ms-appx" scheme is relative to the installation directory, since there is no
    # installation in our case, we use current working directory as a base.
    # e.g. "ms-appx:///images/logo.png"
    
    elif split.scheme == "ms-appx":
        path = Path(split.netloc + split.path)

        # Force all paths to be relative, even if it starts with a slash ("/").
        # Other schemes should be used instead for working with absolute paths. 
        return URIResult(
            value = str((Path.cwd() / path.relative_to(path.anchor)).resolve().absolute()),
            type = "local"
        )

    # "ms-appdata" scheme returns the location of appdata folder.
    # First segment of the path must be one of these: "local", "roaming" or "temp"
    # https://learn.microsoft.com/en-us/windows/uwp/app-resources/uri-schemes#path-ms-appdata
    # e.g. "ms-appdata:///local/MyApp"

    elif split.scheme == "ms-appdata":
        path = Path(split.netloc + split.path)
        path = path.relative_to(path.anchor)
        reserved = path.parts[0]
        path = path.relative_to(reserved)

        base_path = None
        if reserved == "local":
            base_path = Path(environ["LOCALAPPDATA"])
        elif reserved == "temp":
            base_path = Path(environ["LOCALAPPDATA"]) / "Temp"
        elif reserved == "roaming":
            base_path = Path(environ["APPDATA"]) / "Roaming"

        if not base_path:
            raise ValueError(f"First segment must be 'local', 'temp' or 'roaming' on 'ms-appdata' URIs: '{uri}'")

        resolved = (base_path / path).resolve()

        # Microsoft says it is not allowed to go outside from the reserved folders,
        # so let's do the same here.
        if not resolved.is_relative_to(base_path):
            raise ValueError(f"Visiting parent from a 'ms-appdata' path is not allowed: '{uri}'")

        return URIResult(
            value = str(resolved.absolute()),
            type = "local"
        )

    # "ms-winsoundevent" scheme is used for default toast notification sound enum,
    # so we just return it as-is.
    # e.g. "ms-winsoundevent:Notification.SMS"

    elif split.scheme == "ms-winsoundevent":
        return URIResult(
            value = f"ms-winsoundevent:{split.path}",
            type = "resource"
        )

    # "file" scheme should resolve path same as without the scheme.
    elif split.scheme == "file":
        # Parsing "file://C:/Users" makes netloc to have "C:", but adding another forward slash
        # into "file://" scheme (like "file:///C:/Users") breaks the splitting, since netloc would become empty.
        # So, we manually remove the slash to make 3 slashes behave same with 2 slashes if there is no netloc.
        path = Path(split.netloc + split.path if split.netloc else split.netloc + split.path.removeprefix("/"))
        return URIResult(
            value = str(path.resolve().absolute()),
            type = "local"
        )

    # If scheme is "http" or "https", left as-is.
    elif (split.scheme == "http") or (split.scheme == "https"):
        return URIResult(
            value = urlunsplit(split),
            type = "remote"
        )

    # Allow returning arbitrary bytes if scheme is "data" to avoid needing to have an actual
    # file on filesystem. Should be only used for small files though.
    # e.g. "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ=="
    elif split.scheme == "data":
        data_uri = split.path.removeprefix("/")

        if data_uri.count(";base64,") == 1:
            return URIResult(
                value = b64decode(data_uri.split(";base64,")[-1]).hex(),
                type = "hex"
            )

        raise ValueError(f"Invalid base64 data URI: '{uri}'")

    # Extract icons from Windows icon.
    elif split.scheme == "icon":
        values = dict(parse_qsl(split.query))
        hex_value = (split.netloc or split.path).removeprefix("/").removeprefix("U+").removeprefix("0x")
        hex_digits = set(string.hexdigits)

        if not all(c in hex_digits for c in hex_value):
            raise ValueError(
                f"Icon URI path needs to be a hex value of character point: '{uri}'"
            )

        icon_data = get_icon_from_font(
            charcode = int(hex_value, 16),
            font_file = str(get_icon_font_default()),
            foreground = ImageColor.getrgb(values.get("foreground", None) or "#000000FF"), # noqa: E501
            background = ImageColor.getrgb(values.get("background", None) or "#00000000"), # noqa: E501
            icon_padding = int(values.get("padding", None) or 0)
        )

        return URIResult(
            value = icon_data.hex(),
            type = "hex"
        )

    raise ValueError(f"Invalid or unsupported URI: '{uri}'")


def is_in_venv() -> bool:
    """
    Returns True if Python is launched in a virtualenv or similar environments.
    Otherwise, False. 
    
    This check is required because since in virtual environment, there will be 
    no Python installed on the system, toast notifications will fail to display 
    as toast notification default app ID is set to sys.executable.

    TODO: Maybe add this check before showing a toast?
    """
    return bool(
        environ.get("CONDA_PREFIX", None) or \
        environ.get("VIRTUAL_ENV", None) or \
        getattr(sys, "real_prefix", sys.base_prefix) != sys.prefix
    )


def get_icon_from_font(
    charcode : int,
    font_file : Union[str, bytes],
    icon_size : int = 64,
    icon_padding : int = 0,
    background : "Image._Color" = (0, 0, 0, 0), # type: ignore
    foreground : "Image._Color" = (255, 255, 255, 255), # type: ignore
    icon_format : str = "png"
) -> bytes:
    """
    Create a image with a character from given icon font file 
    and return the created image in given format as bytes.

    Used to extract system icons from built-in Windows icon fonts
    such as "Segoe MDL2 Assets".

    https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-ui-symbol-font
    """
    image_size = icon_size + icon_padding
    image = Image.new("RGBA", (image_size, image_size), background)
    draw = ImageDraw.Draw(image)
    if not font_file:
        raise ValueError("No font has provided!")
    asset_font = ImageFont.truetype(
        font_file, size = icon_size, 
        layout_engine = ImageFont.Layout.BASIC
    )
    text_content = chr(charcode)
    text_length = draw.textlength(text_content, asset_font)
    # If text length exceeds the icon size, make text smaller.
    if text_length > icon_size:
        asset_font = asset_font.font_variant(
            size = icon_size - ((text_length - icon_size) // 2) - (icon_size // 12)
        )
    # Draw text to the image.
    draw.text(
        xy = (image_size // 2, image_size // 2), text = text_content,
        fill = foreground, font = asset_font, align = "center", 
        anchor = "mm", spacing = 0
    )
    buffer = BytesIO()
    image.save(buffer, icon_format)
    return buffer.getvalue()


def get_icon_fonts_path() -> List[Tuple[Literal["mdl2", "fluent"], Path]]:
    """
    Returns a list of file paths of Segoe MDL2 and Segoe Fluent
    fonts from registry. MDL2 comes preinstalled in Windows 10 and onwards,
    and Fluent is preinstalled in Windows 11 and onwards, and both of
    these fonts can also be installed separetely.

    Fluent Icons: https://aka.ms/SegoeFluentIcons
    MDL2 Icons: https://aka.ms/segoemdl2
    """
    available = []
    fonts = {
        "mdl2": "Segoe MDL2 Assets (TrueType)",
        "fluent": "Segoe Fluent Icons Normal (TrueType)"
    }
    system_fonts = winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, 
        "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"
    )
    user_fonts = None
    try:
        user_fonts = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"
        )
    except OSError as ore:
        if ore.errno != 2:
            raise ore
    # system_fonts_path = Path(SystemDataPaths.get_default().fonts)
    # Check for system fonts.
    system_fonts_count = winreg.QueryInfoKey(system_fonts)[1]
    for i in range(system_fonts_count):
        name, file, _ = winreg.EnumValue(system_fonts, i)
        for k, v in fonts.items():
            if name == v:
                font_path = Path(file)
                # if not font_path.is_absolute():
                #    font_path = system_fonts_path.joinpath(font_path)
                available.append((k, font_path))
    system_fonts.Close()
    # Check for user fonts.
    if user_fonts:
        user_fonts_count = winreg.QueryInfoKey(user_fonts)[1]
        for i in range(user_fonts_count):
            name, file, _ = winreg.EnumValue(user_fonts, i)
            for k, v in fonts.items():
                if name == v:
                    available.append((k, Path(file)))
    return available


def get_query_app_ids(is_user : bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Return a mapping of all AUMIDs (App User Model IDs) and their values
    such as its display name and icon.
    """
    output = {}
    aumids = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER if is_user else winreg.HKEY_LOCAL_MACHINE, 
        "SOFTWARE\\Classes\\AppUserModelId"
    )
    key_count = winreg.QueryInfoKey(aumids)[0]
    for i in range(key_count):
        app_id = winreg.EnumKey(aumids, i)
        app_info = winreg.OpenKey(aumids, app_id)
        values = {}
        value_count = winreg.QueryInfoKey(app_info)[1]
        for j in range(value_count):
            k, v, _ = winreg.EnumValue(app_info, j)
            values[k] = v
        output[app_id] = values
    return output


def get_windows_build() -> int:
    """
    Gets Windows build number.
    https://en.wikipedia.org/wiki/List_of_Microsoft_Windows_versions
    """
    return sys.getwindowsversion().build


def get_icon_font_default() -> Path:
    """
    Returns the path of recommended icon font
    to be used in toast icons.
    """
    fonts = dict(get_icon_fonts_path())
    # Windows 11 comes with fluent icons by default.
    if get_windows_build() >= 22000:
        if "fluent" in fonts:
            return fonts["fluent"]
    # For Windows 10, prefer MDL2 instead.
    if "mdl2" in fonts:
        return fonts["mdl2"]
    raise ValueError("Couldn't find an available icon font.")


class ToastBase(ABC):
    __slots__ = ()

    @abstractmethod
    def _to_xml(self) -> ET.Element:
        ...
    
    @classmethod
    def from_json(cls, data : Dict[str, Any]):
        return cls(**data)


class ToastState:
    def __init__(self) -> None:
        self._provided : bool = False
        self._arguments : Optional[str] = None
        self._inputs : Optional[dict] = None
        self._params : Optional[dict] = None
        self._dismiss_reason : Optional[ToastDismissReason] = None
        self._cleared : bool = False

    @property
    def arguments(self):
        return self._arguments

    @property
    def user_input(self):
        return self._inputs or dict()

    @property
    def template_data(self):
        return self._params or dict()

    @property
    def reason(self):
        return self._dismiss_reason

    @property
    def removed(self):
        if self._arguments is not None:
            return True
        return self._cleared

    def __bool__(self):
        return self.removed

    def __repr__(self) -> str:
        return "<{0} arguments={1} inputs={2} params={3} reason={4} removed={5}>".format(
            self.__class__.__name__,
            None if self._arguments is None else f'"{self._arguments}"',
            self._inputs,
            self._params,
            None if self._dismiss_reason is None else self._dismiss_reason.name,
            self.removed
        )

class _ToastContextState(NamedTuple):
    arguments: Optional[str]
    params: Dict[str, str]
    inputs: Dict[str, str]
    reason: Optional[ToastDismissReason]
    code: Optional[int]
    cleared: bool


class ToastElement(ToastBase):
    _registry : Set[Type["ToastElement"]] = set()
    _etype : _ToastElementType
    _euri : Sequence[str]
    _ename : _ToastXMLTag

    def __init_subclass__(cls, tag : _ToastXMLTag, slot : _ToastElementType, uri_keys : Sequence[str] = (), **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._etype = slot
        cls._euri = uri_keys
        cls._ename = tag
        cls._registry.add(cls)

    @classmethod
    def _xmltag(cls):
        return cls._ename.value

    @classmethod
    def _create_from_type(cls, _type : str, **kwargs) -> "ToastElement":
        for r in cls._registry:
            if r._ename.value == _type:
                return r.from_json(kwargs)
        raise ValueError(
            f"Element couldn't found with name \"{_type}\"."
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"