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

import asyncio
from datetime import datetime
from enum import Enum
import winreg
from inspect import isawaitable, iscoroutinefunction
from toasted.enums import _ToastElementType, ToastDismissReason, _ToastXMLTag, _ToastMediaProps

from abc import ABC, abstractmethod
from typing import (
    Dict,
    Generator,
    NamedTuple,
    Any,
    Optional,
    Set, 
    Tuple, 
    Type, 
    List,
    Union,
    Literal
)
from os import environ
import sys
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from pathlib import Path
from base64 import b64decode
from io import BytesIO
from xml.etree import ElementTree as ET

from PIL import Image, ImageFont, ImageDraw


class ToastPartial(NamedTuple):
    expiration_time: Optional[datetime]
    group_id: Optional[str]
    toast_id: Optional[str]
    params: Dict[str, str]


class ToastThemeInfo(NamedTuple):
    has_high_contrast: bool
    language_code: str
    color_dark: Tuple[int, int, int]
    color_light: Tuple[int, int, int]
    color_accent: Tuple[int, int, int]

    @property
    def is_dark(self):
        return sum(self.color_dark) == 0

    @property
    def is_accent_dark(self):
        r, g, b = self.color_accent
        return ((r * .2126) + (g * .7152) + (b * .0722)) >= 0.5
    
    def to_query(self, extended: bool = False) -> Dict[str, str]:
        """
        Returns theme information formatted as Microsoft query parameters to be added on image URLs.
        If `extended` is True, also includes extra non-MS parameters (prefixed with `ti-`) which is non-standard.
        """
        # Not sure where to find the up-to-date information about the query parameters that being added
        # by Windows to image URLs, but Microsoft briefly mentions query parameters here, so we replicate it.
        # https://learn.microsoft.com/en-us/windows/uwp/launch-resume/tile-toast-language-scale-contrast#hosting-and-loading-images-in-the-cloud
        # 
        # See also:
        # https://github.com/microsoft/AdaptiveCards/issues/1648
        params = {}

        params["ms-contrast"] = "high" if self.has_high_contrast else "standard"

        # It seems the language code is always lowercase, so we convert Windows language code into that.
        params["ms-lang"] = self.language_code.lower().replace("_", "-")

        params["ms-theme"] = "dark" if sum(self.color_dark) == 0 else "light"

        # Resolution scale (DPI) can have these enum values linked below, but I couldn't manage to get the scale
        # programmatically in Python (as a non-UWP app), so we leave it as 100 right now.
        # https://learn.microsoft.com/en-us/uwp/api/windows.graphics.display.resolutionscale?view=winrt-26100
        params["ms-scale"] = "100"

        if extended:
            params["ti-accent"] = rgb_to_hex(self.color_accent)
            params["ti-light"] = rgb_to_hex(self.color_light)
            params["ti-dark"] = rgb_to_hex(self.color_dark)

        return params


class URIResultType(Enum):
    LOCAL = "local"
    REMOTE = "remote"
    INLINE = "hex"
    RESOURCE = "resource"
    ICON = "icon"


class URIResultIcon(NamedTuple):
    charcode: int
    font_file: Optional[Union[str, Literal["mdl2", "fluent"]]] = None
    foreground: Optional[str] = None
    background: Optional[str] = None
    padding: Optional[int] = None
    size: Optional[int] = None
    
    def to_value(self):
        output = {}
        for k, v in self._asdict().items():
            if v is not None:
                output[k] = v
        return urlencode(output)
    
    @staticmethod
    def from_value(value: str):
        output = {}
        for k, v in dict(parse_qsl(value, keep_blank_values = True)).items():
            if v is not None:
                output[k] = str(v) if not v.isnumeric() else int(v)
        return URIResultIcon(**output)


class URIResult(NamedTuple):
    value: str
    type: URIResultType


