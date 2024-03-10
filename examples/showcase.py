from toasted import (
    Toast, Text, ToastTextStyle, 
    Image, Button, ToastImagePlacement, 
    Progress, ToastResult, ToastScenario
)
from toasted.common import is_in_venv
from toasted.elements import Select
from toasted.enums import ToastButtonStyle

import asyncio
import warnings

APP_ID = "Foo.Bar.App"
# APP_ID = "Microsoft.Windows.Explorer"

def warn_if_not_registered(app_id : str):
    # TODO: move that to the library instead.
    if is_in_venv() and (not Toast.is_registered_app_id(app_id)):
        warnings.warn(
            "Running in a virtualenv, therefore an app ID must be registered "
            "to Windows Registry to show toasts. Run 'Toast.register_app_id()'"
        )

async def show_parcel_example(app_id : str):
    toast = Toast(
        app_id = app_id,
        # Images can load from HTTP(S) sources along 
        # with file path locations, if this set to True.
        # (which is the default)
        remote_media = True
    )
    toast.elements = [
        Text("Parcel Track"),
        Text("Your parcel is on the way!"),
        Image("https://iili.io/J2vidJf.jpg"),
        # Groups and subgroups are defined as lists.
        # Groups can only contain subgroups (meaning you can't add elements in group-level), 
        # and subgroups can only contain Text and Image elements.
        [
            [
                Text("18 mins left", style = ToastTextStyle.TITLE)
            ]
        ],
        [
            [
                Text("Track number", style = ToastTextStyle.BASESUBTLE),
                Text("Carrier", style = ToastTextStyle.BASESUBTLE)
            ],[
                Text("A123B456C789", style = ToastTextStyle.BASE),
                Text("FooBar Postal Services", style = ToastTextStyle.BASE)
            ]
        ],
        Button(
            "Dismiss",
            # An arbitrary string which will be passed to the ToastResult
            # when this button has clicked, so you can know which button has clicked.
            arguments = "dismiss",
            icon = "https://iili.io/iIT76B.png"
        ),
        Button(
            "Open details",
            arguments = "open",
            # Images can also be loaded from data URIs, make sure
            # to set the data type. Only base64 values are supported.
            icon = "data:image/png;base64," + (
                "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAACXBIWXMAAAsTAAALEwEAmpwYAAAA"
                "AXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAJ6SURBVHgB7d3RTetQEIThNaKAlJASKAE6oAQo"
                "gQ6gA0qgBDqADoAKEBVAB4czxBIoIo7jJJ7ds/NJUR7wlWB++5JEAbpSWTzLrus+Nn2wfklP9e7c"
                "AjgxoVIAMgUgUwAyBSBTADIFYCvDnky2qjst6u2lTKArYE8Yv97hRD2zCRRgD/uODwow0SHGBwWY"
                "oI6/rHcvtuf4oAA76sfHmb+0A1CAHUwY/67enocOUICRpoxfXzK/3XaQAoxwrPFBAbY45vigAAOO"
                "PT4owAZzjA8K8I+5xgcFWDPn+KAAf8w9PihAjzE+KIDxxof0AZjjQ+oA7PEhbQAP40PKAF7Gh3QB"
                "PI0PqQJ4Gx/SBPA4PqQI4HV8aD6A5/Hh1Bo2YfybOv69zajZABPGv67jP9jMmvwvKMr40FyASOND"
                "UwGijQ/NBIg4PjQRIOr4ED5A5PEh9MPQIOO/DX60BP0RJYxfb+9lvCvzqAQM0Mz4UIIFqJ/TWTPj"
                "QwkUoB//s4x3Zd6VIAGaHB9KgADNjg/FeYCmxzfnzwMwvq0e5y9G/hNXT7Kg/xoWQwe4vAJ2PPNx"
                "3KU5hA2HPnGXV8COZ/5XvV3UM//VAnL3WlCm8cFVgGzjg5sAGccHFwGyjg/0AJnHB2qA7OMDLYDG"
                "X6EE0Pi/WFfAuWn8H5QA/fsv77Yc1vz4QPse0L8DeVOEFOMD9VHQhghpxgf684C1CKnGBxevhiJC"
                "Wf0hj8dM44Obl6O7GX8qxRP9rggyBSBTADIFIFMAMgUgUwAyBSBTADIFIFMAMgUgUwAyBSBTADIF"
                "IFMAMgUgUwAyBSDrSv92BOHQFUCmAGQKQKYAZApApgBkCkD2DXSNDzVM6S4iAAAAAElFTkSuQmCC"
            )
        ),
        Button(
            "Stop tracking",
            arguments = "stop",
            # When button is added to the context menu, it won't be visible on the
            # toast, instead, it will be shown when you click on the top-right of the 
            # notification. 
            is_context = True
        )
    ]
    # To display the toast, call show(). It is a coroutine, so you
    # will need to run with asyncio.run (in top-level and non-async methods) or
    # await keyword in async methods.
    #
    # The returned value is ToastResult, which is an object that contains all 
    # information about the current state of the toast.
    #
    # You can also use toast.on_shown() and toast.on_result() callbacks,
    # which is shown in the next example.
    result = await toast.show()
    print(result)


