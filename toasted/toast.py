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

from toasted.common import ( 
    ToastElement,
    ToastThemeInfo,
    get_query_app_ids,
    get_windows_build,
    ToastResult,
    resolve_uri,
)
from toasted.elements import Button, Image, Text
from toasted.filesystem import ToastMediaFileSystem
from toasted.history import HistoryForToast
from toasted.enums import (
    ToastDuration, 
    ToastScenario, 
    ToastSound, 
    ToastElementType, 
    ToastNotificationMode, 
    ToastDismissReason
)

import asyncio
from datetime import datetime
import locale
import inspect
import sys
from typing import (
    Any, Callable, Dict, Optional, Tuple, 
    List, Union, Set
)
from pathlib import Path
from xml.etree import ElementTree as ET

if sys.platform == "win32":
    import winreg
    import winsound
    from ctypes import windll

    from winrt.system import Object  # pyright: ignore[reportMissingImports]
    from winrt.windows.foundation import IPropertyValue, EventRegistrationToken  # pyright: ignore[reportMissingImports]
    from winrt.windows.ui.viewmanagement import (  # pyright: ignore[reportMissingImports]
        AccessibilitySettings, 
        UISettings, 
        UIColorType
    )
    import winrt.windows.data.xml.dom as dom  # pyright: ignore[reportMissingImports]
    from winrt.windows.ui.notifications import (  # pyright: ignore[reportMissingImports]
        ToastNotification, 
        ToastNotificationManager, 
        ToastActivatedEventArgs, 
        ToastDismissedEventArgs, 
        ToastFailedEventArgs,
        ToastNotifier,
        NotificationSetting,
        NotificationData
    )
else:
    class Proxy:
        def __getattribute__(self, _): raise Exception("Toasted is not supported on non-Windows platforms.") # noqa: E501
    winreg = winsound = windll = Object = IPropertyValue = \
    EventRegistrationToken = AccessibilitySettings = UISettings = UIColorType = \
    dom = ToastNotification = ToastNotificationManager = ToastActivatedEventArgs = \
    ToastDismissedEventArgs = ToastFailedEventArgs = ToastNotifier = \
    NotificationSetting = NotificationData = Proxy()

ToastDataType = Dict[str, str]
ToastResultCallbackType = Optional[Callable[[ToastResult], None]]
ToastShowCallbackType = Optional[Callable[[Optional[ToastDataType]], None]]

ToastElementListItem = Union[
    ToastElement, 
    List[List[Union[Image, Text]]]
]

ToastElementListItemJSON = Union[
    Dict[str, Any],
    List[List[Dict[str, Any]]]
]

