"""Bounded real-number helpers for the pinned mathjs scalar subset. Flow: README.md."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
import math

REL_TOL, ABS_TOL = 1e-12, 1e-15
CONSTANTS = {'pi': math.pi, 'e': math.e, 'tau': math.tau, 'phi': (1 + math.sqrt(5)) / 2,
             'true': 1, 'false': 0}


def nearly_equal(a, b):
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def decimals(value):
    if value != int(value) or not 0 <= value <= 15:
        raise ValueError('Navigator decimal precision must be an integer from 0 to 15.')
    return int(value)


def _decimal_round(value, places):
    with localcontext() as context:
        context.prec = 330
        return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def navigator_round(value, places=0):
    places = decimals(places)
    if places < 12:
        corrected = _decimal_round(value, 12)
        if nearly_equal(value, corrected):
            value = corrected
    return _decimal_round(value, places)


def _integer_round(value, ceiling=False):
    raw = math.ceil(value) if ceiling else math.floor(value)
    nearest = navigator_round(value)
    return nearest if raw != nearest and nearly_equal(value, nearest) and not nearly_equal(value, raw) else raw


def navigator_floor(value, places=0):
    scale = 10 ** decimals(places)
    return _integer_round(value * scale) / scale


def navigator_ceil(value, places=0):
    scale = 10 ** decimals(places)
    return _integer_round(value * scale, True) / scale


def fix(value, places=0):
    return navigator_floor(value, places) if value > 0 else navigator_ceil(value, places)


def mod(a, b):
    return a if b == 0 else a - b * navigator_floor(a / b)


def nth_root(value, root=2):
    if root == 0 or (value < 0 and abs(root) % 2 != 1):
        raise ValueError('Root must be nonzero, and an odd integer for a negative value.')
    if value == 0:
        if root < 0:
            raise ValueError('A negative root of zero is not finite.')
        return 0
    result = math.copysign(abs(value) ** (1 / abs(root)), value)
    return 1 / result if root < 0 else result


def compare(operation, a, b):
    same = nearly_equal(a, b)
    if operation == '==': return same
    if operation == '!=': return not same
    if operation == '<': return a < b and not same
    if operation == '>': return a > b and not same
    if operation == '<=': return a < b or same
    return a > b or same


EXTRA_FUNCTIONS = {name: (getattr(math, name), 1, 1) for name in (
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
    'log2', 'log10', 'log1p', 'expm1')}
EXTRA_FUNCTIONS.update(atan2=(math.atan2, 2, 2), cbrt=(math.cbrt, 1, 1),
    sign=(lambda value: (value > 0) - (value < 0), 1, 1), fix=(fix, 1, 2), mod=(mod, 2, 2),
    nthRoot=(nth_root, 1, 2))