async def show_call_example(app_id : str):
    toast = Toast(
        app_id = app_id,
        # When set to INCOMING_CALL, Windows will change 
        # the default toast sound and toast timeout.
        scenario = ToastScenario.INCOMING_CALL
    )
    toast.elements = [
        # See docstrings of classes to learn more about
        # the other properties of them.
        Text("Benjamin", is_center = True),
        Text("Incoming call", is_center = True),
        Image("https://iili.io/J28vYGf.png", is_circle = True),
        Select(
            id = "select",
            options = {
                "q0": "Reject with a message...",
                "q1": "Can you call back later?",
                "q2": "I'll call you back.",
                "q3": "Please text me."
            },
            default = "q0"
        ),
        Button(
            "Decline", 
            arguments = "decline",
            icon = "icon://U+E778",
            style = ToastButtonStyle.SUCCESS
        ),
        Button(
            "Accept", 
            arguments = "accept",
            icon = "icon://U+E717",
            style = ToastButtonStyle.CRITICAL
        )
    ]
    # As explained in above, you can set callbacks to do a specific task
    # when toast has changed its state. Callbacks can also be coroutines
    # (means "async def" functions also works).
    @toast.on_shown
    def my_handler_1(data):
        print("shown a toast")

    @toast.on_result
    def my_handler_2(result : ToastResult):
        print(result)
    # Even with and without callbacks, the show() function will
    # continue returning a ToastResult, which is the same object with
    # the one that passed to the on_result() handler as a parameter.
    await toast.show()


async def show_sync_example(app_id : str):
    toast = Toast(
        app_id = app_id,
        # An arbitrary string which will be passed to the ToastResult
        # when the toast itself has clicked (not on the buttons),
        # so you can know that if an button is clicked or toast itself
        # has clicked.
        arguments = "click"
    )
    toast.elements = [
        Image("https://iili.io/J286BDB.png", placement = ToastImagePlacement.HERO),
        Text("Cloud Sync"),
        Text("Syncing your files..."),
        # To set a "binding"/"dynamic" value which can be changed
        # during the lifecycle of your application, use a string value
        # which is surrounded with curly braces ("{" and "}").
        Progress(
            value = "{value}",
            status = "{status}",
            title = "Photos/landscape.png",
            display_value = "{value} @ 1.4 MB/s"
        )
    ]
    # Then, you can set these values by providing 
    # a dictionary in show() method.
    result = await toast.show({
        "value": 75 / 100,
        "status": "Uploading..."
    })
    print(result)

if __name__ == "__main__":
    # Toast.register_app_id(APP_ID, "FooBar")
    asyncio.run(show_parcel_example(APP_ID))
    pass