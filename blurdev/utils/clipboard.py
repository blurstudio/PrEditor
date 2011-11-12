"""Convenience module for manipulating the system clipboard."""


try:
    import win32clipboard
except ImportError:
    WIN32 = False
else:
    WIN32 = True


def setText(text):
    if not WIN32:
        return
    text = unicode(text)
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text)
    win32clipboard.CloseClipboard()


def text():
    if not WIN32:
        return ''
    win32clipboard.OpenClipboard()
    text = win32clipboard.GetClipboardData()
    win32clipboard.CloseClipboard()
    return text
