"""Physical SVG paper presets and canonical size conversion. Workflow: README.md."""
import math

UNITS = {'px': 1, 'cm': 96 / 2.54, 'in': 96}
PAPER_SIZES = {'letter': (8.5, 11), 'legal': (8.5, 14), 'small': (11, 17),
               'medium': (18, 24), 'large': (24, 36)}
PAPER_LABELS = [('Custom', 'custom'), ('US Letter · 8.5 × 11 in', 'letter'),
                ('US Legal · 8.5 × 14 in', 'legal'), ('Small · 11 × 17 in', 'small'),
                ('Medium · 18 × 24 in', 'medium'), ('Large · 24 × 36 in', 'large')]
LENGTH_FIELDS = ('width', 'height', 'header_height', 'legend_x', 'legend_y', 'legend_width', 'legend_height')


def validate_page(size, orientation):
    if not isinstance(size, str) or size not in ('custom', *PAPER_SIZES):
        raise ValueError('SVG paper size must be custom, letter, legal, small, medium or large.')
    if not isinstance(orientation, str) or orientation not in ('portrait', 'landscape'):
        raise ValueError('SVG orientation must be portrait or landscape.')


def paper_dimensions(size, orientation, unit='px'):
    validate_page(size, orientation)
    if not isinstance(unit, str) or unit not in UNITS:
        raise ValueError('Invalid SVG unit.')
    if size == 'custom':
        raise ValueError('Custom SVG sizes use explicit width and height.')
    short, long = PAPER_SIZES[size]
    width, height = (short, long) if orientation == 'portrait' else (long, short)
    return width * 96 / UNITS[unit], height * 96 / UNITS[unit]


def custom_orientation(width, height, fallback='portrait'):
    """Custom dimensions are authoritative; zero means Auto and never rotates a legacy export."""
    return ('landscape' if width > height else 'portrait' if height > width else fallback) if width and height else fallback


def maximum_length(unit):
    # Avoid QDoubleSpinBox rounding a maximum up beyond the 100000-pixel limit.
    return math.floor(100000 / UNITS[unit] * 1_000_000) / 1_000_000
