import os

try:
    import win32net
    import win32netcon

    WIN32 = True
except ImportError:
    WIN32 = False


def username():
    """
    Returns the environment username.
    """
    return os.environ.get('USERNAME', None)


def hostname():
    """
    Returns the environment computer (host) name.
    """
    return os.environ.get('COMPUTERNAME', None)


def currentUsernames():
    """
    This gets a list of all usernames logged in across all windows sessions
    on the current computer.
    """
    if not WIN32:
        return []
    server = os.environ.get('COMPUTERNAME')
    res = 1
    pref = win32netcon.MAX_PREFERRED_LENGTH
    level = 0
    total_list = set()
    try:
        user_list, total, res2 = win32net.NetWkstaUserEnum(server, level, res, pref)
        for u in user_list:
            total_list.add(u['username'])
        return list(total_list)
    except Exception:
        return []
