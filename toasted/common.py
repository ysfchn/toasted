__all__ = [
    "xml",
    "get_enum"
]

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional, Any, Type, List, Iterable
from toasted.enums import ToastElementType


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
        attr += " " + k.replace("_", "-") + "=\"" + value + "\""
    return "<" + element + attr + ">" + (_data or "") + "</" + element + ">"


def get_enum(enum : Type[Enum], value : Any) -> Optional[Enum]:
    return next((y for x, y in enum._member_map_.items() if x == value or y.value == value or y == value), None)


class ToastBase(ABC):
    @abstractmethod
    def to_xml(self) -> str:
        ...
    
    @classmethod
    def from_json(cls, data : Dict[str, Any]):
        return cls(**data)


class ToastElement(ToastBase):
    ELEMENT_TYPE : ToastElementType


class ToastElementContainer(ToastBase):
    def __init__(self) -> None:
        self.data : List[ToastElement] = []

    def append(self, element : "ToastElement") -> None:
        self.data.append(element)

    def remove(self, element : "ToastElement") -> None:
        self.data.remove(element)

    def pop(self, index : int = -1) -> "ToastElement":
        return self.data.pop(index)

    def clear(self) -> None:
        return self.data.clear()

    def insert(self, index : int, element : "ToastElement") -> None:
        self.data.insert(index, element)

    def extend(self, other : Iterable["ToastElement"]):
        self.data.extend(other)

    def __len__(self) -> int:
        return len(self.data)

    def __iadd__(self, other : "ToastElement"):
        self.append(other)
        return self

    def __iter__(self) -> "ToastElement":
        return iter(self.data)