def resolve_uri(
    uri: str,
    theme_info: Optional[ToastThemeInfo]
) -> URIResult:
    """
    Resolve a local file path or an URI locating a file or remote source.
    """
    split = urlsplit(uri, scheme = "file", allow_fragments = True)

    # See here for all file path formats on Windows:
    # https://learn.microsoft.com/en-us/dotnet/standard/io/file-path-formats
    # UNC and DOS paths are not supported.

    # A local path
    if split.scheme == "file":
        # Parsing "file://C:/Users" makes netloc to have "C:", but adding another forward slash
        # into "file://" scheme (like "file:///C:/Users") breaks the splitting, since netloc would become empty.
        # So, we manually remove the slash to make 3 slashes behave same with 2 slashes if there is no netloc.
        path = Path(split.netloc + split.path if split.netloc else split.netloc + split.path.removeprefix("/"))
        return URIResult(
            value = str(path.resolve().absolute()),
            type = URIResultType.LOCAL
        )

    # Drive letters as a scheme, should also work on mixed slashes due to URL normalization above.
    # e.g. "C:\Users\ysfchn\Desktop"
    elif (len(split.scheme) == 1) and (ord(split.scheme) in range(97, 123)):
        return URIResult(
            value = str(Path(f"{split.scheme}:{split.path}").resolve().absolute()),
            type = URIResultType.LOCAL
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
            type = URIResultType.LOCAL
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
            type = URIResultType.LOCAL
        )

    # "ms-winsoundevent" scheme is used for default toast notification sound enum,
    # so we just return it as-is.
    # e.g. "ms-winsoundevent:Notification.SMS"

    elif split.scheme == "ms-winsoundevent":
        return URIResult(
            value = f"ms-winsoundevent:{split.path}",
            type = URIResultType.RESOURCE
        )

    # If scheme is "http" or "https", left as-is.
    elif (split.scheme == "http") or (split.scheme == "https"):
        return URIResult(
            value = urlunsplit(split),
            type = URIResultType.REMOTE
        )

    # Allow returning arbitrary bytes if scheme is "data" to avoid needing to have an actual
    # file on filesystem. Should be only used for small files though.
    # e.g. "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ=="
    elif split.scheme == "data":
        data_uri = split.path.removeprefix("/")

        if data_uri.count(";base64,") == 1:
            return URIResult(
                value = b64decode(data_uri.split(";base64,")[-1]).hex(),
                type = URIResultType.INLINE
            )

        raise ValueError(f"Invalid base64 data URI: '{uri}'")

    # Pick an icon from system.
    elif split.scheme == "icon":
        hex_value = (split.netloc or split.path).removeprefix("/").removeprefix("U+").removeprefix("0x")
        return URIResult(
            value = URIResultIcon.from_value(f"charcode={int(hex_value, 16)}&{split.query + split.fragment}").to_value(),
            type = URIResultType.ICON
        )

    raise ValueError(f"Invalid or unsupported URI: '{uri}'")


def rgb_to_hex(
    color: Union[Tuple[int, int, int], Tuple[int, int, int, int]]
):
    """
    Converts RGB tuple to a hexadecimal string.
    """
    value = 0
    for i, c in enumerate(color):
        value += max(0, min(c, 255)) << (len(color) - (i + 1)) * 8
    return value.to_bytes(len(color), "big").hex()


def hex_to_rgb(
    value: str
) -> Union[Tuple[int, int, int], Tuple[int, int, int, int]]:
    color = int.from_bytes(bytes.fromhex(value.removeprefix("#")), "big")
    result = []
    if len(value) == 8:
        result.append((color >> 24) & 0xFF)
    result.append((color >> 16) & 0xFF)
    result.append((color >> 8) & 0xFF)
    result.append(color & 0xFF)
    return tuple(result)


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
    charcode: int,
    font_file: Union[str, bytes],
    icon_size: int,
    icon_padding: Union[int, Tuple[int, int]],
    background: str,
    foreground: str,
    icon_format: str = "png"
) -> bytes:
    """
    Create a image with a character from given icon font file 
    and return the created image in given format as bytes.

    Used to extract system icons from built-in Windows icon fonts
    such as "Segoe MDL2 Assets".

    https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-ui-symbol-font
    """
    v_padding, h_padding = (icon_padding, icon_padding) if type(icon_padding) is int else icon_padding # type: ignore
    image = Image.new("RGBA", (v_padding + icon_size, h_padding + icon_size), hex_to_rgb(background)) # type: ignore
    draw = ImageDraw.Draw(image)
    if not font_file:
        raise ValueError("No font has provided!")
    asset_font = ImageFont.truetype(
        font_file,
        size = icon_size, 
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
        xy = ((v_padding + icon_size) // 2, (h_padding + icon_size) // 2),
        text = text_content,
        fill = hex_to_rgb(foreground),
        font = asset_font,
        align = "center",
        anchor = "mm",
        spacing = 0
    )
    buffer = BytesIO()
    image.save(buffer, icon_format)
    return buffer.getvalue()


def wrap_callback(caller):
    if caller is None:
        return None
    async def wrapped(*args):
        if iscoroutinefunction(caller):
            await caller(*args)
            return
        result = await asyncio.to_thread(caller, *args)
        if isawaitable(result):
            await result
    return wrapped


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


def get_icon_font_default(font_type: Optional[Literal["fluent", "mdl2"]] = None) -> Optional[Path]:
    """
    Returns the path of recommended icon font
    to be used in toast icons.
    """
    fonts = dict(get_icon_fonts_path())
    # Windows 11 comes with fluent icons by default.
    if get_windows_build() >= 22000:
        if "fluent" in fonts:
            if (not font_type) or (font_type == "fluent"):
                return fonts["fluent"]
    # For Windows 10, prefer MDL2 instead.
    if "mdl2" in fonts:
        if (not font_type) or (font_type == "mdl2"):
            return fonts["mdl2"]


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

    def _update(self, context: "_ToastContextState"):
        self._provided = True
        self._dismiss_reason = context.reason
        self._arguments = context.arguments
        self._params = context.params
        self._inputs = context.inputs
        self._cleared = context.cleared

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
            "{}" if not self._params else dict(((k, v) for k, v in self._params.items() if k != "__sentinel__")),
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
    _ename : _ToastXMLTag

    def __init_subclass__(cls, tag : _ToastXMLTag, slot : _ToastElementType, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._etype = slot
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

    def _uri_holder(self) -> Generator[_ToastMediaProps, None, None]:
        yield from []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"