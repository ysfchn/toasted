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
    "Text",
    "Image",
    "Progress",
    "Button",
    "Header",
    "Input",
    "Select"
]

from toasted.common import (
    ToastElement, 
    XMLData,
    get_enum
)
from toasted.enums import (
    ToastElementType, 
    ToastTextAlign, 
    ToastTextStyle, 
    ToastButtonStyle, 
    ToastImagePlacement
)
from typing import Optional, Dict, Any, Union

class Text(ToastElement, etype = ToastElementType.VISUAL, ename = "text"):
    """
    Specifies text used in the toast template.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-text

    Args:
        content:
            Content of the text element.
        id:
            The text element in the toast template that this text is intended for. 
            If a template has only one text element, then this value is 1. 
            The number of available text positions is based on the template definition.
        style:
            The style controls the text's font size, weight, and opacity. 
            Only works for text elements inside a group/subgroup.
        align:
            The horizontal alignment of the text. 
            Only works for text elements inside a group/subgroup.
        is_attribution:
            The placement of the text. Introduced in Anniversary Update. 
            If you set to True, the text is always displayed at the bottom of your 
            notification, along with your app's identity or the notification's 
            timestamp. On older versions of Windows that don't support attribution 
            text, the text will simply be displayed as another text element 
            (assuming you don't already have the maximum of three text elements). 
        is_center:
            Set to True to center the text for incoming call notifications. 
            This value is only used for notifications with with a scenario value of 
            INCOMING_CALL; otherwise, it is ignored. It seems to only works in
            Windows 11.
        max_lines:
            Gets or sets the maximum number of lines the text element is allowed 
            to display.
        min_lines:
            Gets or sets the minimum number of lines the text element must display. 
            This property will only take effect if the text is inside an subgroup.
    """
    __slots__ = (
        "content", "id", "style", "align", 
        "is_attribution", "is_center", "max_lines", 
        "min_lines", 
    )

    def __init__(
        self, 
        content : str, 
        id : Optional[int] = None,
        style : Optional[ToastTextStyle] = None,
        align : Optional[ToastTextAlign] = None, 
        is_attribution : bool = False,
        is_center : bool = False,
        max_lines : Optional[int] = None,
        min_lines : Optional[int] = None
    ) -> None:
        self.content = content
        self.id = None if id is None else int(id)
        self.is_attribution = is_attribution
        self.is_center = is_center
        self.style = style
        self.align = align
        self.max_lines = max_lines
        self.min_lines = min_lines

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        x.style = get_enum(ToastTextStyle, data.get("style", None))
        x.align = get_enum(ToastTextAlign, data.get("align", None))
        return x

    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "text", 
            content = self.content,
            attrs = {
                "id": self.id,
                "placement": "attribution" if self.is_attribution else None,
                "hint-callScenarioCenterAlign": True if self.is_center else None,
                "hint-align": self.align,
                "hint-style": self.style,
                "hint-maxLines": self.max_lines,
                "hint-minLines": self.min_lines
            }
        )


class Image(ToastElement, etype = ToastElementType.VISUAL, ename = "image"):
    """
    Specifies an image used in the toast template.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-image

    Args:
        source:
            The URI of the image source (http(s):// is supported when "remote_images" 
            has enabled on Toast objects - which is default, otherwise only file paths 
            can be used).
        id:
            The image element in the toast template that this image is intended for. 
            If a template has only one image, then this value is 1. 
            The number of available image positions is based on the template definition.
        alt:
            A description of the image, for users of assistive technologies.
        placement:
            The placement of the image.
            LOGO: The image is displayed as a logo at left,
            HERO: The image is displayed as a hero image,
            None or default value: The image is displayed inside the toast.
        is_circle:
            If True, the image is cropped into a circle.
    """
    __slots__ = ("source", "id", "alt", "placement", "is_circle", )

    def __init__(
        self, 
        source : str,
        id : Optional[int] = None,
        alt : Optional[str] = None,
        placement : Optional[ToastImagePlacement] = None,
        is_circle : bool = False
    ) -> None:
        self.source = source
        self.id = None if id is None else int(id)
        self.alt = alt
        self.placement = placement
        self.is_circle = is_circle

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        x.placement = get_enum(ToastImagePlacement, data.get("placement", None))
        return x

    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "image",
            attrs = {
                "id": self.id,
                "src": self.source,
                "alt": self.alt,
                "placement": self.placement,
                "hint-crop": "circle" if self.is_circle else None
            },
            source_replace = "src"
        )


class Progress(ToastElement, etype = ToastElementType.VISUAL, ename = "progress"):
    """
    Specifies a progress bar for a toast notification. Only supported on toasts on 
    Desktop, build 15063 or later.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-progress

    Args:
        value:
            The value of the progress bar. This value either be a float between 0 
            and 1 (inclusive) or -1 (indeterminate), which results in a 
            loading animation.
        status:
            A status string that is displayed underneath the progress bar on the left. 
            This string should reflect the status of the operation, like 
            "Downloading..." or "Installing..."
        title:
            An optional title string.
        display_value:
            An optional string to be displayed instead of the default percentage 
            string. If this isn't provided, something like "70%" will be displayed.
    """
    __slots__ = ("value", "status", "title", "display_value", )

    def __init__(
        self, 
        value : Union[str, float],
        status : Optional[str] = None,
        title : Optional[str] = None,
        display_value : Optional[str] = None
    ) -> None:
        self.value = value
        self.status = status
        self.title = title
        self.display_value = display_value

    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "progress",
            attrs = {
                "title": self.title,
                "value": "indeterminate" if (self.value == -1) else self.value,
                "status": self.status or " ",
                "valueStringOverride": self.display_value
            }
        )


