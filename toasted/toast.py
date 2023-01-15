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

__all__ = ["Toast"]

from contextlib import closing
from collections.abc import Iterator as CollectionsIterator
from toasted.common import ToastElementContainer, ToastElement, get_enum, xml, ToastResult, get_windows_version
from toasted.history import HistoryForToast
from toasted.enums import ToastDuration, ToastScenario, ToastSound, ToastElementType, ToastNotificationMode, ToastDismissReason
import asyncio
from ctypes import windll
from datetime import datetime
import locale
import inspect
import sys
import winsound
from typing import Any, Callable, Dict, Iterator, Optional, Tuple, Union
from pathlib import Path
import winreg
from uuid import uuid4
import httpx
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
from fs.tempfs import TempFS


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
            The amount of time the toast should display. Allowed values are "long", "short" and None.
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
        app_id:
            Windows requires an ID of installed application in the computer to show notifications from. This also
            sets the icon and name of the given application in the toast title. Defaults to executable path of Python
            (sys.executable), so notification will show up as "Python". However, this will not work for embedded versions
            of Python since Python is not installed on system, so you will need to change this. You can also register 
            an ID in system to use a custom name and icon. See `Toast.register_app_id()`.
    """

    _current_app_id : Optional[str] = None

    __slots__ = (
        "duration",
        "arguments",
        "scenario",
        "timestamp",
        "show_popup",
        "base_path",
        "sound",
        "sound_loop",
        "remote_images",
        "add_query_params",
        "expiration_time",
        "group_id",
        "toast_id",
        "_toast_handler",
        "_show_handler",
        "_manager",
        "_toast",
        "_xml_mute_sound",
        "_xml_resolve_http",
        "_toast_result",
        "_temp_filesystem"
    )

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
        app_id : Optional[str] = None
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
        self.app_id = app_id
        self._toast_handler : Optional[Callable[[str, Optional[Dict[str, str]], int], None]] = None
        self._show_handler : Optional[Callable] = None
        self._manager : ToastNotifier = None
        self._toast : ToastNotification = None
        self._xml_mute_sound : bool = False
        self._xml_resolve_http : bool = False
        self._toast_result : Optional[ToastResult] = None
        self._temp_filesystem : Optional[TempFS] = None


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


    def to_xml(self) -> str:
        # Cleanup old cached media.
        self._close_temp_filesystem()
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
            if self.remote_images and self._xml_resolve_http:
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
            silent = self._xml_mute_sound or (self.sound == None) or (not (self.sound or "ms-winsoundevent:").startswith("ms-winsoundevent:")),
            loop = self.sound_loop
        )
        self._xml_resolve_http = False
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


    def _build_notification_data(self, data : dict) -> NotificationData:
        x = NotificationData()
        for k, v in data.items():
            x.values[str(k)] = str(v)
        return x


    def _handle_toast_activated(self, toast : ToastNotification, args : Object):
        self._close_temp_filesystem()
        eventargs = ToastActivatedEventArgs._from(args)
        result = ToastResult(
            arguments = eventargs.arguments,
            inputs = ({} if not eventargs.user_input else {
                x : IPropertyValue._from(y).get_string() for x, y in eventargs.user_input.items()
            }),
            show_data = {} if not toast.data else dict(toast.data.values.items()),
            dismiss_reason = ToastDismissReason.NOT_DISMISSED
        )
        self._toast_result = result
        if self._toast_handler:
            self._toast_handler(self._toast_result)


    def _handle_toast_dismissed(self, toast : ToastNotification, args : ToastDismissedEventArgs):
        self._close_temp_filesystem()
        winsound.PlaySound(None, 4)
        result = ToastResult(
            arguments = "", 
            inputs = {},
            show_data = {} if not toast.data else dict(toast.data.values.items()), 
            dismiss_reason = ToastDismissReason(args.reason.value)
        )
        self._toast_result = result
        if self._toast_handler:
            self._toast_handler(self._toast_result)


    def _handle_toast_failed(self, toast : ToastNotification, args : ToastFailedEventArgs):
        self._close_temp_filesystem()
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


    def _create_temp_filesystem(self) -> TempFS:
        if self._temp_filesystem:
            return self._temp_filesystem
        self._temp_filesystem = TempFS()
        return self._temp_filesystem


    def _close_temp_filesystem(self) -> None:
        if self._temp_filesystem:
            self._temp_filesystem.close()


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
            return self.import_media(stream.iter_bytes(1024 * 10))


    def import_media(self, data : Union[bytes, Iterator[bytes]]) -> str:
        """
        Creates a temporary file on filesystem with given bytes to use as an image/sound source.
        In other terms, instead of providing a local file path or a HTTP source to images/sounds,
        you can provide a bytes object directly using this method. The return value is the created
        path of the temporary file.

        Parameters:
            data:
                A bytes object or an iterator of bytes.
        """
        is_iterator = isinstance(data, CollectionsIterator)
        filename = str(uuid4()).replace("-", "")
        filesystem = self._create_temp_filesystem()
        with closing(filesystem.open(filename, mode="wb")) as file:
            if is_iterator:
                for i in data:
                    file.write(i)
            else:
                file.write(data)
        return filesystem.getsyspath("/" + filename)


    @staticmethod
    def register_app_id(
        handle : str, 
        display_name : Optional[str] = None,
        icon_background_color : Optional[str] = None,
        icon_uri : Optional[str] = None,
        show_in_settings : bool = True
    ) -> str:
        """
        Registers an app ID (AUMID) in Windows Registry to use a custom icon and name for notifications.
        Returns the given handle.
        https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/send-local-toast-other-apps#step-1-register-your-app-in-the-registry

        Parameters:
            handle:
                A unique ID that identifies the app in "CompanyName.ProductName.SubProduct.VersionInformation" format,
                (last section, "VersionInformation" is optional)
            display_name:
                A display name for application. Shows as title in notification. If not provided, same as handle.
            icon_background_color:
                Background color of icon in ARGB hex format. Default is #00000000.
            icon_uri:
                URI or file path of application icon. Shows up as icon in notification.
            show_in_settings:
                True (default) to show this application in notification settings.
        """
        if (not handle) or (len(handle) > 129):
            raise ValueError("Invalid handle; " + ("maximum allowed characters is 129." if handle else "can't be empty."))
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Classes\\AppUserModelId\\" + handle)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_EXPAND_SZ, display_name or handle)
        winreg.SetValueEx(key, "IconBackgroundColor", 0, winreg.REG_SZ, (icon_background_color or "#00000000").replace("#", ""))
        winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, icon_uri)
        winreg.SetValueEx(key, "CustomActivator", 0, winreg.REG_SZ, "{" + str(uuid4()).upper() + "}")
        winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, int(show_in_settings))
        return handle


    @staticmethod
    def unregister_app_id(handle : str) -> None:
        """
        Unregisters an app ID in Windows Registry by deleting the associated key. Unwanted
        system behaviours MAY happen if you unregister an another application of system. It is
        advised to only work with handles used in register_app_id()

        Parameters:
            handle:
                A unique ID that identifies the app.
        """
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Classes\\AppUserModelId\\" + handle)


    @property
    def app_id(self) -> str:
        return self._current_app_id or sys.executable

    @app_id.setter
    def app_id(self, value : Optional[str]) -> None:
        """
        Sets the app ID for currently running Python process.
        https://learn.microsoft.com/en-us/windows/win32/shell/appids#how-to-form-an-application-defined-appusermodelid

        Parameters:
            app_id:
                An executable file path of application registered on system 
                or an AUMID in "CompanyName.ProductName.SubProduct.VersionInformation" format,
                (last section, "VersionInformation" is optional)
        """
        if value != Toast._current_app_id:
            Toast._current_app_id = value or sys.executable
            # https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid
            # https://stackoverflow.com/a/1552105
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(value or sys.executable)


    @property
    def history(self) -> HistoryForToast:
        """
        Get History object bound for this toast.
        """
        return HistoryForToast(self)


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
        self._manager = ToastNotificationManager.create_toast_notifier(self.app_id)
        event_loop = asyncio.get_running_loop()
        # Create toast XML document
        self._xml_mute_sound = mute_sound
        self._xml_resolve_http = True
        xml = dom.XmlDocument()
        xml.load_xml(self.to_xml())
        self._toast = ToastNotification(xml)
        if data:
            self._toast.data = self._build_notification_data(data)
        if self.group_id:
            release, _ = get_windows_version()
            # TODO: Looks like groups doesn't work in Windows 11.
            if release != 11:
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
        return event_loop, f1, f2, f3, t1, t2, t3, custom_sound,


    @staticmethod
    def get_notification_mode() -> ToastNotificationMode:
        return ToastNotificationMode(ToastNotificationManager.get_default().notification_mode.value)


    def toasts_enabled(self) -> bool:
        if not self._manager:
            self._manager = ToastNotificationManager.create_toast_notifier(self.app_id)
        return self._manager.setting == NotificationSetting.ENABLED


    def hide(self) -> None:
        # If any of these properties are not set, 
        # then we are sure that toast never displayed before.
        if (not self._toast) or (not self._manager):
            return
        self._close_temp_filesystem()
        winsound.PlaySound(None, 4)
        self._manager.hide(self._toast)


    def update(
        self,
        data : Dict[str, str],
        silent : bool = False
    ) -> bool:
        """
        Updates the notification without showing a new one. Used for changing dynamic
        values (a.k.a. binding values). You won't need this method if you don't use any binding
        values. Returns True if succeded (always True if silent is False).

        Parameters:
            data:
                Dictionary of binding keys and their values to replace with.
                See also show() method to set initial values of binding keys before showing the toast.
            silent:
                If True, no exceptions will be raised when notification was not found 
                (user has deleted the notification). Defaults to False.
        """
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
        return update_result == 0


    async def show(
        self,
        data : Optional[Dict[str, str]] = None,
        mute_sound : bool = False
    ) -> ToastResult:
        """
        Shows the notification. If there is any {binding} key, you can give a "data" 
        dictionary to replace binding keys with their values. You can also "mute_sound" 
        to mute notification sound regardless of "sound" attribute of this toast. 

        Parameters:
            data:
                Dictionary of binding keys and their initial values to replace with.
                See also update() method to update binding keys after showing the toast.
            mute_sound:
                Mute the sound of this notification, if set any. Can be useful if you want to
                show same toast but want to mute sound to prevent repetitive notification
                sounds without needing to change Toast.sound attribute.
        """
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
            app_id = str(json.get("app_id", "")) or None
        )
        for el in json["elements"]:
            toast.append(ToastElement._create_from_type(**el))
        return toast

    def copy(self) -> "Toast":
        return self.__copy__()

    def __repr__(self) -> str:
        return f"<{self.__class__} id={self.toast_id} group={self.group_id} elements={len(self.data)}>"

    def __del__(self):
        self._close_temp_filesystem()

    def __copy__(self) -> "Toast":
        x = Toast()
        for i in self.__slots__:
            setattr(x, i, getattr(self, i))
        return x