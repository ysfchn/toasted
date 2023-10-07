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
    Generic, 
    NamedTuple, 
    Optional, 
    Any, 
    Tuple, 
    Type, 
    List, 
    Iterable, 
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