# -*- coding: utf-8 -*-
"""Decorator utility functions.

decorators:
- synchronized
- propertyx
- accepts
- returns
- singleton
- attrs
"""

from threading import Lock
from sys import settrace


def synchronized(lock=None):
    """Decorator that synchronizes a method or a function with a mutex lock.

    Example usage:

        @synchronized()
        def operation(self, a, b):
            ...
    """
    if lock is None:
        lock = Lock()
    def wrapper(function):
        def new_function(*args, **kwargs):
            lock.acquire()
            try:
                return function(*args, **kwargs)
            finally:
                lock.release()
        return new_function
    return wrapper


def propertyx(function):
    """Decorator to easily create properties in classes.

    Example:

        class Angle(object):
            def __init__(self, rad):
                self._rad = rad

            @property
            def rad():
                def fget(self):
                    return self._rad
                def fset(self, angle):
                    if isinstance(angle, Angle):
                        angle = angle.rad
                    self._rad = float(angle)

    Arguments:
    - `function`: The function to be decorated.
    """
    keys = ('fget', 'fset', 'fdel')
    func_locals = {'doc': function.__doc__}

    def probe_func(frame, event, arg):
        if event == 'return':
            locals = frame.f_locals
            func_locals.update(dict((k, locals.get(k)) for k in keys))
            settrace(None)
        return probe_func

    settrace(probe_func)
    function()
    return property(**func_locals)


def accepts(*types):
    """Decorator to ensure that the decorated function accepts the given types as arguments.

    Example:
        @accepts(int, (int,float))
        @returns((int,float))
        def func(arg1, arg2):
            return arg1 * arg2
    """
    def check_accepts(f):
        assert len(types) == f.func_code.co_argcount
        def new_f(*args, **kwds):
            for (a, t) in zip(args, types):
                assert isinstance(a, t), \
                    "arg %r does not match %s" % (a,t)
            return f(*args, **kwds)
        new_f.func_name = f.func_name
        return new_f
    return check_accepts


def returns(rtype):
    """Decorator to ensure that the decorated function returns the given
    type as argument.

    Example:
        @accepts(int, (int,float))
        @returns((int,float))
        def func(arg1, arg2):
            return arg1 * arg2
    """
    def check_returns(f):
        def new_f(*args, **kwds):
            result = f(*args, **kwds)
            assert isinstance(result, rtype), \
                "return value %r does not match %s" % (result,rtype)
            return result
        new_f.func_name = f.func_name
        return new_f
    return check_returns


def singleton(cls):
    """Decorator to ensures a class follows the singleton pattern.

    Example:
        @singleton
        class MyClass:
            ...
    """
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


def attrs(**kwds):
    """Decorator to add attributes to a function.

    Example:

        @attrs(versionadded="2.2",
               author="Guido van Rossum")
        def mymethod(f):
            ...
    """
    def decorate(f):
        for k in kwds:
            setattr(f, k, kwds[k])
        return f
    return decorate
