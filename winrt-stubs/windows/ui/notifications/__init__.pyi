from datetime import datetime
from typing import Callable, Dict, List, Optional, overload
from winrt.system import Object
from winrt.windows.data.xml.dom import XmlDocument
from winrt.windows.foundation import EventRegistrationToken

class NotificationMode:
    value: int

class NotificationSetting:
    value: int

class ToastNotificationManagerForUser:
    history: ToastNotificationHistory
    notification_mode: NotificationMode

class ToastNotificationManager:
    @classmethod
    def get_default(cls) -> ToastNotificationManagerForUser: ...
    @classmethod
    def create_toast_notifier(cls, app_id: str, /) -> ToastNotifier: ...

class ToastActivatedEventArgs:
    arguments: str
    user_input: Dict[str, str]

    @classmethod
    def _from(cls, value: Object, /) -> ToastActivatedEventArgs: ...

class _ToastDismissalReason:
    value: int

class ToastDismissedEventArgs:
    reason: _ToastDismissalReason

class _Exception:
    value: int

class ToastFailedEventArgs:
    error_code: _Exception

class NotificationData:
    values: Dict[str, str]

class ToastNotificationHistory:
    def get_history(self, app_id: str, /) -> List[ToastNotification]: ...

class ToastNotification:
    data: NotificationData
    group: str
    tag: str
    suppress_popup: bool
    expiration_time: Optional[datetime]

    def __init__(self, xml: XmlDocument) -> None: ...
    def add_activated(self, listener: Callable, /) -> EventRegistrationToken: ...
    def add_dismissed(self, listener: Callable, /) -> EventRegistrationToken: ...
    def add_failed(self, listener: Callable, /) -> EventRegistrationToken: ...
    def remove_activated(self, token: EventRegistrationToken, /): ...
    def remove_dismissed(self, token: EventRegistrationToken, /): ...
    def remove_failed(self, token: EventRegistrationToken, /): ...

class ToastNotifier:
    setting: NotificationSetting
    def show(self, toast: ToastNotification, /): ...
    def hide(self, toast: ToastNotification, /): ...
    @overload
    def update(self, data: NotificationData, toast_id: str, group_id: str, /): ...
    @overload
    def update(self, data: NotificationData, toast_id: str, /): ...