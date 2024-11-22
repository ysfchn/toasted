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
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl
from pathlib import Path
from base64 import b64decode
import string
from io import BytesIO

from PIL import Image, ImageFont, ImageDraw, ImageColor

if sys.platform == "win32":
    import winreg
    from winrt.windows.storage import SystemDataPaths # pyright: ignore[reportMissingImports]
else:
    class Proxy:
        def __getattribute__(self, _): raise Exception("Toasted is not supported on non-Windows platforms.") # noqa: E501
    winreg = SystemDataPaths = Proxy()

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
    # https://learn.microsoft.com/en-us/windows/uwp/app-resources/uri-schemes
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
        values = dict(parse_qsl(split.query))
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
            foreground = ImageColor.getrgb(values.get("foreground", None) or "#000000FF"), # noqa: E501
            background = ImageColor.getrgb(values.get("background", None) or "#00000000"), # noqa: E501
            icon_padding = int(values.get("padding", None) or 0)
        )
    # If scheme is "http" or "https", left as-is.
    elif (split.scheme == "https") or (split.scheme == "http"):
        if not allow_remote:
            raise ValueError(
                "A remote URI has been provided while it is not allowed because " +
                "Toast.remote_media is True: \"{0}\"".format(uri)
            )
        return urlunsplit(split)
    # If scheme is "ms-appdata", path is relative to appdata which is based
    # on the first part of the path ("local", "roaming" or "temp").
    # https://learn.microsoft.com/en-us/windows/uwp/app-resources/uri-schemes#path-ms-appdata
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
        "Unsupported or invalid URI: \"{0}\"".format(uri)
    )


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


def get_icon_from_font(
    charcode : int,
    font_file : Union[str, bytes],
    icon_size : int = 64,
    icon_padding : int = 0,
    background : "Image._Color" = (0, 0, 0, 0),
    foreground : "Image._Color" = (255, 255, 255, 255),
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
    _registry : List[Tuple[str, Type["ToastElement"]]] = []
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