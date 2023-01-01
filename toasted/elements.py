__all__ = [
    "Text",
    "Image",
    "Progress",
    "Button",
    "Header",
    "Input",
    "Select",
    "Group",
    "Subgroup"
]

from toasted.common import ToastElement, xml, get_enum, ToastElementContainer, ToastGenericContainer
from toasted.enums import (
    ToastElementType, 
    ToastTextAlign, 
    ToastTextStyle, 
    ToastButtonStyle, 
    ToastImagePlacement
)
from typing import Optional, Dict, Any, List, Union

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
            If you set to True, the text is always displayed at the bottom of your notification, 
            along with your app's identity or the notification's timestamp. 
            On older versions of Windows that don't support attribution text, 
            the text will simply be displayed as another text element 
            (assuming you don't already have the maximum of three text elements). 
        is_center:
            Set to True to center the text for incoming call notifications. 
            This value is only used for notifications with with a scenario value of INCOMING_CALL; 
            otherwise, it is ignored.
        max_lines:
            Gets or sets the maximum number of lines the text element is allowed to display.
        min_lines:
            Gets or sets the minimum number of lines the text element must display. 
            This property will only take effect if the text is inside an subgroup.
    """
    __slots__ = ("content", "id", "style", "align", "is_attribution", "is_center", "max_lines", "min_lines", )

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
        self.id = None if id == None else int(id)
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

    def to_xml(self) -> str:
        return xml(
            "text", 
            self.content, 
            id = self.id,
            placement = "attribution" if self.is_attribution else None,
            hint_callScenarioCenterAlign = True if self.is_center else None,
            hint_align = self.align,
            hint_style = self.style,
            hint_maxLines = self.max_lines,
            hint_minLines = self.min_lines
        )


class Image(ToastElement, etype = ToastElementType.VISUAL, ename = "image", esources = {"source": "src"}):
    """
    Specifies an image used in the toast template.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-image

    Args:
        source:
            The URI of the image source (http(s):// is supported when "remote_images" has enabled
            on Toast objects - which is default, otherwise only file paths can be used).
        id:
            The image element in the toast template that this image is intended for. 
            If a template has only one image, then this value is 1. 
            The number of available image positions is based on the template definition.
        alt:
            A description of the image, for users of assistive technologies.
        placement:
            The placement of the image. 
            LOGO: The image replaces your app's logo in the toast notification.,
            HERO: The image is displayed as a hero image. 
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
        self.id = None if id == None else int(id)
        self.alt = alt
        self.placement = placement
        self.is_circle = is_circle

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        x.placement = get_enum(ToastImagePlacement, data.get("placement", None))
        return x

    def to_xml(self) -> str:
        return xml(
            "image", 
            id = self.id,
            src = self.source,
            alt = self.alt,
            placement = self.placement,
            hint_crop = "circle" if self.is_circle else None
        )


class Progress(ToastElement, etype = ToastElementType.VISUAL, ename = "progress"):
    """
    Specifies a progress bar for a toast notification. Only supported on toasts on Desktop, build 15063 or later.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-progress

    Args:
        value:
            The value of the progress bar. This value either be a float between 0 and 1 (inclusive)
            or "indeterminate", which results in a loading animation.
        status:
            A status string that is displayed underneath the progress bar on the left. 
            This string should reflect the status of the operation, like "Downloading..." or "Installing..."
        title:
            An optional title string.
        display_value:
            An optional string to be displayed instead of the default percentage string. 
            If this isn't provided, something like "70%" will be displayed.
    """
    __slots__ = ("value", "status", "title", "display_value", )

    def __init__(
        self, 
        value : Union[str, int],
        status : Optional[str] = None,
        title : Optional[str] = None,
        display_value : Optional[str] = None
    ) -> None:
        self.value = value
        self.status = status
        self.title = title
        self.display_value = display_value

    def to_xml(self) -> str:
        return xml(
            "progress", 
            title = self.title,
            value = self.value,
            status = self.status or " ",
            valueStringOverride = self.display_value
        )


class Button(ToastElement, etype = ToastElementType.ACTION, ename = "button", esources = {"icon": "imageUri"}):
    """
    Specifies a button shown in a toast.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-action

    Args:
        content:
            The content displayed on the button.
        arguments:
            App-defined string of arguments that the app will later receive if the user clicks this button.
        is_context:
            When set to True, the action becomes a context menu action added to the 
            toast notification's context menu rather than a traditional toast button.
        icon:
            The URI of the image source for a toast button icon. 
            These icons are white transparent 16x16 pixel images at 100% scaling and should have no padding 
            included in the image itself. If you choose to provide icons on a toast notification, 
            you must provide icons for ALL of your buttons in the notification, 
            as it transforms the style of your buttons into icon buttons.
        input_id:
            Set to the ID of an input to position button beside the input.
        style:
            The button style.
        tooltip:
            The tooltip for a button, if the button has an empty content string.
    """
    __slots__ = ("content", "arguments", "is_context", "icon", "input_id", "style", "tooltip", )

    def __init__(
        self,
        content : str,
        arguments : str,
        is_context : bool = False,
        icon : Optional[str] = None,
        input_id : Optional[str] = None,
        style : Optional[ToastButtonStyle] = None,
        tooltip : Optional[str] = None
    ) -> None:
        self.content = content
        self.arguments = arguments
        self.is_context = is_context
        self.icon = icon
        self.input_id = input_id
        self.style = style
        self.tooltip = tooltip

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json(data)
        x.style = get_enum(ToastButtonStyle, data.get("style", None))
        return x

    def to_xml(self) -> str:
        return xml(
            "action", 
            content = self.content,
            arguments = self.arguments,
            activationType = "foreground", 
            placement = "contextMenu" if self.is_context else None,
            imageUri = self.icon,
            hint_inputId = self.input_id,
            hint_buttonStyle = self.style,
            hint_toolTip = self.tooltip
            # Unsupported options:
            # - protocolActivationTargetApplicationPfn
            # - afterActivationBehavior = "pendingUpdate"
        )


class Header(ToastElement, etype = ToastElementType.HEADER, ename = "header"):
    """
    Specifies a custom header that groups multiple notifications together within Action Center.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-header

    Args:
        id:
            A developer-created identifier that uniquely identifies this header. 
            If two notifications have the same header id, they will be displayed underneath the 
            same header in Action Center.
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

    def to_xml(self) -> str:
        return xml(
            "header", 
            id = self.id, 
            title = self.title, 
            arguments = self.arguments,
            activationType = "foreground"
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

    def to_xml(self) -> str:
        return xml(
            "input", 
            type = "text",
            id = self.id, 
            title = self.title, 
            placeHolderContent = self.placeholder,
            defaultInput = self.default
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

    def to_xml(self) -> str:
        return xml(
            "input", 
            "".join([
                xml(
                    "selection", 
                    id = x, 
                    content = y
                ) for x, y in self.options.items()
            ]),
            type = "selection",
            id = self.id, 
            title = self.title,
            defaultInput = self.default
        )


class Subgroup(ToastElementContainer):
    """
    Specifies vertical columns that can contain text and images.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-subgroup
    """
    def __init__(self) -> None:
        super().__init__()

    def to_xml(self) -> str:
        return xml(
            "subgroup",
            "".join([x.to_xml() for x in self.data])
        )


class Group(ToastGenericContainer[Subgroup], ToastElement, etype = ToastElementType.VISUAL, ename = "group"):
    """
    Semantically identifies that the content in the group must either be displayed as a whole, 
    or not displayed if it cannot fit. Groups also allow creating multiple columns.
    https://docs.microsoft.com/en-us/uwp/schemas/tiles/toastschema/element-group
    """

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def from_list(data : List[List[ToastElement]]) -> "Group":
        x = Group()
        for i in data:
            y = Subgroup()
            for e in i:
                y.append(e)
            x.data.append(y)
        return x

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        x = super().from_json({})
        for i in data["elements"]:
            y = Subgroup()
            for e in i:
                y.append(cls._create_from_type(**e))
            x.data.append(y)
        return x

    def to_xml(self) -> str:
        return xml(
            "group",
            "".join([x.to_xml() for x in self.data])
        )