class Toast:
    """
    Represents a toast.
    https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/adaptive-interactive-toasts?tabs=builder-syntax

    Args:
        arguments:
            A string that is passed to the application when it is activated by the 
            toast. The format and contents of this string are defined by the app for 
            its own use. When the user taps or clicks the toast to launch its 
            associated app, the launch string provides the context to the app that 
            allows it to show the user a view relevant to the toast content, rather 
            than launching in its default way.
        duration:
            The amount of time the toast should display. Allowed values are 
            "long", "short" and None.
        timestamp:
            Introduced in Creators Update: Overrides the default timestamp with a 
            custom timestamp representing when your notification content was actually 
            delivered, rather than the time the notification was received by the 
            Windows platform.
        scenario:
            The scenario your toast is used for, like an alarm or reminder. 
            REMINDER: A reminder notification. This will be displayed pre-expanded and 
                stay on the user's screen till dismissed.
            ALARM: An alarm notification. This will be displayed pre-expanded and stay 
                on the user's screen till dismissed. Audio will loop by default and 
                will use alarm audio.
            INCOMING_CALL: An incoming call notification. This will be displayed 
                pre-expanded in a special call format and stay on the user's screen 
                till dismissed. Audio will loop by default and will use ringtone audio.
            URGENT: Only takes an effect in Windows 11 build 22546 or later.
                An important notification. This allows users to have more control 
                over what apps can send them high-priority toast notifications that can 
                break through Focus Assist (Do not Disturb). This can be modified in 
                the notifications settings. If URGENT is not supported in current 
                system, notification will be shown normally.
            None: Default notification. (default)
        group_id:
            Group ID that this toast belongs in. Used for deleting a notification 
            from Action Center.
        toast_id:
            ID of the toast. Used for deleting a notification from Action Center.
        contact_info:
            Shouldn't be used. Was in use for unsupported [My People](https://learn.microsoft.com/en-us/windows/uwp/contacts-and-calendar/my-people-notifications) notifications.
            This won't work in Windows 11 and Windows 10 versions with KB5034203 update.
            Sets the sending contact information.
        show_popup:
            Gets or sets whether a toast's pop-up UI is displayed on the user's screen. 
            If pop-up is not shown, the notification will be added to Action Center 
            silently. Do not set this property to true in a toast sent to a Windows 
            8.x device. Doing so will cause a dropped notification.
        base_path:
            Specify a base file path which is used when an image source is a relative 
            path. For example, if base_path is "file:///C:/Users/ysfchn/Desktop/" and 
            an Image element's source is "test.png", the resulting path will be 
            "file:///C:/Users/ysfchn/Desktop/test.png", defaults to current running 
            path. If specified, it must end with slash (/).
        sound:
            Specifies a sound to play when a toast notification is displayed. 
            Set to None for mute the notification sound.
        sound_loop:
            Set to true if the sound should repeat as long as the toast is shown; 
            false to play only once. If this attribute is set to true, 
            the duration attribute in the toast element must also be set. 
            There are specific sounds provided to be used when looping. 
        remote_media:
            If True, makes https:// and http:// links functional on media sources by 
            downloading the files in temporary directory, then deletes them when toast 
            has clicked or dismissed.
        add_query_params:
            Set to True to append a query string to the image URI supplied 
            in the toast notification. Use this attribute if your server hosts images 
            and can handle query strings, either by retrieving an image variant based 
            on the query strings or by ignoring the query string and returning the 
            image as specified without the query string. This query string specifies 
            contrast setting, language and theme; for instance, a value of:
            "https://example.com/images/foo.png" given in the notification becomes
            "https://example.com/images/foo.png?ms-contrast=standard&ms-lang=en-us&ms-theme=dark".
        expiration_time:
            In Windows 10, all toast notifications go in Action Center after they are 
            dismissed or ignored by the user, so users can look at your notification 
            after the popup is gone. However, if the message in your notification is 
            only relevant for a period of time, you should set an expiration time on 
            the toast notification so the users do not see stale information from your 
            app. For example, if a promotion is only valid for 12 hours, set the 
            expiration time to 12 hours.
        app_id:
            Windows requires the Application Model ID of any registered application 
            on the system to send notifications on its behalf, so toast notification
            will have the icon and the name of the specified icon. For example, by
            default, toasts will be sent on behalf of Python executable. 
            (sys.executable) So in the toast title, it will show up as "Python".
            However, the default approach will not work for portable versions of
            Python since Python is not registered to the system in this case, so 
            you will need to use one of app IDs registered in system or create 
            yours with `Toast.register_app_id()`, so you can set a custom name and icon.
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
        "elements",
        "remote_media",
        "add_query_params",
        "expiration_time",
        "group_id",
        "toast_id",
        "contact_info",
        "_callback_result",
        "_callback_show",
        "_imp_manager",
        "_imp_toast",
        "_xml_mute_sound",
        "_fs"
    )

    _exclude_copy = (
        "_fs",
        "_toast_result",
        "_xml_mute_sound"
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
        remote_media : bool = True,
        add_query_params : bool = False,
        expiration_time : Optional[datetime] = None,
        app_id : Optional[str] = None,
        contact_info : Optional[str] = None
    ) -> None:
        super().__init__()
        self.elements : List[ToastElementListItem] = []
        self.duration = duration
        self.arguments = arguments
        self.scenario = scenario
        self.timestamp = timestamp
        self.show_popup = show_popup
        self.base_path = base_path
        self.sound = sound or None
        self.sound_loop = sound_loop
        self.remote_media = remote_media
        self.add_query_params = add_query_params
        self.expiration_time = expiration_time
        self.group_id = group_id
        self.toast_id = toast_id
        self.app_id = app_id
        self.contact_info = contact_info
        self._callback_result : ToastResultCallbackType = None
        self._callback_show : ToastShowCallbackType = None
        self._imp_manager : "ToastNotifier" = None
        self._imp_toast : "ToastNotification" = None
        self._xml_mute_sound : bool = False
        self._fs : Optional[ToastMediaFileSystem] = None


    def on_result(self, function : ToastResultCallbackType = None):
        """
        A decorator that calls the function when user has clicked or dismissed 
        the toast. An instance of ToastResult will be passed to the handler.
        """
        if function:
            self._callback_result = function
            return function
        else:
            def decorator(func : Callable):
                self._callback_result = func
                return func
            return decorator


    def on_shown(self, function : ToastShowCallbackType = None):
        """
        A decorator that calls the function when toast has shown with show().
        The notification data passed to show() will be passed to the handler.
        """
        if function:
            self._callback_show = function
            return function
        else:
            def decorator(func : Callable):
                self._callback_show = func
                return func
            return decorator


    def _to_xml(self, allow_fs: bool):
        """
        Create XML representing the toast.
        """
        root = ET.Element("toast")
        if self.arguments:
            root.attrib["launch"] = self.arguments
        if self.duration:
            root.attrib["duration"] = self.duration.value
        if self.scenario:
            root.attrib["scenario"] = self.scenario.value
        if self.timestamp:
            root.attrib["displayTimestamp"] = self.timestamp.isoformat(timespec = "milliseconds")

        visual = ET.Element("visual")
        actions = ET.Element("actions")
        binding = ET.Element("binding")
        binding_exp = ET.Element("binding")
        binding.attrib["template"] = "ToastGeneric"
        binding_exp.attrib["template"] = "ToastGeneric"
        binding_exp.attrib["experienceType"] = "shoulderTap"
        visual.append(binding)
        root.append(visual)

        query_params = None if not self.add_query_params else self.get_theme_info().as_params()

        # Iterate through elements and add them to the binding element.
        for item in self.elements:
            if isinstance(item, list):
                group = ET.Element("group")
                for subgroup in item:
                    sgroup = ET.Element("subgroup")
                    assert isinstance(subgroup, list), "Groups can only contain subgroups."
                    for child in subgroup:
                        assert isinstance(child, (Image, Text)), "Subgroups can only contain Image or Text elements."
                        el = child._to_xml()

                        # Resolve URIs found in the element.
                        for arg in child._euri:
                            if el.attrib.get(arg):
                                el.attrib[arg] = self._resolve_uri(el.attrib[arg], allow_fs, query_params)
                        sgroup.append(el)
                    group.append(sgroup)
                binding.append(group)
            else:
                assert isinstance(item, ToastElement), "Toasts must contain of ToastElement objects."
                el = item._to_xml()
                is_spritesheet = False

                # Resolve URIs found in the element.
                for arg in item._euri:
                    if el.attrib.get(arg):
                        if arg == "spritesheet-src":
                            assert self.contact_info, "My People notifications require a contact info to be set with Toast.contact_info, otherwise remove the sprite from the image."
                            is_spritesheet = True
                        el.attrib[arg] = self._resolve_uri(el.attrib[arg], allow_fs, query_params)
                if item._etype == ToastElementType.ACTION:
                    actions.append(el)
                elif item._etype == ToastElementType.HEADER:
                    root.append(el)
                elif is_spritesheet:
                    binding_exp.append(el)
                else:
                    binding.append(el)

                # Enable custom styles on the toast itself if any button has a custom style.
                if isinstance(item, Button):
                    if item.style:
                        root.attrib["useButtonStyle"] = "true"
        if len(actions):
            root.append(actions)

        if self.contact_info:
            assert self.contact_info.startswith("tel:") or self.contact_info.startswith("mailto:") or self.contact_info.startswith("remoteid:"), \
                "Toast.contact_info must start with 'tel:', 'mailto:' or 'remoteid:' if given."

        if len(binding_exp) and self.contact_info:
            visual.append(binding_exp)
            root.attrib["hint-people"] = self.contact_info

        if len(actions) > 5:
            raise ValueError("A Toast notification can only have up to 5 actions.")

        # Notification sound
        audio = ET.Element("audio")
        if self.sound:
            audio.attrib["src"] = self._resolve_uri(self.sound, allow_fs, query_params)

        # If custom sound has provided, mute the original toast 
        # sound to None since we use our own sound solution.
        if self._xml_mute_sound or self.uses_custom_sound:
            audio.attrib["silent"] = "true"
        audio.attrib["loop"] = "true" if self.sound_loop else "false"
        root.append(audio)
        return root


    def _resolve_uri(self, uri: str, allow_fs: bool, query_params: Optional[Dict[str, str]]):
        resolved = resolve_uri(uri)
        if resolved.type == "hex":
            if allow_fs:
                if not self._fs:
                    self._fs = ToastMediaFileSystem()
                return self._fs.put(bytes.fromhex(resolved.value))
        elif resolved.type == "remote":
            if allow_fs:
                if not self.remote_media:
                    raise ValueError(f"Downloading from remote URI '{resolved.value}' was disallowed by `Toast.remote_media` property.")
                if not self._fs:
                    self._fs = ToastMediaFileSystem()
                return self._fs.get(
                    url = resolved.value,
                    query_params = query_params
                )
        else:
            return resolved.value
        return uri


    def to_xml_string(
        self,
        download_media: bool = False
    ) -> str:
        return ET.tostring(self._to_xml(download_media), encoding = "unicode")


    @staticmethod
    def register_app_id(
        handle : str, 
        display_name : Optional[str] = None,
        icon_background_color : Optional[str] = None,
        icon_uri : Optional[str] = None,
        show_in_settings : bool = True
    ) -> str:
        """
        Registers an app ID (AUMID) in Windows Registry to use a custom icon 
        and name for notifications. Returns the given handle.
        https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/send-local-toast-other-apps#step-1-register-your-app-in-the-registry

        Parameters:
            handle:
                A unique ID that identifies the app in 
                "CompanyName.ProductName.SubProduct.VersionInformation" format,
                (last section, "VersionInformation" is optional)
            display_name:
                A display name for application. Shows as title in notification. 
                If not provided, same as handle.
            icon_background_color:
                Background color of icon in ARGB hex format. Default is #00000000.
            icon_uri:
                URI or file path of application icon. Shows up as icon in notification.
            show_in_settings:
                True (default) to show this application in notification settings.
        """
        if (not handle) or (len(handle) > 129) or ("\\" in handle):
            raise ValueError(
                "Invalid handle; " + (
                    "maximum allowed characters is 129." if handle 
                    else "can't be empty."
                )
            )
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, "SOFTWARE\\Classes\\AppUserModelId\\" + handle
        )
        winreg.SetValueEx(
            key, "DisplayName", 0, winreg.REG_EXPAND_SZ, 
            display_name or handle
        )
        winreg.SetValueEx(
            key, "IconBackgroundColor", 0, winreg.REG_SZ, 
            (icon_background_color or "#00000000").replace("#", "")
        )
        winreg.SetValueEx(
            key, "IconUri", 0, winreg.REG_SZ, 
            icon_uri
        )
        winreg.SetValueEx(
            key, "ShowInSettings", 0, winreg.REG_DWORD, 
            int(show_in_settings)
        )
        return handle


    @staticmethod
    def unregister_app_id(handle : str) -> None:
        """
        Unregisters an app ID in Windows Registry by deleting the associated key. 
        Unwanted system behaviours MAY happen if you unregister an another 
        application of system. It is advised to only work with handles used 
        in register_app_id()

        Parameters:
            handle:
                A unique ID that identifies the app.
        """
        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER, 
            "SOFTWARE\\Classes\\AppUserModelId\\" + handle
        )
    

    @staticmethod
    def is_registered_app_id(handle : str) -> bool:
        """
        Returns True if given app ID (AUMID) is in Windows Registry.
        Otherwise, False.

        Parameters:
            handle:
                A unique ID that identifies the app.
        """
        try:
            winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, 
                "SOFTWARE\\Classes\\AppUserModelId\\" + handle
            )
        except FileNotFoundError:
            return False
        return True


    @property
    def can_receive(self) -> bool:
        """
        Returns True if notifications for current app ID are enabled on the device. 
        Otherwise, False.
        """
        return self.can_receive_from(self.app_id)

    
    @staticmethod
    def can_receive_from(app_id: str):
        """
        Returns True if notifications for given app ID are enabled on the device. 
        Otherwise, False.
        """
        try:
            return \
                ToastNotificationManager.create_toast_notifier(app_id).setting \
                == NotificationSetting.ENABLED
        except OSError as e:
            if e.winerror == -2147023728:
                # App ID is not registered in the registry. See register_app_id().
                # TODO: maybe return a value other than False?
                return False
            raise e


    @property
    def uses_custom_sound(self) -> bool:
        """
        Returns True if the toast uses a file or a URL as a toast sound.
        """
        if self.sound and not self.sound.startswith("ms-winsoundevent:"):
            return True
        return False

    @property
    def uses_windows_sound(self) -> bool:
        """
        Returns True if the toast uses sound that comes with the Windows.
        """
        if self.sound and self.sound.startswith("ms-winsoundevent:"):
            return True
        return False


    @property
    def app_id(self) -> str: 
        return self._current_app_id or sys.executable

    @app_id.setter
    def app_id(self, value : Optional[str]) -> None:
        """
        Sets or gets the app ID for currently running Python process.
        https://learn.microsoft.com/en-us/windows/win32/shell/appids#how-to-form-an-application-defined-appusermodelid

        Parameters:
            app_id:
                An executable file path of application registered on system 
                or an AUMID in "CompanyName.ProductName.SubProduct.VersionInformation" 
                format, (last section, "VersionInformation" is optional)
        """
        if value != Toast._current_app_id:
            Toast._current_app_id = value or sys.executable
            # https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid
            # https://stackoverflow.com/a/1552105
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                value or sys.executable
            )

    @staticmethod
    def list_app_ids() -> List[Tuple[str, Optional[str], Optional[str]]]:
        """
        Get a list of all app IDs and their display name and icons 
        are reigstered for current user and system.
        """
        output = []
        for k, v in get_query_app_ids(is_user = True).items():
            output.append((k, v.get("DisplayName"), v.get("IconUri"), ))
        for k, v in get_query_app_ids(is_user = False).items():
            output.append((k, v.get("DisplayName"), v.get("IconUri"), ))
        return output

    @property
    def history(self) -> HistoryForToast:
        """
        Get History object bound for this toast.
        """
        return HistoryForToast(self)


    @staticmethod
    def get_notification_mode() -> ToastNotificationMode:
        """
        Get notification mode (alarms only, priority only or unrestricted) 
        of this device.
        """
        # Not all versions support this.
        try:
            return ToastNotificationMode(
                ToastNotificationManager.get_default().notification_mode.value
            )
        except AttributeError:
            return ToastNotificationMode.FEATURE_NOT_AVAILABLE


    @staticmethod
    def get_theme_info() -> ToastThemeInfo:
        """
        Get information about theme and language setting which is currently
        set on Windows.
        """
        color = UISettings().get_color_value(UIColorType.BACKGROUND)
        lang = locale.windows_locale[windll.kernel32.GetUserDefaultUILanguage()]
        high_contrast = AccessibilitySettings().high_contrast
        return ToastThemeInfo(
            contrast = "high" if high_contrast else "standard",
            lang = lang.lower().replace("_", "-"),
            theme = "dark" if (color.g + color.r + color.b) == 0 else "light"
        )


    def hide(self) -> None:
        """
        Dismisses this toast and stops the custom sound if currently playing. 
        """
        # If any of these properties are not set, 
        # then we are sure that toast never displayed before.
        if (not self._imp_toast) or (not self._imp_manager):
            return
        if self._fs:
            self._fs.close()
        winsound.PlaySound(None, 4)
        self._imp_manager.hide(self._imp_toast)


    def update(
        self,
        data : ToastDataType,
        missing_ok : bool = False
    ) -> bool:
        """
        Updates the notification without showing a new one. Used for changing dynamic
        values (a.k.a. binding values). You probably won't need this method if you 
        don't use any binding values. Returns True if succeded.

        Parameters:
            data:
                Dictionary of binding keys and their values to replace with.
                See also show() method to set initial values of binding keys before 
                showing the toast.
            missing_ok:
                If True, no exceptions will be raised when notification was not found 
                (e.g. user has deleted the notification). Defaults to False.
        """
        notifdata = self._build_notification_data(data)
        update_result = None
        if self.toast_id is None:
            raise ValueError(
                "Toast must have an ID to use update() function."
            )
        if self.group_id:
            update_result = self._imp_manager.update(
                notifdata, self.toast_id, self.group_id
            ).value
        else:
            update_result = self._imp_manager.update(notifdata, self.toast_id).value
        if update_result != 0:
            if not missing_ok:
                raise Exception(
                    "Failed to update the notification; " + (
                        "notification has not found." if update_result == 2 else
                        f"unknown error code: {update_result}"
                    )
                )
        return update_result == 0


    async def show(
        self,
        data : Optional[ToastDataType] = None,
        mute_sound : bool = False
    ) -> Optional[ToastResult]:
        """
        Shows the notification. If there is any {binding} key, you can give a "data" 
        dictionary to replace binding keys with their values. You can also 
        "mute_sound" to mute notification sound regardless of "sound" attribute 
        of this toast. 

        Parameters:
            data:
                Dictionary of binding keys and their initial values to replace with.
                See also update() method to update binding keys after showing the toast.
            mute_sound:
                Mute the sound of this notification, if set before. Useful if you 
                want to show same toast but want to mute sound to prevent repetitive 
                notification sounds without needing to change Toast.sound attribute for
                each time.
        """
        event_loop, futures, tokens = self._set_toast_manager(mute_sound, data)
        self._imp_manager.show(self._imp_toast)
        # If sound is custom, play with winsound.
        if self.uses_custom_sound:
            if mute_sound:
                winsound.PlaySound(None, 4)
            else:
                winsound.PlaySound(
                    str(Path(str(self.sound)).resolve()),
                    winsound.SND_FILENAME + winsound.SND_NODEFAULT + \
                    winsound.SND_ASYNC + \
                    (winsound.SND_LOOP if self.sound_loop else 0)
                )
        # Execute show handler.
        if self._callback_show:
            if inspect.iscoroutinefunction(self._callback_show):
                await self._callback_show(data)
            else:
                event_loop.call_soon_threadsafe(
                    self._callback_show, data
                )
        try:
            done, pending = await asyncio.wait(
                futures, return_when = asyncio.FIRST_COMPLETED
            )
            for p in pending:
                p.cancel()
            for d in done:
                return d.result()
        except asyncio.CancelledError:
            self.hide()
        finally:
            for i, t in enumerate(tokens):
                if i == 0:
                    self._imp_toast.remove_activated(t)
                elif i == 1:
                    self._imp_toast.remove_dismissed(t)
                elif i == 2:
                    self._imp_toast.remove_failed(t)
            

    # --------------------
    # Private
    # --------------------

    def _create_future_toast_event(
        self,
        loop : asyncio.AbstractEventLoop, 
        method_name : str, 
        hook_name : str
    ) -> Tuple[asyncio.Future, "EventRegistrationToken"]:
        future = loop.create_future()
        token : EventRegistrationToken = getattr(self._imp_toast, hook_name)(
            lambda sender, event_args: \
            loop.call_soon_threadsafe(
                future.set_result, getattr(self, method_name)(sender, event_args)
            )
        )
        return future, token,


    def _set_toast_manager(
        self,
        mute_sound : bool = False,
        data : Optional[ToastDataType] = None
    ) -> Tuple[
        asyncio.AbstractEventLoop, 
        Set[asyncio.Future], 
        List["EventRegistrationToken"]
    ]:
        self._imp_manager = ToastNotificationManager.create_toast_notifier(self.app_id)
        event_loop = asyncio.get_running_loop()
        self._xml_mute_sound = mute_sound
        xml = dom.XmlDocument()
        xml.load_xml(self._to_xml(True))
        self._imp_toast = ToastNotification(xml)
        if data:
            self._imp_toast.data = self._build_notification_data(data)
        if self.group_id:
            # TODO: Toast groups doesn't seem to supported on Windows 11.
            if get_windows_build() >= 22000:
                self._imp_toast.group = self.group_id
        if self.toast_id:
            self._imp_toast.tag = self.toast_id
        self._imp_toast.suppress_popup = not self.show_popup
        self._imp_toast.expiration_time = self.expiration_time
        # Create handlers.
        futures = set()
        tokens: List[EventRegistrationToken] = []
        for k, v in (
            ("add_activated", "_handle_toast_activated"),
            ("add_dismissed", "_handle_toast_dismissed"),
            ("add_failed", "_handle_toast_failed")
        ):
            fut, token_obj = self._create_future_toast_event(
                loop = event_loop, method_name = v, hook_name = k
            )
            futures.add(fut)
            tokens.append(token_obj)
        return event_loop, futures, tokens,


    def _handle_toast_activated(
        self, 
        toast : "ToastNotification", 
        args : "Object"
    ):
        if self._fs:
            self._fs.close()
        eventargs = ToastActivatedEventArgs._from(args)
        inputs = {}
        if eventargs.user_input:
            for x, y in eventargs.user_input.items():
                inputs[x] = IPropertyValue._from(y).get_string()
        result = ToastResult(
            arguments = eventargs.arguments,
            inputs = inputs,
            show_data = {} if not toast.data else dict(toast.data.values.items()),
            dismiss_reason = ToastDismissReason.NOT_DISMISSED
        )
        if self._callback_result:
            self._callback_result(result)
        return result


    def _handle_toast_dismissed(
        self, 
        toast : "ToastNotification", 
        args : "ToastDismissedEventArgs"
    ):
        if self._fs:
            self._fs.close()
        winsound.PlaySound(None, 4)
        result = ToastResult(
            arguments = "", 
            inputs = {},
            show_data = {} if not toast.data else dict(toast.data.values.items()), 
            dismiss_reason = ToastDismissReason(args.reason.value)
        )
        if self._callback_result:
            self._callback_result(result)
        return result


    def _handle_toast_failed(
        self, 
        toast : "ToastNotification",
        args : "ToastFailedEventArgs"
    ):
        if self._fs:
            self._fs.close()
        winsound.PlaySound(None, 4)
        raise RuntimeError(
            "Toast failed with error code: " + args.error_code.value
        )


    @staticmethod
    def _build_notification_data(
        data : dict
    ) -> "NotificationData":
        x = NotificationData()
        for k, v in data.items():
            x.values[str(k)] = str(v)
        return x

    @staticmethod
    def elements_from_json(
        elements : List[ToastElementListItemJSON]
    ):
        for i in elements:
            if isinstance(i, list):
                for j in i:
                    for k in j:
                        yield ToastElement._create_from_type(**k)
            else:
                yield ToastElement._create_from_type(**i)

    # --------------------
    # Misc
    # --------------------

    @classmethod
    def from_json(
        cls,
        json : Dict[str, Any]
    ):
        """
        Create a new Toast from a dictionary (JSON types only)

        Parameters:
            json:
                Dictionary for toast data. Use "elements" key to define toast elements.
                Element types are defined with "_type" key.
        """
        toast = cls(
            duration = None if not json.get("duration") else ToastDuration(json["duration"]),
            arguments = json.get("arguments", None),
            scenario = None if not json.get("scenario") else ToastScenario(json["scenario"]),
            group_id = str(json.get("group_id", "")) or None,
            toast_id = str(json.get("toast_id", "")) or None,
            show_popup = bool(json.get("show_popup", True)),
            base_path = str(json.get("base_path", "")) or None,
            timestamp = None if "timestamp" not in json else \
                datetime.fromisoformat(json["timestamp"]),
            sound = json.get("sound", ToastSound.DEFAULT),
            sound_loop = bool(json.get("sound_loop", False)),
            remote_media = bool(json.get("remote_media", True)),
            add_query_params = bool(json.get("add_query_params", False)),
            expiration_time = None if "expiration_time" not in json else \
                datetime.fromisoformat(json["expiration_time"]),
            app_id = str(json.get("app_id", "")) or None
        )
        toast.elements.extend(cls.elements_from_json(json["elements"]))
        return toast


    def copy(self):
        return self.__copy__()


    def __repr__(self) -> str:
        return (
            "<{class_name} id={toast_id} "
            "group={group_id} elements={elements}>"
        ).format(
            class_name = self.__class__.__name__,
            toast_id = self.toast_id,
            group_id = self.group_id,
            elements = len(self.elements)
        )

    def __del__(self):
        if hasattr(self, "_fs"):
            if self._fs:
                self._fs.close()

    def __copy__(self) -> "Toast":
        x = Toast()
        for i in self.__slots__:
            if i in self._exclude_copy:
                continue
            setattr(x, i, getattr(self, i))
        return x
