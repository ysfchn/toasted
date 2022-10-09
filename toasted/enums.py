__all__ = [
    "ToastDuration",
    "ToastScenario",
    "ToastElementType",
    "ToastImagePlacement",
    "ToastSound",
    "ToastTextStyle",
    "ToastTextAlign",
    "ToastButtonStyle"
]

from enum import Enum

class ToastDuration(Enum):
    LONG = "long"
    SHORT = "short"


# https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-schema#toastscenario
class ToastScenario(Enum):
    REMINDER = "reminder"
    ALARM = "alarm"
    INCOMING_CALL = "incomingCall"
    URGENT = "urgent"


class ToastElementType(Enum):
    VISUAL = 1
    ACTION = 2
    HEADER = 3


# https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-image#attributes
class ToastImagePlacement(Enum):
    LOGO = "appLogoOverride"
    HERO = "hero"


class ToastNotificationMode(Enum):
    UNRESTRICTED = 0
    PRIORITY_ONLY = 1
    ALARMS_ONLY = 2


# https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-audio#attributes
class ToastSound:
    DEFAULT  = "ms-winsoundevent:Notification.Default"
    IM       = "ms-winsoundevent:Notification.IM"
    MAIL     = "ms-winsoundevent:Notification.Mail"
    REMINDER = "ms-winsoundevent:Notification.Reminder"
    SMS      = "ms-winsoundevent:Notification.SMS"
    ALARM1   = "ms-winsoundevent:Notification.Looping.Alarm"
    ALARM2   = "ms-winsoundevent:Notification.Looping.Alarm2"
    ALARM3   = "ms-winsoundevent:Notification.Looping.Alarm3"
    ALARM4   = "ms-winsoundevent:Notification.Looping.Alarm4"
    ALARM5   = "ms-winsoundevent:Notification.Looping.Alarm5"
    ALARM6   = "ms-winsoundevent:Notification.Looping.Alarm6"
    ALARM7   = "ms-winsoundevent:Notification.Looping.Alarm7"
    ALARM8   = "ms-winsoundevent:Notification.Looping.Alarm8"
    ALARM9   = "ms-winsoundevent:Notification.Looping.Alarm9"
    ALARM10  = "ms-winsoundevent:Notification.Looping.Alarm10"
    CALL1    = "ms-winsoundevent:Notification.Looping.Call"
    CALL2    = "ms-winsoundevent:Notification.Looping.Call2"
    CALL3    = "ms-winsoundevent:Notification.Looping.Call3"
    CALL4    = "ms-winsoundevent:Notification.Looping.Call4"
    CALL5    = "ms-winsoundevent:Notification.Looping.Call5"
    CALL6    = "ms-winsoundevent:Notification.Looping.Call6"
    CALL7    = "ms-winsoundevent:Notification.Looping.Call7"
    CALL8    = "ms-winsoundevent:Notification.Looping.Call8"
    CALL9    = "ms-winsoundevent:Notification.Looping.Call9"
    CALL10   = "ms-winsoundevent:Notification.Looping.Call10"


# https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-schema#adaptivetextstyle
class ToastTextStyle(Enum):
    DEFAULT = "default"
    CAPTION = "caption"
    CAPTIONSUBTLE = "captionSubtle"
    BODY = "body"
    BODYSUBTLE = "bodySubtle"
    BASE = "base"
    BASESUBTLE = "baseSubtle"
    SUBTITLE = "subtitle"
    SUBTITLESUBTLE = "subtitleSubtle"
    TITLE = "title"
    TITLESUBTLE = "titleSubtle"
    TITLENUMERAL = "titleNumeral"
    SUBHEADER = "subHeader"
    SUBHEADERSUBTLE = "subheaderSubtle"
    SUBHEADERNUMERAL = "subheaderNumberal"
    HEADER = "header"
    HEADERSUBTLE = "headerSubtle"
    HEADERNUMERAL = "headerNumeral"


# https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-schema#adaptivetextalign
class ToastTextAlign(Enum):
    AUTO = "auto"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


# https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-action#attributes
class ToastButtonStyle(Enum):
    SUCCESS = "Success"
    CRITICAL = "Critical"