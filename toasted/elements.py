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

from toasted.common import ToastElement
from toasted.enums import (
    _ToastXMLTag,
    _ToastElementType, 
    ToastTextAlign, 
    ToastTextStyle, 
    ToastButtonStyle, 
    ToastImagePlacement
)
from typing import Optional, Dict, Any, Union
from xml.etree import ElementTree as ET

class Text(ToastElement, slot = _ToastElementType.VISUAL, tag = _ToastXMLTag.TEXT):
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
        is_wrap:
            If text should be wrapped.
    """
    __slots__ = (
        "content",
        "id",
        "style",
        "align",
        "is_attribution",
        "is_center",
        "max_lines",
        "min_lines"
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
        min_lines : Optional[int] = None,
        is_wrap : bool = False
    ) -> None:
        self.content = content
        self.id = None if id is None else int(id)
        self.is_attribution = is_attribution
        self.is_center = is_center
        self.style = style
        self.align = align
        self.max_lines = max_lines
        self.min_lines = min_lines
        self.is_wrap = is_wrap

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        if data.get("style"):
            x.style = ToastTextStyle(data["style"])
        if data.get("align"):
            x.align = ToastTextAlign(data["align"])
        return x

    def _to_xml(self):
        el = ET.Element(self._xmltag())
        el.text = self.content
        if self.id:
            el.attrib["id"] = str(self.id)
        if self.is_attribution:
            el.attrib["placement"] = "attribution"
        if self.is_center:
            el.attrib["hint-callScenarioCenterAlign"] = "true"
        if self.align:
            el.attrib["hint-align"] = self.align.value
        if self.style:
            el.attrib["hint-style"] = self.style.value
        if self.max_lines:
            el.attrib["hint-maxLines"] = str(self.max_lines)
        if self.min_lines:
            el.attrib["hint-minLines"] = str(self.min_lines)
        if self.is_wrap:
            el.attrib["hint-wrap"] = "true"
        return el


class Image(ToastElement, slot = _ToastElementType.VISUAL, tag = _ToastXMLTag.IMAGE, uri_keys = ("src", "spritesheet-src")):
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
        sprite_source:
            Shouldn't be used. Was in use for unsupported [My People](https://learn.microsoft.com/en-us/windows/uwp/contacts-and-calendar/my-people-notifications) notifications.
            This won't work in Windows 11 and Windows 10 versions with KB5034203 update. sprite_* properties
            are only implemented here as a reference.
        sprite_height:
            Shouldn't be used. Frame height for each sprite. Only required for spritesheet animations.
        sprite_fps:
            Shouldn't be used. Frames per second (FPS), maximum 120. Only required for spritesheet animations.
        sprite_index:
            Shouldn't be used. Starting frame index of the sprite. Only required for spritesheet animations.
    """
    __slots__ = (
        "source",
        "id",
        "alt",
        "placement",
        "is_circle",
        "sprite_source",
        "sprite_height",
        "sprite_fps",
        "sprite_index"
    )

    def __init__(
        self, 
        source : str,
        id : Optional[int] = None,
        alt : Optional[str] = None,
        placement : Optional[ToastImagePlacement] = None,
        is_circle : bool = False,
        sprite_source : Optional[str] = None,
        sprite_height : Optional[int] = None,
        sprite_fps : Optional[int] = None,
        sprite_index : Optional[int] = None
    ) -> None:
        self.source = source
        self.id = None if id is None else int(id)
        self.alt = alt
        self.placement = placement
        self.is_circle = is_circle
        self.sprite_source = sprite_source
        self.sprite_height = sprite_height
        self.sprite_fps = sprite_fps
        self.sprite_index = sprite_index

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        if data.get("placement"):
            x.placement = ToastImagePlacement(data["placement"])
        return x

    def _to_xml(self):
        el = ET.Element(self._xmltag())
        if self.id:
            el.attrib["id"] = str(self.id)
        el.attrib["src"] = self.source
        if self.alt:
            el.attrib["alt"] = self.alt
        if self.placement:
            el.attrib["placement"] = self.placement.value
        if self.is_circle:
            el.attrib["hint-crop"] = "circle"
        if self.sprite_source:
            assert self.sprite_fps and self.sprite_index and self.sprite_height, "All sprite parameters must be provided if an spritesheet was given."
            el.attrib["spritesheet-src"] = self.sprite_source
            el.attrib["spritesheet-height"] = str(self.sprite_height)
            el.attrib["spritesheet-fps"] = str(self.sprite_fps)
            el.attrib["spritesheet-startingFrame"] = str(self.sprite_index)
        return el


