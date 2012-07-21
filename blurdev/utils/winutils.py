import win32gui, win32api


def bringWindowToFrontIfExists(window_name):
    def _handleGet(handle, args):
        windowtitle = win32gui.GetWindowText(handle)
        if windowtitle.startswith(window_name):
            args.append(handle)

    worked = False
    handles = []
    win32gui.EnumWindows(_handleGet, handles)
    for handle in handles:
        try:
            win32gui.SetForegroundWindow(handle)
        except Exception, e:
            print str(e)  # Microsoft sucks
        else:
            worked = True
    return worked
