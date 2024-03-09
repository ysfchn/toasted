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
    "resolve_uri",
    "xml",
    "get_enum",
    "get_windows_version",
    "ToastResult"
]

from toasted.enums import ToastElementType, ToastDismissReason

from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Dict,
    NamedTuple, 
    Optional, 
    Any, 
    Tuple, 
    Type, 
    List, 
    TypeVar, 
    Union,
    Literal
)
from os import environ, sep
import platform
import sys
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from base64 import b64decode
import winreg
import string
from io import BytesIO

from winsdk.windows.storage import SystemDataPaths
from PIL import Image, ImageFont, ImageDraw


T = TypeVar('T')


class ToastThemeInfo(NamedTuple):
    contrast : Literal["high", "standard"]
    lang : str
    theme : Literal["dark", "light"]


def resolve_uri(
    uri : str,
    allow_remote : bool = False
) -> Union[str, Path, bytes]:
    """
    Resolve an file system or remote URI, similar how it is done in UWP apps.
    """
    split = urlsplit(uri, allow_fragments = False)
    path_part = (split.netloc + split.path).removeprefix("/")
    # If scheme is "ms-appx", path is relative to current working directory.
    if split.scheme == "ms-appx":
        return Path().cwd() / path_part
    # If scheme is "file", path is relative to system root.
    elif split.scheme == "file":
        return Path(sep).absolute() / path_part
    # If scheme is "data", return bytes.
    elif split.scheme == "data":
        meta, data = path_part.split(",", 1)
        _, data_type = ";" if ";" not in meta else meta.split(";", 1)
        if data_type != "base64":
            raise ValueError(
                "Data URI must be in 'base64' type: \"{0}\"".format(uri)
            )
        return b64decode(data)
    # If scheme is "icon", extract icon from Windows icon font.
    elif split.scheme == "icon":
        hex_value = path_part.removeprefix("U+").removeprefix("0x")
        hex_digits = set(string.hexdigits)
        if not all(c in hex_digits for c in hex_value):
            raise ValueError(
                "Icon URI path needs to be a hexadecimal " +
                "value of character point: \"{0}\"".format(uri)    
            )
        return get_icon_from_font(
            charcode = int(hex_value, 16),
            font_file = get_icon_font_default(),
            in_white = False
        )
    # If scheme is "http" or "https", left as-is.
    elif allow_remote and (split.scheme in ["https", "http"]):
        return urlunsplit(split)
    # If scheme is "ms-appdata", path is relative to appdata which is based
    # on the first part of the path ("local", "roaming" or "temp").
    elif split.scheme == "ms-appdata":
        if path_part.startswith("local/"):
            return (
                Path(environ["LOCALAPPDATA"]).resolve() / 
                path_part.removeprefix("local/")
            )
        elif path_part.startswith("roaming/"):
            return (
                Path(environ["APPDATA"]).resolve() / "Roaming" /
                path_part.removeprefix("roaming/")
            )
        elif path_part.startswith("temp/"):
            return (
                Path(environ["LOCALAPPDATA"]).resolve() / "Temp" /
                path_part.removeprefix("temp/")
            )
    raise ValueError(
        "Unknown or invalid URI: \"{0}\"".format(uri)
    )


def is_in_venv() -> bool:
    """
    Returns True if Python is launched in a virtualenv or similar environments.
    Otherwise, False.
    """
    return bool(
        environ.get("CONDA_PREFIX", None) or \
        environ.get("VIRTUAL_ENV", None) or \
        getattr(sys, "real_prefix", sys.base_prefix) != sys.prefix
    )


def get_theme_query_parameters(
    info : ToastThemeInfo
) -> Dict[str, str]:
    """
    Convert ToastThemeInfo object to query parameters.
    """
    return {
        "ms-contrast": info.contrast,
        "ms-lang": info.lang,
        "ms-theme": info.theme
    }


def xmldata_to_content(
    content : Union[None, str, List["XMLData"], "XMLData"]
):
    if not content:
        yield None
    elif isinstance(content, list):
        for i in content:
            for j in xmldata_to_content(i):
                yield j
    elif isinstance(content, XMLData):
        yield "<{0}{1}>".format(content.tag, attrs_to_string(content.attrs or {}))
        for i in xmldata_to_content(content.content):
            yield i
        yield "</{0}>".format(content.tag)
    else:
        yield content


def attrs_to_string(
    attrs : Dict[str, Any]
) -> str:
    attr = ""
    for k, v in attrs.items():
        value = ""
        if v is None:
            continue
        if isinstance(v, bool):
            value = str(v).lower()
        elif isinstance(v, Enum):
            value = str(v.value)
        else:
            value = str(v)
        attr += " " + k.replace("_", "-") + "=\"" + value.replace("\"", "&quot;") + "\""
    return attr


def xml(element : str, _data : Optional[str] = None, **kwargs) -> str:
    return \
        "<" + element + attrs_to_string(kwargs) + ">" + \
        (_data or "") + \
        "</" + element + ">"


def get_enum(enum : Type[Enum], value : Any, default : T = None) -> Union[Enum, T]:
    return next(
        (y for x, y in enum._member_map_.items() if (y.value == value) 
        or (y == value) or (x == value)), default
    )


def get_windows_version() -> Tuple[float, int]:
    ver = platform.version()
    if not ver.replace(".", "").isnumeric():
        raise ValueError(f"Invalid Windows version: {ver}")
    rel, bul = ver.rsplit(".", 1)
    rel = float(rel)
    bul = int(bul)
    # If build is above 20000, then we are in Windows 11.
    if bul > 20000:
        rel += 1.0
    return rel, bul,