class Button(ToastElement, etype = ToastElementType.ACTION, ename = "button"):
    """
    Specifies a button shown in a toast.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-action

    Args:
        content:
            The content displayed on the button.
        arguments:
            App-defined string of arguments that the app will later receive if the 
            user clicks this button.
        is_context:
            When set to True, the action becomes a context menu action added to the 
            toast notification's context menu rather than a traditional toast button.
        icon:
            The URI of the image source for a toast button icon. 
            These icons are white transparent 16x16 pixel images at 100% scaling and 
            should have no padding included in the image itself. If you choose to 
            provide icons on a toast notification, you must provide icons for ALL of 
            your buttons in the notification, as it transforms the style of your 
            buttons into icon buttons. In dark theme, the icon will show in white 
            color, otherwise, in black color. This is a Windows behaviour.
        input_id:
            Set to the ID of an input to position button beside the input.
        style:
            The button style.
        tooltip:
            The tooltip for a button, if the button has an empty content string.
        is_protocol:
            If True, launch an application or visit a link when this button 
            has clicked. To make it work, also specify a URI in "arguments" parameter.
    """
    __slots__ = (
        "content", "arguments", "is_context", "icon", 
        "input_id", "style", "tooltip", "is_protocol",
    )

    def __init__(
        self,
        content : str,
        arguments : str,
        is_context : bool = False,
        icon : Optional[str] = None,
        input_id : Optional[str] = None,
        style : Optional[ToastButtonStyle] = None,
        tooltip : Optional[str] = None,
        is_protocol : bool = False
    ) -> None:
        self.content = content
        self.arguments = arguments
        self.is_context = is_context
        self.icon = icon
        self.input_id = input_id
        self.style = style
        self.tooltip = tooltip
        self.is_protocol = is_protocol

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        x.style = get_enum(ToastButtonStyle, data.get("style", None))
        return x

    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "action",
            attrs = {
                "content": self.content,
                "arguments": self.arguments,
                "activationType": "foreground" if not self.is_protocol else "protocol", 
                "placement": "contextMenu" if self.is_context else None,
                "imageUri": self.icon,
                "hint-inputId": self.input_id,
                "hint-buttonStyle": self.style,
                "hint-toolTip": self.tooltip,
                "afterActivationBehavior": "pendingUpdate"
                # Unsupported options:
                # - protocolActivationTargetApplicationPfn
                # - afterActivationBehavior = "pendingUpdate"
                #     (activationType must be "background")
            },
            source_replace = "imageUri"
        )


class Header(ToastElement, etype = ToastElementType.HEADER, ename = "header"):
    """
    Specifies a custom header that groups multiple notifications together within 
    Action Center.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-header

    Args:
        id:
            A developer-created identifier that uniquely identifies this header. 
            If two notifications have the same header id, they will be displayed 
            underneath the same header in Action Center.
        title:
            A title for the header.
        arguments:
            A developer-defined string of arguments that is returned to the app 
            when the user clicks this header. Cannot be null.
    """
    __slots__ = ("id", "title", "arguments", )

    def __init__(
        self,
        id : str,
        title : str,
        arguments : str
    ) -> None:
        self.id = id
        self.title = title
        self.arguments = arguments
    
    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "header",
            attrs = {
                "id": self.id, 
                "title": self.title, 
                "arguments": self.arguments,
                "activationType": "foreground"
            }
        )


class Input(ToastElement, etype = ToastElementType.ACTION, ename = "input"):
    """
    Specifies an text box, shown in a toast notification.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-input

    Args:
        id:
            The ID associated with the input.
        placeholder:
            The placeholder displayed for text input.
        title:
            Text displayed as a label for the input.
        default:
            Default value shown in the input.
    """
    __slots__ = ("id", "placeholder", "title", "default", )

    def __init__(
        self,
        id : str,
        placeholder : Optional[str] = None,
        title : Optional[str] = None,
        default : Optional[str] = None
    ) -> None:
        self.id = id
        self.placeholder = placeholder
        self.title = title
        self.default = default
    
    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "input",
            attrs = {
                "type": "text",
                "id": self.id,
                "title": self.title,
                "placeHolderContent": self.placeholder,
                "defaultInput": self.default
            }
        )


class Select(ToastElement, etype = ToastElementType.ACTION, ename = "select"):
    """
    Specifies an selection menu, shown in a toast notification.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-input

    Args:
        id:
            The ID associated with the select.
        title:
            Text displayed as a label for the select.
        options:
            Key and value mappings of select items. Keys represents their IDs, and
            values represents the display text shown on the notification.
        default:
            Key of the option that will be shown as selected in the select menu.
    """
    __slots__ = ("id", "options", "title", "default", )

    def __init__(
        self,
        id : str,
        options : Dict[str, str],
        title : Optional[str] = None,
        default : Optional[str] = None
    ) -> None:
        self.id = id
        self.title = title
        self.options = options
        self.default = default

    def to_xml_data(self) -> XMLData:
        return XMLData(
            tag = "input",
            content = [
                XMLData(
                    tag = "selection",
                    attrs = {"id": x, "content": y}
                ) for x, y in self.options.items()
            ],
            attrs = {
                "type": "selection",
                "id": self.id, 
                "title": self.title,
                "defaultInput": self.default
            }
        )