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
    ToastPayload,
    ToastThemeInfo,
    get_enum,
    get_query_app_ids, 
    xml, 
    ToastResult, 
    get_windows_version, 
    resolve_uri,
    get_theme_query_parameters,
    xmldata_to_content,
    XMLData
)
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
    Any, Callable, Dict, Generator, Optional, Tuple, 
    List, Union, Literal, Set
)
from pathlib import Path

if sys.platform == "win32":
    import winreg
    import winsound
    from ctypes import windll

    from winsdk._winrt import Object # type: ignore
    from winsdk.windows.foundation import IPropertyValue, EventRegistrationToken # type: ignore
    from winsdk.windows.ui.viewmanagement import ( # type: ignore
        AccessibilitySettings, 
        UISettings, 
        UIColorType
    )
    import winsdk.windows.data.xml.dom as dom # type: ignore
    from winsdk.windows.ui.notifications import ( # type: ignore
        ToastNotification, 
        ToastNotificationManager, 
        ToastActivatedEventArgs, 
        ToastDismissedEventArgs, 
        ToastFailedEventArgs,
        ToastNotifier,
        NotificationSetting,
        NotificationData
    )

ToastDataType = Dict[str, str]
ToastResultCallbackType = Optional[Callable[[ToastResult], None]]
ToastShowCallbackType = Optional[Callable[[Optional[ToastDataType]], None]]

ToastElementTreeType = Union[ToastElement, List["ToastElementTreeType"]]
ToastElementsListType = List[ToastElementTreeType]

ToastElementTreeJSONType = Union[Dict[str, Any], List["ToastElementTreeJSONType"]]
ToastElementsListJSONType = List[ToastElementTreeJSONType]

LEVEL_START = "LEVEL_START"
LEVEL_END = "LEVEL_END"

