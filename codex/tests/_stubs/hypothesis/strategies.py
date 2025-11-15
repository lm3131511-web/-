from __future__ import annotations

def floats(*, min_value: float, max_value: float):
    class FloatStrategy:
        def example(self):
            return min_value

    return FloatStrategy()


class _Strategies:
    def floats(self, *, min_value: float, max_value: float):
        return floats(min_value=min_value, max_value=max_value)


strategies = _Strategies()
