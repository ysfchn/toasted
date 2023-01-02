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
    "xml",
    "get_enum",
    "resolve_value",
    "get_windows_version",
    "ToastResult"
]

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Generic, Optional, Any, Tuple, Type, List, Iterable, TypeVar, Union
from toasted.enums import ToastElementType, ToastDismissReason
import platform

T = TypeVar('T')

def xml(element : str, _data : Optional[str] = None, **kwargs) -> str:
    attr = ""
    for k, v in kwargs.items():
        value = ""
        if v == None:
            continue
        if type(v) == bool:
            value = str(v).lower()
        elif isinstance(v, Enum):
            value = str(v.value)
        else:
            value = str(v)
        attr += " " + k.replace("_", "-") + "=\"" + value.replace("\"", "&quot;") + "\""
    return "<" + element + attr + ">" + (_data or "") + "</" + element + ">"


def get_enum(enum : Type[Enum], value : Any, default : T = None) -> Union[Enum, T]:
    return next((y for x, y in enum._member_map_.items() if (y.value == value) or (y == value) or (x == value)), default)


def resolve_value(val : str, is_media : bool = False) -> Tuple[Optional[str], str, Optional[str]]:
    # Binding values
    if str(val).startswith("{") and str(val).startswith("}"):
        return "BINDING", val, str(val)[1:-1],
    elif is_media:
        # Remote
        if str(val).startswith("http://") or str(val).startswith("https://"):
            return "REMOTE", val, None,
        # Local
        return "LOCAL", val, \
            str(val).removeprefix("ms-appx://") \
            .removeprefix("ms-appdata://") \
            .removeprefix("/"),
    return None, val, None,


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


class ToastBase(ABC):
    __slots__ = ()

    @abstractmethod
    def to_xml(self) -> str:
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


class ToastElement(ToastBase):
    _registry : List[Tuple[str, "ToastElement"]] = []
    _etype : ToastElementType
    _esources : Optional[Dict[str, Any]]

    def __init_subclass__(cls, ename : str, etype : ToastElementType, esources : Optional[Dict[str, Any]] = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._etype = etype
        cls._esources = esources
        cls._registry.append((ename, cls, ))

    @classmethod
    def _create_from_type(cls, _type : str, **kwargs) -> "ToastElement":
        for x, y in cls._registry:
            if x == _type:
                return y.from_json(kwargs)
        raise ValueError(
            "Subgroups can't be created from root level, use \"group\" with children instead." \
            if _type == "subgroup" else f"Element couldn't found with name \"{_type}\"."
        )

    def _resolve(self) -> List[Tuple[str, str, str, str]]:
        # Toast elements produce a XML, however the output XML attribute names are not same
        # with the class __init__ parameter names, so there is an "esources" class parameter for elements
        # in their definitions. We need to do that to support HTTP images, because when source is 
        # an HTTP image, we are replacing the output XML to point to the downloaded file.
        #
        # class Image(ToastElement, esources = {"source": "src"}):
        #     ...
        #
        # "source" is attribute name, "src" is name of the attribute in output XML
        x = []
        if self._esources:
            for k, v in self._esources.items():
                c_type, c_old, c_new = resolve_value(getattr(self, k), is_media = True)
                x.append((c_type, v or k, c_old, c_old or c_new))
        return x

    def __repr__(self) -> str:
        return f"<{self.__class__}>"


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

    def __iter__(self) -> T:
        return iter(self.data)


class ToastElementContainer(ToastGenericContainer[ToastElement]):
    pass