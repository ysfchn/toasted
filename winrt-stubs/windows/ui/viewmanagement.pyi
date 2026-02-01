from enum import Enum

class AccessibilitySettings:
    high_contrast: bool

class UIColorType(Enum):
    BACKGROUND = ...
    ACCENT = ...
    FOREGROUND = ...

class Color:
    r: int
    g: int
    b: int

class UISettings:
    def get_color_value(self, color_type: UIColorType, /) -> Color: ...