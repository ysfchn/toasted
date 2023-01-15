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

from typing import TYPE_CHECKING, Optional
from winsdk.windows.ui.notifications import (
    ToastNotificationManager
)

if TYPE_CHECKING:
    from toasted.toast import Toast


class History:
    def __init__(self) -> None:
        pass

    @staticmethod
    def remove(toast_id : str, group_id : str, app_id : str):
        ToastNotificationManager.get_default().history.remove(toast_id, group_id, app_id)

    @staticmethod
    def remove_group(group_id : str, app_id : str):
        ToastNotificationManager.get_default().history.remove_group(group_id, app_id)

    @staticmethod
    def clear(app_id : str):
        ToastNotificationManager.get_default().history.clear(app_id)


class HistoryForToast(History):
    __slots__ = ("toast", )

    def __init__(self, toast : "Toast") -> None:
        super().__init__()
        self.toast = toast

    def remove(self):
        super().remove(self.toast.toast_id, self.toast.group_id, self.toast.app_id)

    def remove_group(self):
        super().remove_group(self.toast.group_id, self.toast.app_id)

    def clear(self):
        super().clear(self.toast.app_id)