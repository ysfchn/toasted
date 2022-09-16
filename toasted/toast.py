__all__ = ["Toast"]

from toasted.common import ToastElementContainer, ToastElement, get_enum, xml
from toasted.enums import ToastDuration, ToastScenario, ToastSound, ToastElementType, ToastNotificationMode
from toasted.elements import Image, Button, _create_element
import asyncio
from ctypes import windll
from datetime import datetime
import sys
import locale
from tempfile import NamedTemporaryFile
import httpx
from typing import Any, Callable, Dict, List, Optional, Tuple
from winsdk.windows.ui.notifications import (
    ToastNotification, 
    ToastNotificationManager, 
    ToastActivatedEventArgs, 
    ToastDismissedEventArgs, 
    ToastFailedEventArgs,
    ToastNotifier,
    NotificationSetting,
    NotificationData,
    NotificationUpdateResult
)
from winsdk._winrt import Object
from winsdk.windows.foundation import IPropertyValue, EventRegistrationToken
from winsdk.windows.ui.viewmanagement import AccessibilitySettings, UISettings, UIColorType
import winsdk.windows.data.xml.dom as dom


class Toast(ToastElementContainer):
    """
    Represents a toast.
    https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/adaptive-interactive-toasts?tabs=builder-syntax

    Args:
        arguments:
            A string that is passed to the application when it is activated by the toast. 
            The format and contents of this string are defined by the app for its own use. 
            When the user taps or clicks the toast to launch its associated app, 
            the launch string provides the context to the app that allows it to show the user a 
            view relevant to the toast content, rather than launching in its default way.
        duration:
            The amount of time the toast should display.
        timestamp:
            Introduced in Creators Update: Overrides the default timestamp with a custom timestamp 
            representing when your notification content was actually delivered, 
            rather than the time the notification was received by the Windows platform.
        scenario:
            The scenario your toast is used for, like an alarm or reminder. 
            REMINDER: A reminder notification. This will be displayed pre-expanded and stay on the user's screen till dismissed.
            ALARM: An alarm notification. This will be displayed pre-expanded and stay on the user's screen till dismissed. 
                Audio will loop by default and will use alarm audio.
            INCOMING_CALL: An incoming call notification. This will be displayed pre-expanded in a special call format and 
                stay on the user's screen till dismissed. Audio will loop by default and will use ringtone audio.
            URGENT:  An important notification. This allows users to have more control over what apps can send them 
                high-priority toast notifications that can break through Focus Assist (Do not Disturb). 
                This can be modified in the notifications settings.
        use_button_style:
            Specifies whether styled buttons should be used. The styling of the button is determined by the
            "button_style" property on Button object.
        group_id:
            Group ID that this toast belongs in. Used for deleting a notification from Action Center.
        toast_id:
            ID of the toast. Used for deleting a notification from Action Center.
        show_popup:
            Gets or sets whether a toast's pop-up UI is displayed on the user's screen. If pop-up is not shown,
            the notification will be added to Action Center silently. Do not set this property to true in a toast 
            sent to a Windows 8.x device. Doing so will cause a dropped notification.
        base_path:
            Specify a base file path which is used when an image source is a relative path. For example, if base_path is
            "file:///C:\\Users\\ysfchn\\Desktop\\" and an Image element's source is "test.png", the resulting path will be 
            "file:///C:\\Users\\ysfchn\\Desktop\\test.png", defaults to "file:///". If specified, it must end with backslash (\\).
        sound:
            Specifies a sound to play when a toast notification is displayed. Set to None for mute the notification sound.
        sound_loop:
            Set to true if the sound should repeat as long as the toast is shown; 
            false to play only once. If this attribute is set to true, 
            the duration attribute in the toast element must also be set. 
            There are specific sounds provided to be used when looping. 
        remote_images:
            If True, makes https:// and http:// links functional on image sources by downloading the images in 
            temporary directory, then deletes them when toast has clicked or dismissed. 
        add_query_params:
            Set to True to append a query string to the image URI supplied 
            in the toast notification. Use this attribute if your server hosts images and can handle query strings, 
            either by retrieving an image variant based on the query strings or by ignoring the query string 
            and returning the image as specified without the query string. This query string specifies 
            contrast setting, language and theme; for instance, a value of:
            "https://example.com/images/foo.png" given in the notification becomes
            "https://example.com/images/foo.png?ms-contrast=standard&ms-lang=en-us&ms-theme=dark".
        expiration_time:
            In Windows 10, all toast notifications go in Action Center after they are dismissed or 
            ignored by the user, so users can look at your notification after the popup is gone.
            However, if the message in your notification is only relevant for a period of time, 
            you should set an expiration time on the toast notification so the users do not see stale information 
            from your app. For example, if a promotion is only valid for 12 hours, set the expiration time to 12 hours.
    """

    def __init__(
        self, 
        arguments : Optional[str] = None,
        duration : Optional[ToastDuration] = None, 
        timestamp : Optional[datetime] = None,
        scenario : Optional[ToastScenario] = None,
        use_button_style : bool = True,
        group_id : Optional[str] = None,
        toast_id : Optional[str] = None,
        show_popup : bool = True,
        base_path : Optional[str] = None,
        sound : Optional[ToastSound] = ToastSound.DEFAULT,
        sound_loop : bool = False,
        remote_images : bool = True,
        add_query_params : bool = False,
        expiration_time : Optional[datetime] = None
    ) -> None:
        super().__init__()
        self.duration = duration
        self.arguments = arguments
        self.scenario = scenario
        self.timestamp = timestamp
        self.use_button_style = use_button_style
        self.show_popup = show_popup
        self.base_path = base_path
        self.sound = sound
        self.sound_loop = sound_loop
        self.remote_images = remote_images
        self.add_query_params = add_query_params
        self.expiration_time = expiration_time
        self.group_id = group_id
        self.toast_id = toast_id
        self._toast_handler : Optional[Callable[[str, Optional[Dict[str, str]], int], None]] = None
        self._show_handler : Optional[Callable] = None
        self._manager : ToastNotifier = None
        self._toast : ToastNotification = None
        self._mute_sound_override : bool = False
        self._temp_files : List[Any] = []
        self._called_by_show : bool = False


    def __copy__(self) -> "Toast":
        x = Toast(
            duration = self.duration,
            arguments = self.arguments,
            scenario = self.scenario,
            use_button_style = self.use_button_style,
            toast_id = self.toast_id,
            group_id = self.group_id,
            show_popup = self.show_popup,
            timestamp = self.timestamp,
            base_path = self.base_path,
            sound = self.sound,
            sound_loop = self.sound_loop,
            remote_images = self.remote_images,
            add_query_params = self.add_query_params,
            expiration_time = self.expiration_time
        )
        x._mute_sound_override = self._mute_sound_override
        x._toast_handler = self._toast_handler
        x._show_handler = self._show_handler
        x.data = self.data
        return x

    
    @staticmethod
    def from_json(json : Dict[str, Any]) -> "Toast":
        toast = Toast(
            duration = get_enum(ToastDuration, json.get("duration", None)),
            arguments = json.get("arguments", None),
            scenario = get_enum(ToastScenario, json.get("scenario", None)),
            use_button_style = bool(json.get("use_button_style", True)),
            group_id = str(json.get("group_id", "")) or None,
            toast_id = str(json.get("toast_id", "")) or None,
            show_popup = bool(json.get("show_popup", True)),
            base_path = str(json.get("base_path", "")) or None,
            timestamp = None if "timestamp" not in json else datetime.fromisoformat(json["timestamp"]),
            sound = get_enum(ToastSound, json.get("sound", "DEFAULT")),
            sound_loop = bool(json.get("sound_loop", False)),
            remote_images = bool(json.get("remote_images", True)),
            add_query_params = bool(json.get("add_query_params", False)),
            expiration_time = None if "expiration_time" not in json else datetime.fromisoformat(json["expiration_time"])
        )
        for el in json["elements"]:
            toast.append(_create_element(el))
        return toast


    def handler(self, function : Optional[Callable[[str, Dict[str, str], int], None]] = None):
        """
        A decorator that calls the function when user has clicked or dismissed the toast.

        Passed positional parameters to function:
            arguments:
                If the toast itself has clicked, the "arguments" will be this toast's arguments, 
                if a button has clicked, then the "arguments" will be the button's own "arguments" value.
                This is used for tracking which button has clicked. If toast has dismissed, this will be
                a blank string.
            user_input:
                A dictionary of inputs mapped with input IDs and input values.
            dismiss_reason:
                The reason of why toast has dismissed.
                NOT_DISMISSED = -1
                USER_CANCELED = 0
                APPLICATION_HIDDEN = 1
                TIMED_OUT = 2
        """
        if function:
            self._toast_handler = function
            return function
        else:
            def decorator(func : Callable):
                self._toast_handler = func
                return func
            return decorator


    def shown(self, function : Optional[Callable] = None):
        """
        A decorator that calls the function when toast has shown with show().

        Passed positional parameters to function:
            data:
                The notification data passed to show().
        """
        if function:
            self._show_handler = function
            return function
        else:
            def decorator(func : Callable):
                self._show_handler = func
                return func
            return decorator


    def copy(self) -> "Toast":
        return self.__copy__()


    def to_xml(self) -> str:
        self._cleanup_images()
        visual = ""
        actions = ""
        other = ""
        for element in self.data:
            replace_source = None
            if not isinstance(element, ToastElement):
                raise ValueError("Element must be a type of ToastElement:", element)
            if element.ELEMENT_TYPE == ToastElementType.VISUAL:
                # If remote images are enabled, and to_xml() called by show(), cache online images.
                if self.remote_images and self._called_by_show:
                    if element.__class__ == Image:
                        if element.source.startswith("http"):
                            replace_source = self._download_image(element.source, self.add_query_params) or ""
                el = element.to_xml()
                # Replace with temp file path without modifying the original element.
                if replace_source:
                    el = el.replace("src=\"" + element.source + "\"", "src=\"" + replace_source + "\"")
                visual += el
            elif element.ELEMENT_TYPE == ToastElementType.ACTION:
                # If remote images are enabled, and to_xml() called by show(), cache online images.
                if self.remote_images and self._called_by_show:
                    if element.__class__ == Button:
                        if element.icon and element.icon.startswith("http"):
                            element.icon = self._download_image(element.icon, self.add_query_params) or ""
                el = element.to_xml()
                # Replace with temp file path without modifying the original element.
                if replace_source:
                    el = el.replace("imageUri=\"" + element.icon + "\"", "imageUri=\"" + replace_source + "\"")
                actions += el
            else:
                other += element.to_xml()
        # Add notification sound properties
        other += xml(
            "audio", 
            src = self.sound,
            silent = self._mute_sound_override or (self.sound == None),
            loop = self.sound_loop
        )
        self._called_by_show = False
        # Build toast XML document
        return xml(
            "toast",
                xml(
                    "visual", 
                    xml(
                        "binding", 
                        visual,
                        template = "ToastGeneric"
                    ),
                    baseUri = self.base_path or "file:///"
                ) + ("" if not actions else \
                xml(
                    "actions", 
                    actions
                )) + other,
            launch = self.arguments,
            duration = None if not self.duration else self.duration.value,
            scenario = None if not self.scenario else self.scenario.value,
            displayTimestamp = None if not self.timestamp else self.timestamp.isoformat(),
            useButtonStyle = self.use_button_style
        )


    def _handle_toast_activated(self, toast : ToastNotification, args : Object):
        eventargs = ToastActivatedEventArgs._from(args)
        if self._toast_handler:
            self._toast_handler(eventargs.arguments, 
                ({} if not eventargs.user_input else {
                    x : IPropertyValue._from(y).get_string() for x, y in eventargs.user_input.items()
                }), -1
            )


    def _handle_toast_dismissed(self, toast : ToastNotification, args : ToastDismissedEventArgs):
        if self._toast_handler:
            self._toast_handler("", {}, args.reason.value)


    def _handle_toast_failed(self, toast : ToastNotification, args : ToastFailedEventArgs):
        raise RuntimeError("Toast failed with error code:", args.error_code.value)


    def _handle_toast_shown(self, data : Dict[str, str]):
        if self._show_handler:
            self._show_handler(data)


    def _build_image_query_params(self) -> Dict[str, Any]:
        # Build query parameters like how Windows does.
        color = UISettings().get_color_value(UIColorType.BACKGROUND)
        lang = locale.windows_locale[windll.kernel32.GetUserDefaultUILanguage()].lower().replace("_", "-")
        high_contrast = AccessibilitySettings().high_contrast
        return {
            "ms-contrast": "high" if high_contrast else "standard",
            "ms-lang": lang,
            "ms-theme": "dark" if (color.g + color.r + color.b) == 0 else "light"
        }


    def _download_image(self, remote : str, add_query_params : bool = False) -> Optional[str]:
        # Only allow images smaller than or equal to 3 MB.
        # https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/send-local-toast?tabs=uwp#adding-images
        with httpx.stream(
            "GET", remote, 
            trust_env = False, follow_redirects = True, 
            headers = {"Range": "bytes=0-3000000"}, 
            params = None if not add_query_params else self._build_image_query_params()
        ) as stream:
            if not stream.is_success:
                return
            file = NamedTemporaryFile("w+b", suffix = ".png")
            for i in stream.iter_bytes(1024 * 10):
                file.write(i)
            file.flush()
            self._temp_files.append(file)
            return "file:///" + file.name


    def _cleanup_images(self):
        for i in self._temp_files:
            i.close()
            self._temp_files.remove(i)


    def _create_handler_future(
        self,
        notification : ToastNotification, 
        loop : asyncio.AbstractEventLoop, 
        method_name : str, 
        hook_name : str
    ) -> Tuple[asyncio.Future, EventRegistrationToken]:
        future = loop.create_future()
        token : EventRegistrationToken = getattr(notification, method_name)(lambda sender, event_args: \
            loop.call_soon_threadsafe(
                future.set_result, getattr(self, hook_name)(sender, event_args)
            )
        )
        return future, token, 


    def _init_toast(
        self,
        mute_sound : bool = False,
        data : Optional[Dict[str, str]] = None
    ):
        # For convenience, allow muting the sound without setting "toast.sound = None".
        self._mute_sound_override = mute_sound
        self._manager = ToastNotificationManager.create_toast_notifier(sys.executable)
        event_loop = asyncio.get_running_loop()
        self._called_by_show = True
        xmldata = self.to_xml()
        xml = dom.XmlDocument()
        xml.load_xml(xmldata)
        self._toast = ToastNotification(xml)
        if data:
            self._toast.data = NotificationData()
            for k, v in data.items():
                self._toast.data.values[k] = str(v)
        if self.group_id:
            self._toast.group = self.group_id
        if self.toast_id:
            self._toast.tag = self.toast_id
        self._toast.suppress_popup = not self.show_popup
        self._toast.expiration_time = self.expiration_time
        # Create handlers.
        f1, t1 = self._create_handler_future(self._toast, event_loop, "add_activated", "_handle_toast_activated")
        f2, t2 = self._create_handler_future(self._toast, event_loop, "add_dismissed", "_handle_toast_dismissed")
        f3, t3 = self._create_handler_future(self._toast, event_loop, "add_failed", "_handle_toast_failed")
        self._post_init_toast()
        return event_loop, f1, f2, f3, t1, t2, t3, 


    def _post_init_toast(self):
        # Allow people to access the underlying ToastNotification when subclassing the Toast.
        pass


    @staticmethod
    def history_clear() -> None:
        Toast.history_remove_other()


    def history_remove(self) -> None:
        self.history_remove_other(self.group_id, self.toast_id)


    @staticmethod
    def history_remove_other(group_id : Optional[str] = None, toast_id : Optional[str] = None) -> None:
        if toast_id and group_id:
            ToastNotificationManager.get_default().history.remove(toast_id, group_id, sys.executable)
        elif group_id:
            ToastNotificationManager.get_default().history.remove_group(group_id, sys.executable)
        else:
            ToastNotificationManager.get_default().history.clear(sys.executable)


    @staticmethod
    def get_notification_mode() -> ToastNotificationMode:
        return ToastNotificationMode(ToastNotificationManager.get_default().notification_mode.value)


    def toasts_enabled(self) -> bool:
        self._init()
        return self._manager.setting == NotificationSetting.ENABLED


    def hide(self) -> None:
        # If any of these properties are not set, 
        # then we are sure that toast never displayed before.
        if (not self._toast) or (not self._manager):
            return
        self._manager.hide(self._toast)


    def update(
        self,
        data : Dict[str, str]
    ) -> None:
        notifdata = NotificationData()
        for k, v in data.items():
            notifdata.values[k] = str(v)
        update_result = None
        if self.toast_id == None:
            raise ValueError("Toast must have an ID to use update() function.")
        if self.group_id:
            update_result = self._manager.update(notifdata, self.toast_id, self.group_id)
        else:
            update_result = self._manager.update(notifdata, self.toast_id)
        if update_result != NotificationUpdateResult.SUCCEEDED:
            raise ValueError("Failed to update notification: " + update_result.name)


    async def show(
        self,
        mute_sound : bool = False,
        data : Optional[Dict[str, str]] = None
    ) -> None:
        event_loop, f1, f2, f3, t1, t2, t3 = self._init_toast(mute_sound, data)
        tokens = {"1": t1, "2": t2, "3": t3}
        self._manager.show(self._toast)
        future = event_loop.create_future()
        event_loop.call_soon_threadsafe(
            future.set_result, self._handle_toast_shown(data)
        )
        try:
            _, pending = await asyncio.wait([f1, f2, f3], return_when = asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
        finally:
            if (t1 := tokens['1']) is not None:
                self._toast.remove_activated(t1)
            if (t2 := tokens['2']) is not None:
                self._toast.remove_dismissed(t2)
            if (t3 := tokens['3']) is not None:
                self._toast.remove_failed(t3)