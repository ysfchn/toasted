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
    "ToastDuration",
    "ToastDismissReason",
    "ToastScenario",
    "ToastImagePlacement",
    "ToastSound",
    "ToastTextStyle",
    "ToastTextAlign",
    "ToastButtonStyle",
    "ToastUpdateResult",
    "ToastNotificationSetting"
]

from enum import Enum
from typing import NamedTuple, Tuple, Union

# --------------------
# Internal
# --------------------

class _ToastElementType(Enum):
    VISUAL = 1
    ACTION = 2
    HEADER = 3

class _ToastXMLTag(Enum):
    TEXT = "text"
    IMAGE = "image"
    PROGRESS = "progress"
    ACTION = "action"
    HEADER = "header"
    INPUT = "input"

class _ToastMediaProps(NamedTuple):
    attribute: str
    icon_size: int
    icon_padding: Union[int, Tuple[int, int]]
    is_sprite: bool = False


# --------------------
# API
# --------------------

# https://learn.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-toast#attributes
class ToastDuration(Enum):
    LONG = "long"
    SHORT = "short"


# https://learn.microsoft.com/en-us/uwp/api/windows.ui.notifications.toastdismissalreason?view=winrt-22621#fields
class ToastDismissReason(Enum):
    TIMED_OUT = 2
    USER_CANCELED = 0
    APPLICATION_HIDDEN = 1


# https://learn.microsoft.com/en-us/uwp/api/windows.ui.notifications.notificationupdateresult?view=winrt-26100
class ToastUpdateResult(Enum):
    SUCCEEDED = 0
    FAILED = 1
    NOTIFICATION_NOT_FOUND = 2


# https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-schema#toastscenario
class ToastScenario(Enum):
    REMINDER = "reminder"
    ALARM = "alarm"
    INCOMING_CALL = "incomingCall"
    URGENT = "urgent"


# https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-image#attributes
class ToastImagePlacement(Enum):
    LOGO = "appLogoOverride"
    HERO = "hero"


# https://learn.microsoft.com/en-us/uwp/api/windows.ui.notifications.toastnotificationmode?view=winrt-22621#fields
class ToastNotificationMode(Enum):
    UNRESTRICTED = 0
    PRIORITY_ONLY = 1
    ALARMS_ONLY = 2
    FEATURE_NOT_AVAILABLE = 3


# https://learn.microsoft.com/en-us/uwp/api/windows.ui.notifications.notificationsetting?view=winrt-26100
class ToastNotificationSetting(Enum):
    ENABLED = 0
    DISABLED_FOR_APPLICATION = 1
    DISABLED_FOR_USER = 2
    DISABLED_BY_GROUPPOLICY = 3
    DISABLED_BY_MANIFEST = 4


# https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-audio#attributes
class ToastSound(str, Enum):
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

    def __str__(self):
        return str(self.value)


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