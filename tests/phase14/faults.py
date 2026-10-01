"""Test-only injection utilities. BaseException models process loss, not adapter failure."""
class InjectedCrash(BaseException):
    pass


def crash_after(original, occurrence=1):
    count = 0
    def wrapped(*args, **kwargs):
        nonlocal count
        value = original(*args, **kwargs)
        count += 1
        if count == occurrence:
            raise InjectedCrash('test crash boundary')
        return value
    return wrapped


def crash_before(original, occurrence=1):
    count = 0
    def wrapped(*args, **kwargs):
        nonlocal count
        count += 1
        if count == occurrence:
            raise InjectedCrash('test crash boundary')
        return original(*args, **kwargs)
    return wrapped
