__all__ = [
    "xml",
    "get_enum",
    "ToastResult"
]

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Generic, Optional, Any, Tuple, Type, List, Iterable, TypeVar
from toasted.enums import ToastElementType

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
        attr += " " + k.replace("_", "-") + "=\"" + value + "\""
    return "<" + element + attr + ">" + (_data or "") + "</" + element + ">"


def get_enum(enum : Type[Enum], value : Any, default : Any = None) -> Optional[Enum]:
    return next((y for x, y in enum._member_map_.items() if y.value == value or y == value or x == value), default)


class ToastBase(ABC):
    @abstractmethod
    def to_xml(self) -> str:
        ...

    def _list_remote_images(self) -> Optional[List[Tuple[str, str]]]:
        return
    
    @classmethod
    def from_json(cls, data : Dict[str, Any]):
        return cls(**data)


class ToastResult:
    def __init__(
        self,
        arguments : str,
        inputs : dict,
        show_data : dict,
        dismiss_reason : int
    ) -> None:
        self.arguments = arguments
        self.inputs = inputs
        self.show_data = show_data
        self.dismiss_reason = dismiss_reason

    @property
    def is_dismissed(self):
        return self.dismiss_reason != -1

    def __bool__(self):
        return self.is_dismissed


class ToastElement(ToastBase):
    ELEMENT_TYPE : ToastElementType


class ToastGenericContainer(Generic[T], ToastBase):
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