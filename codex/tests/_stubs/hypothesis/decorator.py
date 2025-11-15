from __future__ import annotations

def given(strategy):
    def decorator(func):
        def wrapper(*args, **kwargs):
            kwargs.setdefault("value", strategy.example())
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
