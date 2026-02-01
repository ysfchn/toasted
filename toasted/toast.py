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

from uuid import uuid4

from httpx import ConnectError, ConnectTimeout
from toasted.common import (
    ToastElement,
    ToastState,
    ToastThemeInfo,
    URIResultIcon,
    URIResultType,
    get_icon_font_default,
    get_icon_from_font,
    get_query_app_ids,
    get_windows_build,
    resolve_uri,
    _ToastContextState,
    rgb_to_hex,
    wrap_callback
)
from toasted.elements import Button, Image, Text
from toasted.filesystem import ToastMediaFileSystem
from toasted.history import HistoryForToast
from toasted.enums import (
    ToastDuration, 
    ToastScenario, 
    ToastSound, 
    _ToastElementType,
    _ToastMediaProps,
    ToastNotificationMode, 
    ToastDismissReason,
    ToastUpdateResult,
    ToastNotificationSetting
)

import asyncio
from datetime import datetime
import locale
import sys
from typing import (
    Any, Callable, Coroutine, Dict, Optional, Tuple, 
    List, Union, cast, TYPE_CHECKING
)
from pathlib import Path
from xml.etree import ElementTree as ET

import winreg
import winsound
from ctypes import windll

from winrt.windows.foundation import IPropertyValue
from winrt.windows.ui.viewmanagement import (
    AccessibilitySettings, 
    UISettings, 
    UIColorType
)
import winrt.windows.data.xml.dom as dom
from winrt.windows.ui.notifications import (
    ToastNotificationManager,
    ToastActivatedEventArgs,
    NotificationData,
    ToastNotification
)

if TYPE_CHECKING:
    from winrt.windows.ui.notifications import (
        ToastNotifier,
        ToastNotificationHistory,
        ToastDismissedEventArgs, 
        ToastFailedEventArgs
    )
    from winrt.system import Object