class Progress(ToastElement, slot = _ToastElementType.VISUAL, tag = _ToastXMLTag.PROGRESS):
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
    __slots__ = (
        "value",
        "status",
        "title",
        "display_value"
    )

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

    def _to_xml(self):
        el = ET.Element(self._xmltag())
        el.attrib["value"] = "indeterminate" if (self.value == -1) else str(self.value)
        if self.title:
            el.attrib["title"] = self.title
        el.attrib["status"] = self.status or " "
        if self.display_value:
            el.attrib["valueStringOverride"] = self.display_value
        return el


class Button(ToastElement, slot = _ToastElementType.ACTION, tag = _ToastXMLTag.ACTION, uri_keys = ("imageUri", )):
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
        hint_action_id:
            An arbitrary string to identify the action which is reserved to use for
            telemetry.
    """
    __slots__ = (
        "content",
        "arguments",
        "is_context",
        "icon", 
        "input_id",
        "style",
        "tooltip",
        "is_protocol",
        "hint_action_id"
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
        is_protocol : bool = False,
        hint_action_id : Optional[str] = None
    ) -> None:
        self.content = content
        self.arguments = arguments
        self.is_context = is_context
        self.icon = icon
        self.input_id = input_id
        self.style = style
        self.tooltip = tooltip
        self.is_protocol = is_protocol
        self.hint_action_id = hint_action_id

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        if data.get("style"):
            x.style = ToastButtonStyle(data["style"])
        return x

    def _to_xml(self):
        el = ET.Element(self._xmltag())
        el.attrib["content"] = self.content
        el.attrib["arguments"] = self.arguments
        el.attrib["activationType"] = "foreground" if not self.is_protocol else "protocol"
        # Unsupported options:
        # - protocolActivationTargetApplicationPfn
        # - afterActivationBehavior = "pendingUpdate"
        #     (activationType must be "background")
        if self.is_context:
            el.attrib["placement"] = "contextMenu"
        if self.icon:
            el.attrib["imageUri"] = self.icon
        if self.input_id:
            el.attrib["hint-inputId"] = self.input_id
        if self.style:
            el.attrib["hint-buttonStyle"] = self.style.value
        if self.tooltip:
            el.attrib["hint-toolTip"] = self.tooltip
        if self.hint_action_id:
            el.attrib["hint-actionId"] = self.hint_action_id
        return el


class Header(ToastElement, slot = _ToastElementType.HEADER, tag = _ToastXMLTag.HEADER):
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
    __slots__ = (
        "id",
        "title",
        "arguments"
    )

    def __init__(
        self,
        id : str,
        title : str,
        arguments : str
    ) -> None:
        self.id = id
        self.title = title
        self.arguments = arguments
    
    def _to_xml(self):
        el = ET.Element(self._xmltag())
        el.attrib["id"] = self.id
        el.attrib["title"] = self.title
        el.attrib["arguments"] = self.arguments
        el.attrib["activationType"] = "foreground"
        return el


class Input(ToastElement, slot = _ToastElementType.ACTION, tag = _ToastXMLTag.INPUT):
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
    __slots__ = (
        "id",
        "placeholder",
        "title",
        "default"
    )

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
    
    def _to_xml(self):
        el = ET.Element(self._xmltag())
        el.attrib["id"] = self.id
        el.attrib["type"] = "text"
        if self.title:
            el.attrib["title"] = self.title
        if self.placeholder:
            el.attrib["placeHolderContent"] = self.placeholder
        if self.default:
            el.attrib["defaultInput"] = self.default
        return el


class Select(ToastElement, slot = _ToastElementType.ACTION, tag = _ToastXMLTag.INPUT):
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
    __slots__ = (
        "id",
        "options",
        "title",
        "default"
    )

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

    def _to_xml(self):
        el = ET.Element(self._xmltag())
        el.attrib["id"] = self.id
        el.attrib["type"] = "selection"
        if self.title:
            el.attrib["title"] = self.title
        if self.default:
            el.attrib["defaultInput"] = self.default
        for k, v in self.options.items():
            choice = ET.Element("selection")
            choice.attrib["id"] = k
            choice.attrib["content"] = v
            el.append(choice)
        return el