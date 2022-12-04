__all__ = ["Toast"]

import os
from toasted.common import ToastElementContainer, ToastElement, get_enum, xml, ToastResult
from toasted.enums import ToastDuration, ToastScenario, ToastSound, ToastElementType, ToastNotificationMode
import asyncio
import re
from ctypes import windll
from datetime import datetime
import locale
import mimetypes
import inspect
import sys
from tempfile import NamedTemporaryFile
import httpx
import winsound
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path
from winsdk.windows.ui.notifications import (
    ToastNotification, 
    ToastNotificationManager, 
    ToastActivatedEventArgs, 
    ToastDismissedEventArgs, 
    ToastFailedEventArgs,
    ToastNotifier,
    NotificationSetting,
    NotificationData
)
from winsdk._winrt import Object
from winsdk.windows.foundation import IPropertyValue, EventRegistrationToken
from winsdk.windows.ui.viewmanagement import AccessibilitySettings, UISettings, UIColorType
import winsdk.windows.data.xml.dom as dom
import winreg
from uuid import uuid4


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
        source_app_id:
            Windows requires an ID of installed application in the computer to show notifications from. Therefore,
            Python must be installed on the computer. However, you can set a custom "source_app_id" of an application
            that installed on your computer, so you can display toast notification on embedded versions of Python.
            For example, setting "Microsoft.Windows.Explorer" as ID will display "Windows Explorer" in the toast.
            Defaults to executable path of the Python (sys.executable).
    """

    def __init__(
        self, 
        arguments : Optional[str] = None,
        duration : Optional[ToastDuration] = None, 
        timestamp : Optional[datetime] = None,
        scenario : Optional[ToastScenario] = None,
        group_id : Optional[str] = None,
        toast_id : Optional[str] = None,
        show_popup : bool = True,
        base_path : Optional[str] = None,
        sound : Optional[str] = ToastSound.DEFAULT,
        sound_loop : bool = False,
        remote_images : bool = True,
        add_query_params : bool = False,
        expiration_time : Optional[datetime] = None,
        source_app_id : str = sys.executable
    ) -> None:
        super().__init__()
        self.duration = duration
        self.arguments = arguments
        self.scenario = scenario
        self.timestamp = timestamp
        self.show_popup = show_popup
        self.base_path = base_path
        self.sound = sound or None
        self.sound_loop = sound_loop
        self.remote_images = remote_images
        self.add_query_params = add_query_params
        self.expiration_time = expiration_time
        self.group_id = group_id
        self.toast_id = toast_id
        self.source_app_id = source_app_id
        self._toast_handler : Optional[Callable[[str, Optional[Dict[str, str]], int], None]] = None
        self._show_handler : Optional[Callable] = None
        self._manager : ToastNotifier = None
        self._toast : ToastNotification = None
        self._mute_sound_override : bool = False
        self._temp_files : List[Any] = []
        self._called_by_show : bool = False
        self._toast_result : Optional[ToastResult] = None


    def __copy__(self) -> "Toast":
        x = Toast(
            duration = self.duration,
            arguments = self.arguments,
            scenario = self.scenario,
            toast_id = self.toast_id,
            group_id = self.group_id,
            show_popup = self.show_popup,
            timestamp = self.timestamp,
            base_path = self.base_path,
            sound = self.sound,
            sound_loop = self.sound_loop,
            remote_images = self.remote_images,
            add_query_params = self.add_query_params,
            expiration_time = self.expiration_time,
            source_app_id = self.source_app_id
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
            group_id = str(json.get("group_id", "")) or None,
            toast_id = str(json.get("toast_id", "")) or None,
            show_popup = bool(json.get("show_popup", True)),
            base_path = str(json.get("base_path", "")) or None,
            timestamp = None if "timestamp" not in json else datetime.fromisoformat(json["timestamp"]),
            sound = json.get("sound", ToastSound.DEFAULT),
            sound_loop = bool(json.get("sound_loop", False)),
            remote_images = bool(json.get("remote_images", True)),
            add_query_params = bool(json.get("add_query_params", False)),
            expiration_time = None if "expiration_time" not in json else datetime.fromisoformat(json["expiration_time"]),
            source_app_id = str(json.get("group_id", "")) or sys.executable
        )
        for el in json["elements"]:
            toast.append(ToastElement._create_from_type(**el))
        return toast


    def handler(self, function : Optional[Callable[[ToastResult], None]] = None):
        """
        A decorator that calls the function when user has clicked or dismissed the toast.
        An instance of ToastResult will be passed to the handler.
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
        The notification data passed to show() will be passed to the handler.
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
        # Cleanup old cached media.
        self._cleanup_media()
        output = ["", "", ""]
        # 1st - Visual
        # 2nd - Action
        # 3rd - Other
        using_custom_style : bool = False
        for element in self.data:
            if not isinstance(element, ToastElement):
                raise ValueError("Element must be a type of ToastElement:", element)
            el = element.to_xml()
            # Download remote images to disk, and replace the URL
            # with the cached image's file path by editing the output XML.
            if self.remote_images and self._called_by_show:
                for r_type, r_key, r_value, _ in element._resolve():
                    if r_type == "REMOTE":
                        temp_file = "file:///" + Path(self._download_media(r_value, self.add_query_params) or "").resolve().as_posix()
                        el = el.replace(r_key + "=\"" + r_value + "\"", r_key + "=\"" + temp_file + "\"")
            # Enable custom styles on the toast
            # if button has a custom style.
            if "hint-buttonStyle=\"" in el:
                using_custom_style = True
            # Append output XML to list.
            output[
                0 if element._etype == ToastElementType.VISUAL else
                1 if element._etype == ToastElementType.ACTION else
                2
            ] += el
        # Add notification sound properties
        output[2] += xml(
            "audio", 
            src = self.sound if (self.sound or "ms-winsoundevent:").startswith("ms-winsoundevent:") else None,
            # If custom sound has provided, mute the original toast sound to None 
            # since we use our own sound solution.
            silent = self._mute_sound_override or (self.sound == None) or (not (self.sound or "ms-winsoundevent:").startswith("ms-winsoundevent:")),
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
                        output[0],
                        template = "ToastGeneric"
                    ),
                    baseUri = self.base_path or "file:///"
                ) + ("" if not output[1] else \
                xml(
                    "actions", 
                    output[1]
                )) + output[2],
            launch = self.arguments,
            duration = None if not self.duration else self.duration.value,
            scenario = None if not self.scenario else self.scenario.value,
            displayTimestamp = None if not self.timestamp else self.timestamp.isoformat(),
            useButtonStyle = using_custom_style or None
        )


    def _to_xml_document(self, mute_sound : bool) -> dom.XmlDocument:
        self._mute_sound_override = mute_sound
        self._called_by_show = True
        xmldata = self.to_xml()
        xml = dom.XmlDocument()
        xml.load_xml(xmldata)
        return xml


    def _build_notification_data(self, data : dict) -> NotificationData:
        x = NotificationData()
        for k, v in data.items():
            x.values[k] = str(v)
        return x


    def _handle_toast_activated(self, toast : ToastNotification, args : Object):
        self._cleanup_media()
        eventargs = ToastActivatedEventArgs._from(args)
        result = ToastResult(
            arguments = eventargs.arguments,
            inputs = ({} if not eventargs.user_input else {
                x : IPropertyValue._from(y).get_string() for x, y in eventargs.user_input.items()
            }),
            show_data = {} if not toast.data else dict(toast.data.values.items()),
            dismiss_reason = -1
        )
        self._toast_result = result
        if self._toast_handler:
            self._toast_handler(self._toast_result)


    def _handle_toast_dismissed(self, toast : ToastNotification, args : ToastDismissedEventArgs):
        self._cleanup_media()
        winsound.PlaySound(None, 4)
        result = ToastResult(
            arguments = "", 
            inputs = {},
            show_data = {} if not toast.data else dict(toast.data.values.items()), 
            dismiss_reason = args.reason.value
        )
        self._toast_result = result
        if self._toast_handler:
            self._toast_handler(self._toast_result)


    def _handle_toast_failed(self, toast : ToastNotification, args : ToastFailedEventArgs):
        self._cleanup_media()
        winsound.PlaySound(None, 4)
        raise RuntimeError("Toast failed with error code:", args.error_code.value)


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


    def _download_media(self, remote : str, add_query_params : bool = False) -> Optional[str]:
        # Only allow media smaller than or equal to 3 MB.
        # https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/send-local-toast?tabs=uwp#adding-images
        with httpx.stream(
            "GET", remote, 
            trust_env = False, follow_redirects = True, 
            headers = {"Range": "bytes=0-3000000"}, 
            params = None if not add_query_params else self._build_image_query_params()
        ) as stream:
            if not stream.is_success:
                return
            # Try to guess the file extension.
            filename = re.findall("filename=\"(.*)\"", stream.headers.get("Content-Disposition", ""))
            mimetype, _ = mimetypes.guess_type(remote if not filename else filename[0], False)
            extension = mimetypes.guess_extension(mimetype, False)
            file = NamedTemporaryFile("w+b", suffix = extension, delete = False)
            for i in stream.iter_bytes(1024 * 10):
                file.write(i)
            file.close()
            self._temp_files.append(file)
            return file.name


    def _cleanup_media(self):
        for i in self._temp_files:
            try:
                os.remove(i.name)
            except Exception:
                pass
        self._temp_files.clear()

    
    @staticmethod
    def register_app_id(handle : str = "Toasted.Notification.Test", display_name : str = "My App"):
        # https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/send-local-toast-other-apps
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Classes\\AppUserModelId\\" + handle)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_EXPAND_SZ, display_name)
        winreg.SetValueEx(key, "IconBackgroundColor", 0, winreg.REG_SZ, "0")
        winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, "ms-resource://Windows.ParentalControlsSettings/Files/Images/MicrosoftFamily.png")
        winreg.SetValueEx(key, "CustomActivator", 0, winreg.REG_SZ, "{" + str(uuid4()).upper() + "}")
        winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, 0)


    @staticmethod
    def unregister_app_id(handle : str = "Toasted.Notification.Test"):
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Classes\\AppUserModelId\\" + handle)


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
        # https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid
        # https://stackoverflow.com/a/1552105
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.source_app_id)
        # For convenience, allow muting the sound without setting "toast.sound = None".
        self._manager = ToastNotificationManager.create_toast_notifier(self.source_app_id)
        event_loop = asyncio.get_running_loop()
        self._toast = ToastNotification(self._to_xml_document(mute_sound))
        if data:
            self._toast.data = self._build_notification_data(data)
        if self.group_id:
            self._toast.group = self.group_id
        if self.toast_id:
            self._toast.tag = self.toast_id
        self._toast.suppress_popup = not self.show_popup
        self._toast.expiration_time = self.expiration_time
        custom_sound = None
        # Check for custom sound, and if custom sound is HTTP, download it.
        if (not (self.sound or "ms-winsoundevent:").startswith("ms-winsoundevent:")):
            if (self.sound or "").startswith("http"):
                custom_sound = self._download_media(self.sound, False)
            else:
                custom_sound = self.sound
        # Create handlers.
        f1, t1 = self._create_handler_future(self._toast, event_loop, "add_activated", "_handle_toast_activated")
        f2, t2 = self._create_handler_future(self._toast, event_loop, "add_dismissed", "_handle_toast_dismissed")
        f3, t3 = self._create_handler_future(self._toast, event_loop, "add_failed", "_handle_toast_failed")
        self._post_init_toast()
        return event_loop, f1, f2, f3, t1, t2, t3, custom_sound,


    def _post_init_toast(self):
        # Allow people to access the underlying ToastNotification when subclassing the Toast.
        pass


    def history_clear(self) -> None:
        self.history_remove_other(self.source_app_id)


    def history_remove(self) -> None:
        self.history_remove_other(self.source_app_id, self.group_id, self.toast_id)


    @staticmethod
    def history_remove_other(app_id : str, group_id : Optional[str] = None, toast_id : Optional[str] = None) -> None:
        if toast_id and group_id:
            ToastNotificationManager.get_default().history.remove(toast_id, group_id, app_id)
        elif group_id:
            ToastNotificationManager.get_default().history.remove_group(group_id, app_id)
        else:
            ToastNotificationManager.get_default().history.clear(app_id)


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
        self._cleanup_media()
        winsound.PlaySound(None, 4)
        self._manager.hide(self._toast)


    def update(
        self,
        data : Dict[str, str],
        silent : bool = False
    ) -> int:
        notifdata = self._build_notification_data(data)
        update_result = None
        if self.toast_id == None:
            raise ValueError("Toast must have an ID to use update() function.")
        if self.group_id:
            update_result = self._manager.update(notifdata, self.toast_id, self.group_id).value
        else:
            update_result = self._manager.update(notifdata, self.toast_id).value
        if update_result != 0:
            if not silent:
                raise Exception("Failed to update the notification;", (
                    "notification has not found." if update_result == 2 else
                    "unknown error."
                ))
        return update_result


    async def show(
        self,
        data : Optional[Dict[str, str]] = None,
        mute_sound : bool = False
    ) -> ToastResult:
        event_loop, f1, f2, f3, t1, t2, t3, custom_sound = self._init_toast(mute_sound, data)
        tokens = {"1": t1, "2": t2, "3": t3}
        self._manager.show(self._toast)
        future = event_loop.create_future()
        # If sound is custom, play with winsound.
        if custom_sound:
            if mute_sound:
                winsound.PlaySound(None, 4)
            else:
                winsound.PlaySound(
                    Path(custom_sound).resolve().as_posix(), 
                    winsound.SND_FILENAME + winsound.SND_NODEFAULT + winsound.SND_ASYNC + \
                    (winsound.SND_LOOP if self.sound_loop else 0)
                )
        # Execute show handler.
        if self._show_handler:
            if inspect.iscoroutinefunction(self._show_handler):
                await self._show_handler(data)
            else:
                event_loop.call_soon_threadsafe(
                    future.set_result, self._show_handler(data)
                )
        try:
            _, pending = await asyncio.wait([f1, f2, f3], return_when = asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
            return self._toast_result
        finally:
            if (t1 := tokens['1']) is not None:
                self._toast.remove_activated(t1)
            if (t2 := tokens['2']) is not None:
                self._toast.remove_dismissed(t2)
            if (t3 := tokens['3']) is not None:
                self._toast.remove_failed(t3)