ToastResultCallbackType = Optional[Callable[[ToastState], Optional[Coroutine]]]
ToastShowCallbackType = Optional[Callable[[Optional[Dict[str, str]]], Optional[Coroutine]]]

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
        "_sentinel",
        "_callback_result",
        "_callback_show",
        "_imp_manager",
        "_imp_toast",
        "_imp_history",
        "_xml_mute_sound",
        "_fs",
        "_state",
        "_state_queue",
        "_state_done",
        "_fut_completed",
        "_fut_failed",
        "_fut_dismissed"
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
        sound : Union[None, str, ToastSound] = ToastSound.DEFAULT,
        sound_loop : Optional[bool] = None,
        remote_media : bool = True,
        add_query_params : bool = False,
        expiration_time : Optional[datetime] = None,
        app_id : Optional[str] = None,
        contact_info : Optional[str] = None
    ) -> None:
        super().__init__()
        self.elements : List[Union[ToastElement, List[List[Union[Image, Text]]]]] = list()
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
        self._sentinel : Optional[str] = None
        self._callback_result : ToastResultCallbackType = None
        self._callback_show : ToastShowCallbackType = None
        self._imp_manager : Optional["ToastNotifier"] = None
        self._imp_toast : Optional["ToastNotification"] = None
        self._imp_history : Optional["ToastNotificationHistory"] = None
        self._xml_mute_sound : bool = False
        self._fs : Optional[ToastMediaFileSystem] = None
        self._state : Optional[ToastState] = None
        self._state_queue : Optional[asyncio.Queue] = None
        self._state_done : Optional[asyncio.Event] = None
        self._fut_completed : Optional[asyncio.Future[_ToastContextState]] = None
        self._fut_dismissed : Optional[asyncio.Future[_ToastContextState]] = None
        self._fut_failed : Optional[asyncio.Future[_ToastContextState]] = None


    def on_state(self, function : ToastResultCallbackType = None):
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
        root.attrib["launch"] = self.arguments or ""
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

        theme_info = self.get_theme_info()

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
                        for arg in child._uri_holder():
                            el.attrib[arg.attribute] = self._resolve_uri(el.attrib[arg.attribute], allow_fs, theme_info, self.add_query_params, arg)
                        sgroup.append(el)
                    group.append(sgroup)
                binding.append(group)
            else:
                assert isinstance(item, ToastElement), "Toasts must contain of ToastElement objects."
                el = item._to_xml()
                is_spritesheet = False

                # Resolve URIs found in the element.
                for arg in item._uri_holder():
                    if arg.is_sprite:
                        assert self.contact_info, "My People notifications require a contact info to be set with Toast.contact_info, otherwise remove the sprite from the image."
                        is_spritesheet = True
                    el.attrib[arg.attribute] = self._resolve_uri(el.attrib[arg.attribute], allow_fs, theme_info, self.add_query_params, arg)
                if item._etype == _ToastElementType.ACTION:
                    actions.append(el)
                elif item._etype == _ToastElementType.HEADER:
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

        # Windows doesn't allow providing custom audio from the file system, so we
        # silent the audio unless if it is a builtin audio name.
        audio = ET.Element("audio")
        custom_audio_path = None

        if self.sound is not None:
            audio_src = str(self.sound)
            resolved_audio = self._resolve_uri(audio_src, allow_fs, theme_info, self.add_query_params)
            audio.attrib["src"] = resolved_audio
            if not resolved_audio.startswith("ms-winsoundevent:"):
                custom_audio_path = resolved_audio

        if self._xml_mute_sound or custom_audio_path:
            audio.attrib["silent"] = "true"

        if self.sound_loop is not None:
            audio.attrib["loop"] = "true" if self.sound_loop else "false"
        
        root.append(audio)
        return root, custom_audio_path


    def _create_icon(self, icon_data: URIResultIcon, theme_info: ToastThemeInfo, default_props: _ToastMediaProps):
        font_file = None
        if (not icon_data.font_file) or (icon_data.font_file == "mdl2" or icon_data.font_file == "fluent"):
            font_file = get_icon_font_default(icon_data.font_file or None)
            if font_file:
                font_file = str(font_file)
        else:
            font_file = icon_data.font_file
        if not font_file:
            raise ValueError("Couldn't find a suitable icon font, pick another font or remove for using system fonts.")
        return get_icon_from_font(
            charcode = icon_data.charcode,
            font_file = font_file,
            icon_size = icon_data.size or default_props.icon_size,
            icon_padding = icon_data.padding or default_props.icon_padding,
            background = icon_data.background or ("ffffff00" if default_props.icon_padding == 0 else rgb_to_hex(theme_info.color_accent)),
            foreground = icon_data.foreground or "ffffffff" # rgb_to_hex(theme_info.color_light)
        )


    def _resolve_uri(self, uri: str, allow_fs: bool, theme_info: ToastThemeInfo, add_params_to_remote: bool, icon_props: Optional[_ToastMediaProps] = None):
        resolved = resolve_uri(uri, theme_info)
        if resolved.type == URIResultType.INLINE:
            if allow_fs:
                if not self._fs:
                    self._fs = ToastMediaFileSystem()
                return self._fs.put(bytes.fromhex(resolved.value))
        elif resolved.type == URIResultType.ICON:
            assert icon_props, "Icon property object is required"
            if allow_fs:
                if not self._fs:
                    self._fs = ToastMediaFileSystem()
                icon_image = self._create_icon(URIResultIcon.from_value(resolved.value), theme_info, icon_props)
                return self._fs.put(icon_image)
        elif resolved.type == URIResultType.REMOTE:
            if allow_fs:
                if not self.remote_media:
                    raise ValueError(f"Downloading from remote URI '{resolved.value}' was disallowed by `Toast.remote_media` property.")
                if not self._fs:
                    self._fs = ToastMediaFileSystem()
                try:
                    return self._fs.get(
                        url = resolved.value,
                        query_params = theme_info.to_query() if add_params_to_remote else None
                    )
                except (ConnectError, ConnectTimeout):
                    # If can't connect to internet, use a placeholder "no connection" icon.
                    return self._resolve_uri("icon://U+F384", allow_fs, theme_info, True, icon_props)
        else:
            return resolved.value
        return uri


    def to_xml_string(
        self,
        download_media: bool = False
    ) -> str:
        xml, _audio = self._to_xml(download_media)
        return ET.tostring(xml, encoding = "unicode")


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
            setting = ToastNotificationSetting(ToastNotificationManager.create_toast_notifier(app_id).setting.value)
            return setting == ToastNotificationSetting.ENABLED
        except OSError as e:
            if e.winerror == -2147023728:
                # App ID is not registered in the registry. See register_app_id().
                # TODO: maybe return a value other than False?
                return False
            raise e

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
    def get_theme_info():
        """
        Get information about theme and language setting which is currently
        set on Windows.
        """
        return Toast._get_windows_theme()

    
    @property
    def state(self):
        return self._state


    def hide(self):
        """
        Dismisses the currently showing toast and stops the custom sound if currently playing.

        It will return an awaitable task that gets finished when notification gets dismissed.
        While it is also possible to call this method without an `await`, it is not guarnateed
        that the `Toast.state` will be updated right after this method unless you invoke this
        method with `await`.

        If there isn't a toast shown before, await result will be None. Otherwise, it will be
        the `Toast.state` that reflects the current state of the now hidden toast.
        """
        return asyncio.create_task(self._hide_toast())


    def update(
        self,
        data: Dict[str, Any],
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
                (e.g. user has deleted the notification) and will return False instead.
        """
        result = self._update_toast(data)
        if result == ToastUpdateResult.NOTIFICATION_NOT_FOUND:
            if missing_ok:
                return False
            raise Exception("Toast no longer exists.")
        return result == ToastUpdateResult.SUCCEEDED


    def show(
        self,
        data: Optional[Dict[str, Any]] = None,
        mute_sound : bool = False
    ):
        """
        Shows the notification.

        It will return an awaitable task that will block until the toast gets removed
        (same as `toast.show()` and `await toast.wait()` run together). If you don't
        want to block, call this method without `await`.
        
        The current state of toast is always available in `Toast.state` property regardless
        of it is called with or without `await`.
        
        If there is any templating key set, you can give a `data` dictionary to replace
        binding keys with their values. You can also `mute_sound` to mute notification
        sound regardless of `sound` attribute currently set on this toast.

        Parameters:
            data:
                Key/value mapping of binding keys and their initial values to replace with.
                Values must be a string, otherwise they will be cast into string anyways.
                See also `update()` method to update binding keys after showing the toast.
            mute_sound:
                Mute the sound of this notification without replacing existing sound,
                if any. Useful if you want to show same toast but want to override to
                mute the sound for once to prevent repetitive notification sounds.
        """
        loop = asyncio.get_running_loop()
        custom_audio = self._init_toast(loop, mute_sound, data)
        return asyncio.create_task(self._show_toast(data, custom_audio))


    async def wait(self):
        """
        Waits until notification gets completely removed and is no longer usable.
        (e.g. cleared from Action Center, clicked or removed with `hide()`)
        """
        if (not self._state_done) or (self._state is None):
            raise Exception(
                "Toast needs to be shown first to be waited."
            )
        await self._state_done.wait()
        return self._state

    
    async def _show_toast(
        self,
        data : Optional[Dict[str, str]],
        custom_audio : Optional[str]
    ):
        loop = asyncio.get_running_loop()

        assert self._imp_manager and self._imp_toast and self._state_done, "Not initialized"
        assert self._state_queue and (self._state is not None), "Invalid state"
        self._imp_manager.show(self._imp_toast)

        self._play_sound(custom_audio, self.sound_loop or False)

        if self._callback_show:
            wrapped_show = wrap_callback(self._callback_show)
            if wrapped_show:
                loop.create_task(wrapped_show(data))

        wrapped_result = wrap_callback(self._callback_result)

        while not self._state._cleared:
            state = await self._state_queue.get()
            if wrapped_result:
                loop.create_task(wrapped_result(state))
            self._state_queue.task_done()
        
        self._state_done.set()
        return self._state


    async def _hide_toast(self):
        # If any of these properties are not set, then assume that toast never displayed before.
        if (not self._imp_toast) or (not self._imp_manager):
            return
        
        if self._fs:
            self._fs.close()
        self._play_sound(None)

        assert self._state_queue and (self._state is not None), "Invalid state"
        self._imp_manager.hide(self._imp_toast)


    def _update_toast(
        self,
        binding_data: Dict[str, Any]
    ):
        assert self._imp_toast and self._imp_manager, "Not initialized"

        notif_data = NotificationData()
        for k, v in binding_data.items():
            notif_data.values[k] = str(v)
        self._imp_toast.data = notif_data

        update_result = None
        if self.toast_id is None:
            raise ValueError(
                "Toast must have an ID to use update() function."
            )
        if self.group_id:
            update_result = self._imp_manager.update(notif_data, self.toast_id, self.group_id)
        else:
            update_result = self._imp_manager.update(notif_data, self.toast_id)
        return ToastUpdateResult(update_result.value)


    def _init_toast(
        self,
        loop: asyncio.AbstractEventLoop,
        mute_sound: bool = False,
        binding_data: Optional[Dict[str, str]] = None,
    ):
        self._imp_manager = ToastNotificationManager.create_toast_notifier(self.app_id)
        self._xml_mute_sound = mute_sound
        xml, audio = self._to_xml(True)
        winxml = dom.XmlDocument()
        winxml.load_xml(ET.tostring(xml, encoding = "unicode"))
        self._imp_toast = ToastNotification(winxml)

        assert self._imp_toast and self._imp_manager, "Not initialized"

        notif_data = NotificationData()
        if binding_data:
            for k, v in binding_data.items():
                notif_data.values[k] = str(v)

        # Create an temporary ID to track if it is the same toast with the one that returned when getting all toasts.
        self._sentinel = str(uuid4())
        notif_data.values["__sentinel__"] = self._sentinel
        self._imp_toast.data = notif_data

        if self.group_id:
            # Toast groups doesn't seem to supported on Windows 11.
            if get_windows_build() >= 22000:
                self._imp_toast.group = self.group_id

        if self.toast_id:
            self._imp_toast.tag = self.toast_id

        self._imp_toast.suppress_popup = not self.show_popup
        self._imp_toast.expiration_time = self.expiration_time

        self._imp_history = ToastNotificationManager.get_default().history

        # Fullfill Future objects when Windows API event handlers gets invoked.

        self._state = ToastState()
        self._state_queue = asyncio.Queue()
        self._state_done = asyncio.Event()

        self._fut_completed = loop.create_future()
        self._fut_dismissed = loop.create_future()
        self._fut_failed = loop.create_future()

        tok_activated = None
        tok_dismissed = None
        tok_failed = None

        # Each event has their own future, since more than one event can be invoked.
        # Activated is when interacted with the toast (and the toast gets deleted), and failed is when a toast
        # couldn't be shown. Then there is a dismissed event, which works ...interestingly.

        def _activated_handler(_event_target: "ToastNotification", _event_args: "Object"):
            def _safe():
                assert (self._fut_dismissed and self._fut_completed) and self._fut_failed, "Invalid state"
                if self._fut_completed.cancelled():
                    return

                # Called event args is not a ToastActivatedEventArgs object but a plain Object, so we cast to it.
                result = ToastActivatedEventArgs._from(_event_args)
                inputs = {}
                data_values = dict() if not _event_target.data else dict(_event_target.data.values.items())
                if result.user_input:
                    for x, y in result.user_input.items():
                        inputs[x] = IPropertyValue._from(y).get_string()

                self._fut_completed.set_result(_ToastContextState(
                    arguments = result.arguments,
                    params = data_values,
                    inputs = inputs,
                    reason = None,
                    code = None,
                    # Clicking a toast makes it removed.
                    cleared = True
                ))
            loop.call_soon_threadsafe(_safe)

        # When a toast first shown and user clicks to "X" button, the toast will still exist since it will be
        # moved to Action Center. And interestingly, when you clear the toast from there, it will invoke another
        # dismiss event, and there is no way to know if it is actually cleared from Action Center, or just
        # moved to there. So we rely on 2 futures for this one.

        def _dismissed_handler(_event_target: "ToastNotification", _event_args: "ToastDismissedEventArgs"):
            def _safe():
                assert self._imp_toast and self._imp_history, "Not initialized"
                assert (self._fut_dismissed and self._fut_completed) and self._fut_failed, "Invalid state"
                if self._fut_dismissed.cancelled():
                    return

                dismiss_reason = ToastDismissReason(_event_args.reason.value)
                data_values = dict() if not _event_target.data else dict(_event_target.data.values.items())

                # If a notification gets dismissed second time, this should mean it is completely removed
                # (from Action Center), if it is not, then we are in probably an invalid state.
                if self._fut_dismissed.done():
                    if self._fut_completed.cancelled():
                        return
                    self._fut_failed.cancel()
                    assert tok_dismissed and tok_activated and tok_failed, "Invalid state"
                    self._imp_toast.remove_dismissed(tok_dismissed)
                    self._imp_toast.remove_dismissed(tok_activated)
                    self._imp_toast.remove_dismissed(tok_failed)
                    self._fut_completed.set_result(_ToastContextState(
                        arguments = None,
                        reason = dismiss_reason,
                        params = data_values,
                        inputs = dict(),
                        code = None,
                        cleared = True
                    ))
                    return

                # If notification was explictly hidden with hide() method, then assume it is removed already.
                if dismiss_reason == ToastDismissReason.APPLICATION_HIDDEN:
                    assert tok_dismissed, "Invalid state"
                    self._imp_toast.remove_dismissed(tok_dismissed)

                self._fut_dismissed.set_result(_ToastContextState(
                    arguments = None,
                    reason = dismiss_reason,
                    params = data_values,
                    inputs = dict(),
                    code = None,
                    cleared = False
                ))
            loop.call_soon_threadsafe(_safe)

        def _failed_handler(_event_target: "ToastNotification", _event_args: "ToastFailedEventArgs"):
            def _safe():
                assert self._imp_toast and self._imp_history, "Not initialized"
                assert (self._fut_dismissed and self._fut_completed) and self._fut_failed, "Invalid state"
                if self._fut_failed.cancelled():
                    return

                self._fut_completed.cancel()
                self._fut_dismissed.cancel()
                assert tok_dismissed and tok_activated and tok_failed, "Invalid state"
                self._imp_toast.remove_dismissed(tok_dismissed)
                self._imp_toast.remove_dismissed(tok_activated)
                self._imp_toast.remove_dismissed(tok_failed)

                error_code = _event_args.error_code.value
                self._fut_failed.set_result(_ToastContextState(
                    arguments = None,
                    params = dict(),
                    inputs = dict(),
                    reason = None,
                    code = error_code,
                    cleared = True
                ))
            loop.call_soon_threadsafe(_safe)

        tok_activated = self._imp_toast.add_activated(_activated_handler)
        tok_dismissed = self._imp_toast.add_dismissed(_dismissed_handler)
        tok_failed = self._imp_toast.add_failed(_failed_handler)

        def _set_toast_state_handler(future: asyncio.Future[_ToastContextState]):
            if future.cancelled():
                return
            state_data = cast(_ToastContextState, future.result())
            assert self._imp_history and self._imp_toast, "Not initialized"
            assert (self._state is not None) and self._state_queue, "Invalid state"
            self._state._provided = True
            self._state._dismiss_reason = state_data.reason
            self._state._arguments = state_data.arguments
            self._state._params = state_data.params
            self._state._inputs = state_data.inputs
            self._state._cleared = True
            for toast in self._imp_history.get_history(self.app_id):
                if not toast.data:
                    continue
                if toast.data.values.get("__sentinel__") == self._sentinel:
                    self._state._cleared = state_data.cleared
                    break
            if state_data.code:
                raise Exception(
                    f"Toast failed with error code: {state_data.code}"
                )
            if self._state._cleared:
                if self._fs:
                    self._fs.close()
            self._state_queue.put_nowait(self._state)

        self._fut_completed.add_done_callback(_set_toast_state_handler)
        self._fut_dismissed.add_done_callback(_set_toast_state_handler)
        self._fut_failed.add_done_callback(_set_toast_state_handler)

        return audio


    def _play_sound(self, sound_path: Optional[str], sound_loop: bool = False):
        if sound_path:
            winsound.PlaySound(
                str(Path(sound_path).resolve()),
                winsound.SND_FILENAME + \
                winsound.SND_NODEFAULT + \
                winsound.SND_ASYNC + \
                (winsound.SND_LOOP if sound_loop else 0)
            )
        else:
            winsound.PlaySound(None, winsound.SND_MEMORY)


    @staticmethod
    def _get_windows_theme():
        ui_settings = UISettings()

        def read_color(color_type: UIColorType):
            color = ui_settings.get_color_value(color_type)
            return color.r, color.g, color.b,

        bg_color = read_color(UIColorType.BACKGROUND)
        fg_color = read_color(UIColorType.FOREGROUND)
        ac_color = read_color(UIColorType.ACCENT)

        lang = locale.windows_locale[windll.kernel32.GetUserDefaultUILanguage()]
        high_contrast = AccessibilitySettings().high_contrast

        return ToastThemeInfo(
            has_high_contrast = high_contrast,
            language_code = lang,
            color_dark = bg_color,
            color_light = fg_color,
            color_accent = ac_color
        )


    @staticmethod
    def elements_from_json(
        elements : List[Union[
            Dict[str, Any],
            List[List[Dict[str, Any]]]
        ]]
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
            add_query_params = bool(json.get("add_query_params", True)),
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
        if self._fs:
            self._fs.close()
        if self._fut_completed and not self._fut_completed.done():
            self._fut_completed.cancel()
        if self._fut_dismissed and not self._fut_dismissed.done():
            self._fut_dismissed.cancel()
        if self._fut_failed and not self._fut_failed.done():
            self._fut_failed.cancel()
        

    def __copy__(self) -> "Toast":
        toast = Toast(
            arguments = self.arguments,
            duration = self.duration,
            timestamp = self.timestamp,
            scenario = self.scenario,
            group_id = self.group_id,
            toast_id = self.toast_id,
            show_popup = self.show_popup,
            base_path = self.base_path,
            sound = self.sound,
            sound_loop = self.sound_loop,
            remote_media = self.remote_media,
            add_query_params = self.add_query_params,
            expiration_time = self.expiration_time,
            app_id = self.app_id,
            contact_info = self.contact_info
        )
        toast.elements.extend(self.elements)
        return toast