ToastElementWalkLevelType = Literal["LEVEL_START", "LEVEL_END"]

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
            URGENT: An important notification. This allows users to have more control 
                over what apps can send them high-priority toast notifications that can 
                break through Focus Assist (Do not Disturb). This can be modified in 
                the notifications settings.
        group_id:
            Group ID that this toast belongs in. Used for deleting a notification 
            from Action Center.
        toast_id:
            ID of the toast. Used for deleting a notification from Action Center.
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
            Windows requires an ID of installed application in the computer to show 
            notifications from. This also sets the icon and name of the given 
            application in the toast title. Defaults to executable path of Python
            (sys.executable), so notification will show up as "Python". However, this 
            will not work for embedded versions of Python since Python is not installed 
            on system, so you will need to change this. You can also register 
            an ID in system to use a custom name and icon. 
            See `Toast.register_app_id()`.
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
        app_id : Optional[str] = None
    ) -> None:
        super().__init__()
        self.elements : ToastElementsListType = []
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


    def get_payload(
        self,
        download_media : bool = False
    ) -> ToastPayload:
        """
        Walk elements and convert them to XML recursively.
        """
        params = None if not self.add_query_params else get_theme_query_parameters(
            info = self.get_theme_info()
        )
        visual, actions, other = ("", ) * 3
        current_level = 0
        using_custom_style : bool = False
        if download_media:
            if self._fs:
                self._fs.close()
            self._fs = ToastMediaFileSystem()
        for el in self._walk_elements(self.elements):
            if el in [LEVEL_START, LEVEL_END]:
                is_end = el == LEVEL_END
                if not is_end:
                    current_level += 1
                if current_level > 2:
                    raise ValueError(
                        "Toasts doesn't support nested elements other " +
                        "than groups and subgroups."
                    )
                elif current_level == 1:
                    visual += f"<{'/' if is_end else ''}group>"
                elif current_level == 2:
                    visual += f"<{'/' if is_end else ''}subgroup>"
                if is_end:
                    current_level -= 1
            else:
                xmldata = el.to_xml_data()
                xmlcontent = ""
                override = ""
                if xmldata.source_replace:
                    source_uri = xmldata.attrs[xmldata.source_replace]
                    if source_uri:
                        resolved = resolve_uri(source_uri, self.remote_media)
                        if isinstance(resolved, bytes):
                            if download_media:
                                override = self._fs.put(resolved)
                        elif isinstance(resolved, str):
                            if download_media:
                                override = self._fs.get_or_download(
                                    url = resolved,
                                    query_params = params
                                )
                        else:
                            override = resolved.as_uri()
                    for c in xmldata_to_content(XMLData(
                        tag = xmldata.tag,
                        content = xmlcontent,
                        attrs = {
                            **(xmldata.attrs or {}), 
                            xmldata.source_replace : override or None
                        }
                    )):
                        xmlcontent += c or ""
                else:
                    for c in xmldata_to_content(xmldata):
                        xmlcontent += c or ""
                if el._etype == ToastElementType.ACTION:
                    actions += xmlcontent
                elif el._etype == ToastElementType.VISUAL:
                    visual += xmlcontent
                else:
                    other += xmlcontent
                # Enable custom styles on the toast
                # if button has a custom style.
                if xmldata.attrs.get("hint-buttonStyle", None):
                    using_custom_style = True
        other += xml(
            "audio", 
            src = self.sound if self.uses_windows_sound else None,
            # If custom sound has provided, mute the original 
            # toast sound to None since we use our own sound solution.
            silent = self._xml_mute_sound or self.uses_custom_sound,
            loop = self.sound_loop
        )
        custom_sound_file : str = ""
        if self.uses_custom_sound:
            resolved = resolve_uri(self.sound, self.remote_media)
            if isinstance(resolved, bytes):
                if download_media:
                    custom_sound_file = self._fs.put(resolved)
            elif isinstance(resolved, str):
                if download_media:
                    custom_sound_file = self._fs.get_or_download(
                        url = resolved,
                        query_params = params
                    )
            else:
                custom_sound_file = resolved.as_uri()
        return ToastPayload(
            uses_custom_style = using_custom_style or None,
            custom_sound_file = custom_sound_file,
            base_path = self.base_path or resolve_uri("ms-appx://").as_uri(),
            arguments = self.arguments,
            duration = None if not self.duration else self.duration.value,
            scenario = None if not self.scenario else self.scenario.value,
            timestamp = (None if not self.timestamp else self.timestamp.isoformat()),
            visual_xml = visual,
            actions_xml = actions,
            other_xml = other
        )


    @staticmethod
    def _payload_to_xml_string(payload : ToastPayload):
        return xml("toast",
                xml("visual", 
                    xml("binding", payload.visual_xml, template = "ToastGeneric"),
                    baseUri = payload.base_path
                ) + (
                    "" if not payload.actions_xml else \
                    xml("actions", payload.actions_xml)
                ) + \
            payload.other_xml,
            launch = payload.arguments,
            duration = payload.duration,
            scenario = payload.scenario,
            displayTimestamp = payload.timestamp,
            useButtonStyle = payload.uses_custom_style
        )


    def to_xml_string(
        self,
        download_media : bool = False
    ) -> str:
        return self._payload_to_xml_string(
            self.get_payload(download_media)
        )


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
    def can_send_from_app_id(self) -> bool:
        """
        Returns True if notifications (for current app ID) are enabled on the device. 
        Otherwise, False.
        """
        try:
            return \
                ToastNotificationManager.create_toast_notifier(self.app_id).setting \
                == NotificationSetting.ENABLED
        except OSError as e:
            if e.winerror == -2147023728:
                # App ID is not registered in the registry.
                # See register_app_id().
                # TODO: maybe return a value other than False?
                return False


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
    ) -> ToastResult:
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
        event_loop, futures, tokens, custom_sound = self._set_toast_manager(
            mute_sound, data
        )
        self._imp_manager.show(self._imp_toast)
        # If sound is custom, play with winsound.
        if custom_sound:
            if mute_sound:
                winsound.PlaySound(None, 4)
            else:
                winsound.PlaySound(
                    Path(custom_sound).resolve().as_posix(), 
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
        done, pending = await asyncio.wait(
            futures, return_when = asyncio.FIRST_COMPLETED
        )
        for p in pending:
            p.cancel()
        for i, t in enumerate(tokens):
            if i == 0:
                self._imp_toast.remove_activated(t)
            elif i == 1:
                self._imp_toast.remove_dismissed(t)
            elif i == 2:
                self._imp_toast.remove_failed(t)
        for d in done:
            return d.result()

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
        Set["EventRegistrationToken"],
        str
    ]:
        self._imp_manager = ToastNotificationManager.create_toast_notifier(self.app_id)
        event_loop = asyncio.get_running_loop()
        self._xml_mute_sound = mute_sound
        xml = dom.XmlDocument()
        payload = self.get_payload(download_media = True)
        xml.load_xml(self._payload_to_xml_string(payload))
        self._imp_toast = ToastNotification(xml)
        if data:
            self._imp_toast.data = self._build_notification_data(data)
        if self.group_id:
            release, _ = get_windows_version()
            # TODO: Looks like groups doesn't work in Windows 11.
            if release != 11:
                self._imp_toast.group = self.group_id
        if self.toast_id:
            self._imp_toast.tag = self.toast_id
        self._imp_toast.suppress_popup = not self.show_popup
        self._imp_toast.expiration_time = self.expiration_time
        # Create handlers.
        futures = set()
        tokens = set()
        for k, v in (
            ("add_activated", "_handle_toast_activated"),
            ("add_dismissed", "_handle_toast_dismissed"),
            ("add_failed", "_handle_toast_failed")
        ):
            fut, tok = self._create_future_toast_event(
                loop = event_loop, method_name = v, hook_name = k
            )
            futures.add(fut)
            tokens.add(tok)
        return event_loop, futures, tokens, payload.custom_sound_file,


    def _handle_toast_activated(
        self, 
        toast : "ToastNotification", 
        args : "Object"
    ):
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
    def _walk_elements(
        elements : ToastElementsListType,
    ) -> Generator[Union[ToastElement, ToastElementWalkLevelType], None, None]:
        for i in elements:
            if isinstance(i, list):
                yield LEVEL_START
                for j in Toast._walk_elements(i):
                    yield j
                yield LEVEL_END
            elif not isinstance(i, ToastElement):
                raise TypeError(
                    f"Item must be a type of ToastElement: '{repr(i)}'"
                )
            else:
                yield i
    

    @staticmethod
    def elements_from_json(
        elements : ToastElementsListJSONType
    ):
        for i in elements:
            if isinstance(i, list):
                for j in Toast.elements_from_json(i):
                    yield j
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
            duration = get_enum(ToastDuration, json.get("duration", None)),
            arguments = json.get("arguments", None),
            scenario = get_enum(ToastScenario, json.get("scenario", None)),
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
        if self._fs:
            self._fs.close()

    def __copy__(self) -> "Toast":
        x = Toast()
        for i in self.__slots__:
            if i in self._exclude_copy:
                continue
            setattr(x, i, getattr(self, i))
        return x