def get_icon_from_font(
    charcode : int,
    font_file : Union[str, bytes],
    icon_size : int = 64,
    in_white : bool = True,
    icon_format : str = "png"
) -> bytes:
    """
    Create a transparent image with a character in black color
    (or white, if "in_white" is True) from given icon font file 
    and return the created image in given format as bytes.

    Used to extract system icons from built-in Windows icon fonts
    such as "Segoe MDL2 Assets".

    https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-ui-symbol-font
    """
    image = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
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
        xy = (icon_size // 2, icon_size // 2), text = text_content,
        fill = (255, 255, 255, 255) if in_white else (0, 0, 0, 255),
        font = asset_font, align = "center", anchor = "mm", spacing = 0
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
    user_fonts = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, 
        "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"
    )
    system_fonts_path = Path(SystemDataPaths.get_default().fonts)
    # Check for system fonts.
    system_fonts_count = winreg.QueryInfoKey(system_fonts)[1]
    for i in range(system_fonts_count):
        name, file, _ = winreg.EnumValue(system_fonts, i)
        for k, v in fonts.items():
            if name == v:
                font_path = Path(file)
                if not font_path.is_absolute():
                    font_path = system_fonts_path.joinpath(font_path)
                available.append((k, font_path))
    system_fonts.Close()
    # Check for user fonts.
    user_fonts_count = winreg.QueryInfoKey(user_fonts)[1]
    for i in range(user_fonts_count):
        name, file, _ = winreg.EnumValue(user_fonts, i)
        for k, v in fonts.items():
            if name == v:
                available.append((k, Path(file)))
    return available


def get_windows_build() -> int:
    """
    Gets Windows build number.
    """
    return sys.getwindowsversion().build


def get_icon_font_default() -> Path:
    """
    Returns the path of recommended icon font
    to be used in toast icons.
    """
    fonts = dict(get_icon_fonts_path())
    # Windows 11 comes with fluent icons by default.
    # https://en.wikipedia.org/wiki/List_of_Microsoft_Windows_versions
    if get_windows_build() >= 22000:
        if "fluent" in fonts:
            return fonts["fluent"]
    # For Windows 10, prefer MDL2 instead.
    if "mdl2" in fonts:
        return fonts["mdl2"]
    raise ValueError("Couldn't find an available icon font.")


class XMLData(NamedTuple):
    tag : str
    content : Union[None, str, List["XMLData"], "XMLData"] = None
    attrs : Optional[Dict[str, Any]] = None
    source_replace : Optional[str] = None


class ToastPayload(NamedTuple):
    uses_custom_style : Optional[bool]
    custom_sound_file : str
    base_path : str
    arguments : Optional[str]
    duration : Optional[str]
    scenario : Optional[str]
    timestamp : Optional[str]
    visual_xml : str
    actions_xml : str
    other_xml : str



class BindingKey(str):
    def __new__(cls, value : str):
        if value:
            if not isinstance(value, str):
                raise TypeError(f"Unexpected type for binding key: {type(value)}")
            if value.startswith("{") and value.endswith("}"):
                pass
            else:
                raise ValueError(
                    "Binding key values must start with '{' and end with '}'"
                )
        return super().__new__(cls, value)


class ToastBase(ABC):
    __slots__ = ()

    @abstractmethod
    def to_xml_data(self) -> XMLData:
        ...
    
    @classmethod
    def from_json(cls, data : Dict[str, Any]):
        return cls(**data)


class ToastResult:
    def __init__(
        self,
        arguments : str,
        inputs : dict,
        show_data : dict,
        dismiss_reason : ToastDismissReason
    ) -> None:
        self.arguments = arguments
        self.inputs = inputs
        self.show_data = show_data
        self.dismiss_reason = dismiss_reason

    @property
    def is_dismissed(self):
        return self.dismiss_reason != ToastDismissReason.NOT_DISMISSED

    def __bool__(self):
        return self.is_dismissed

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} arguments="{self.arguments}" '
            f'inputs="{self.inputs}" reason={self.dismiss_reason}>'
        )


class ToastElement(ToastBase):
    _registry : List[Tuple[str, "ToastElement"]] = []
    _etype : ToastElementType

    def __init_subclass__(cls, ename : str, etype : ToastElementType, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._etype = etype
        cls._registry.append((ename, cls, ))

    @classmethod
    def _create_from_type(cls, _type : str, **kwargs) -> "ToastElement":
        for x, y in cls._registry:
            if x == _type:
                return y.from_json(kwargs)
        raise ValueError(
            f"Element couldn't found with name \"{_type}\"."
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


"""
TODO: Remove me

class ToastGenericContainer(Generic[T], ToastBase):
    __slots__ = ("data", )

    def __init__(self) -> None:
        self.data : List[T] = []

    def append(self, element : T) -> None:
        self.data.append(element)

    def remove(self, element : T) -> None:
        self.data.remove(element)

    def pop(self, index : int = -1) -> T:
        return self.data.pop(index)

    def clear(self) -> None:
        return self.data.clear()

    def insert(self, index : int, element : T) -> None:
        self.data.insert(index, element)

    def extend(self, other : Iterable[T]):
        self.data.extend(other)

    def __len__(self) -> int:
        return len(self.data)

    def __iadd__(self, other : T):
        self.append(other)
        return self

    def __imul__(self, other : T):
        self.remove(other)
        return self

    def __iter__(self) -> T:
        return iter(self.data)


class ToastElementContainer(ToastGenericContainer[ToastElement]):
    pass
"""