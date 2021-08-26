from __future__ import print_function

from __future__ import absolute_import
import win32gui
import win32con


def bringWindowToFrontIfExists(window_name):
    """
    Looks for a windows with the given *window_name*.  If any are found,
    they are set as the foreground window.

    """

    def _handleGet(handle, args):
        windowtitle = win32gui.GetWindowText(handle)
        if windowtitle.startswith(window_name):
            args.append(handle)

    worked = False
    handles = []
    win32gui.EnumWindows(_handleGet, handles)
    for handle in handles:
        try:
            win32gui.SendMessage(handle, win32con.WM_NULL, 101, 0)
            win32gui.SendMessage(
                handle, win32con.WM_SHOWWINDOW, True, win32con.SW_PARENTOPENING
            )
            win32gui.ShowWindow(handle, win32con.SW_SHOWNORMAL)
            win32gui.ShowWindow(handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(handle)
        except Exception as e:
            print(e)  # Microsoft sucks
        else:
            worked = True
    return worked
