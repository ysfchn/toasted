# toasted

Yet another notifications library for Windows, written in Python, by calling Windows Runtime APIs (WinRT).

What Toasted does differently is to support every notification element provided by Windows, like images, select, inputs and so on. So you are not stuck with a single line of text. See also [why.](#why)

![](.github/assets/preview.png)

It works and has been tested on Windows 10 and 11, though early builds of Windows 10 may not work as the Windows APIs called by Toasted are initially introduced in these early builds with support of fewer features than in the later releases of Windows. Due to backwards-compatible direction of Windows, it can be expected for toast notifications to continue to work in the future releases of Windows too.

## Install

```
python -m pip install toasted
```

## Usage

See [`showcase.py`](./examples/showcase.py) for an introduction to the library with detailed example toast notification configurations.

## Special behaviours

Windows API restricts use of some features of toast notifications for non-UWP/non-packaged apps, Toasted contains bunch of conveinence features to mimic the behaviour of UWP apps and get the most of the toast features of Windows.

### Remote URIs

Normally, Windows only allows local file paths on toasts sent by non-UWP applications. To overcome the limitation, if a HTTP(S) URI was provided as an image or audio source, Toasted will download it to `%TEMP` and patch the URI with the downloaded file location in toast data before sending it to Windows.

Downloaded files are deleted once toast has dismissed or clicked to not leave traces on the system.

Also, to comply with Windows API, you can enable sending system theme information (such as `ms-lang`, `ms-theme`, `ms-contrast`) to given URLs as query parameters by setting `add_query_params` property, so if you are serving files from your web server, you can serve different images based on the system theme.

### Application icon and name (app IDs)

Notifications in Windows gets sent in behalf of a origin app which registered in the system previously. Windows uses the source application's name and icon in toast notifications.

Installed apps registers its "App User Model ID" (AUMID) in the registry, so you can only send notifications on behalf of these installed applications.

You can use `Toast.app_id` property to set the app ID of the notification to one of registered IDs in the system. If you don't provide one (which is the default), Toasted will use the path where Python has installed as an ID (`sys.executable`), since Python already registers its path as a ID when you install Python from the setup. However, **that won't work with virtually created Python environments** as there won't be a Python that registered on the system. In that case, you can _only_ use app IDs registered on the system.

However, Toasted provides a `register_app_id()` helper method to register a new app ID (AUMID) in registry along with your preffered application name and icon. Then you can use your own app ID in your toasts and Windows will the toast show on behalf of your app ID. AUMID usually follows `Foo.Bar.Example` format, but it doesn't need to be, like how Python installation just uses its executable path as an ID.

If `register_app_id()` method was used, Toasted will create a key in `HKEY_CURRENT_USER`, so it doesn't require administrator privileges and can be used right ahead without rebooting Windows.

> [!WARNING]
> Since [app ID registrations alters Windows Registry](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/send-local-toast-other-apps#step-1-register-your-app-in-the-registry), this will leave traces in system even after your Python program is no longer running. You can unregister the application by `unregister_app_id()` method.
>
> When creating a new app ID and using it before sending toast, make sure that all notifications sent by Toasted are cleared from Action Center to make Windows to use the updated application icon and name.

```py
from toasted import Toast

my_app_id = "MyOrg.MyDomain.MyPhone"
Toast.register_app_id(my_app_id, "My Phone App")
mytoast = Toast(app_id = my_app_id)

# You can also change the currently using app ID at any time.
mytoast.app_id = app_id
```

### Custom sounds

If an custom sound has provided, toast's own sound will be muted and Python's `winsound` module will be used instead. Also, sounds from HTTP sources are supported too instead of just file paths.

### Using Windows system icons

Wherever an image can be placed, you can ask Toasted to use a icon from system to give your notifications a more native feeling. Toasted achieves that by creating an image in-memory with Pillow and adding the Unicode character of the given icon code point.

To do that, provide an URI with `icon://` scheme as an image source. For example, setting `icon://E706` as an image will use "brightness" icon found in code point `U+E706`.

This scheme also supports few query parameters to change the look of the created image, like its foreground and background color. (e.g. `icon://EBB5?foreground=#FFFFFF&background=#F7630C&padding=40`). See also `Toasted.common.get_icon_from_font()`.

System icons in Windows comes from [Segoe Fluent](https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-fluent-icons-font) and [Segoe MDL2](https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-ui-symbol-font) font installed in Windows. "Segoe Fluent" icons comes preinstalled on Windows 11, and "Segoe MDL2" icons comes preinstalled on both Windows 10 and 11. These fonts can also be installed separately by visiting given links.

Toasted will prefer using MDL2 icons if Python is running on Windows 10, or Fluent icons if running on Windows 11. To use a custom icon font other than system fonts when using `icon://` scheme, use `font_file` query parameter to provide the full path of the font.

### Update toast content (Data binding)

Windows supports the use of template (binding) keys instead of a fixed value in some places, such as the `value` property of `Progress` element, so their initial values can be set using `show()` and then continuously updated using `update()` without displaying a new toast each time.

```py
from toasted import Toast, Progress, Text
import asyncio

async def main():
    toast = Toast()
    toast.elements = [
        Text("File downloader"),
        Progress(
            value = "{value}",
            status = "Downloading files..."
        )
    ]

    await toast.show(dict(value = 75 / 100))
    await asyncio.sleep(2)
    await toast.update(dict(value = 80 / 100))

asyncio.run(main())
```

## Building

```
python -m pip wheel .
```

## Why?

Even though I do not use Windows daily, I think toast notifications in Windows are so _rich_ to be ignored. And there isn't much resource about it rather than just telling how to create a text-only toast - even when Windows could display a whole UI in it. So I've decided to create one that supports every toast feature that I could implement of.

It may not look like a good practice to keep library exclusively for Windows due to the nature of Python, but it is not like other systems do provide anything rich as in Windows from what I can tell. The closest seems to be Freedesktop's desktop notifications, but still, this library is too integrated with Windows API, and I don't want to remove existing features just to achieve parity. If cross-platform support is crucial for you, you would be better to look for another notification library.

## Unimplemented features

While the intention is to bring every capability of toast notifications, some features are not implemented due to the nature of Toasted only working one-off and portability of Python. Below is a non extensive list of these:

* [Collections](https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-collections)
* [Pending updates & background events](https://learn.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/toast-pending-update?tabs=builder-syntax), seems to require a COM server.
* [Push notifications through WNS](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/push-notifications/wns-overview)

## License

Source code is licensed under [MIT License](LICENSE). You must include the license notice in all copies or substantial uses of the work.

## References

* [App notification content](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/adaptive-interactive-toasts?tabs=xml)
* [Toast content schema](https://learn.microsoft.com/en-us/uwp/schemas/tiles/toastschema/schema-root)