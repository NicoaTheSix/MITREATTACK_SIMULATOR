"""Pure Navigator layer color projection for the native matrix. Flow: README.md."""
from copy import deepcopy
import math
import re
from attack_catalog import external_id, tactic_phases

DEFAULT_GRADIENT = {"colors": ["#ff6666", "#ffe766", "#8ec843"], "minValue": 0, "maxValue": 100}
COLOR = re.compile(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?")


def validate_visuals(layer):
    gradient = layer.get("gradient", DEFAULT_GRADIENT)
    if not isinstance(gradient, dict):
        raise ValueError("Gradient must be an object.")
    colors = gradient.get("colors")
    if not isinstance(colors, list) or not 2 <= len(colors) <= 32 or any(
            not isinstance(color, str) or not COLOR.fullmatch(color) for color in colors):
        raise ValueError("Gradient needs 2–32 #RRGGBB or #RRGGBBAA color stops.")
    low, high = gradient.get("minValue"), gradient.get("maxValue")
    if (any(type(value) not in {int, float} or not math.isfinite(value) for value in (low, high))
            or high <= low or not math.isfinite(high - low)):
        raise ValueError("Gradient bounds must be finite numbers with maximum greater than minimum.")
    legend = layer.get("legendItems", [])
    if not isinstance(legend, list) or len(legend) > 200:
        raise ValueError("Use at most 200 legend entries.")
    for entry in legend:
        if (not isinstance(entry, dict) or not isinstance(entry.get("label"), str)
                or not isinstance(entry.get("color"), str) or not COLOR.fullmatch(entry["color"])):
            raise ValueError("Every legend entry needs a label and a hexadecimal color.")
    if "hideDisabled" in layer and type(layer["hideDisabled"]) is not bool:
        raise ValueError("Hide disabled must be a boolean.")
    layout = layer.get('layout', {})
    if not isinstance(layout, dict):
        raise ValueError('Layout must be an object.')
    for field in ('showAggregateScores', 'countUnscored'):
        if field in layout and type(layout[field]) is not bool:
            raise ValueError(field + ' must be a boolean.')
    if layout.get('aggregateFunction', 'average') not in ('average', 'min', 'max', 'sum'):
        raise ValueError('Aggregate function must be average, min, max or sum.')
    if layout.get('layout', 'flat') not in ('side', 'flat', 'mini'):
        raise ValueError('Layout must be side, flat or mini.')
    if type(layer.get('sorting', 0)) is not int or layer.get('sorting', 0) not in range(4):
        raise ValueError('Sorting must be 0, 1, 2 or 3.')
    filters = layer.get('filters', {})
    if not isinstance(filters, dict):
        raise ValueError('Filters must be an object.')
    if 'platforms' in filters and (not isinstance(filters['platforms'], list) or
                                  any(not isinstance(p, str) for p in filters['platforms'])):
        raise ValueError('Platform filters must be a list of names.')


def rgba(value):
    values = [int(value[index:index + 2], 16) for index in (1, 3, 5)]
    return (*values, int(value[7:9], 16) if len(value) == 9 else 255)


def display_color(value, background="#222526"):
    red, green, blue, alpha = rgba(value)
    back = rgba(background)
    return '#' + ''.join(f'{round(front * alpha / 255 + back[index] * (1 - alpha / 255)):02x}'
                         for index, front in enumerate((red, green, blue)))


def gradient_color(score, gradient, raw=False):
    low, high = gradient["minValue"], gradient["maxValue"]
    position = max(0.0, min(1.0, (score - low) / (high - low))) * (len(gradient["colors"]) - 1)
    index = min(int(position), len(gradient["colors"]) - 2)
    fraction = position - index
    left, right = rgba(gradient["colors"][index]), rgba(gradient["colors"][index + 1])
    color = '#' + ''.join(f'{round(a + (b - a) * fraction):02x}' for a, b in zip(left, right))
    return color if raw else display_color(color)


def foreground_color(background):
    rgb = rgba(background)
    def linear(value):
        value /= 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    luminance = sum(linear(value) * weight for value, weight in zip(rgb[:3], (0.2126, 0.7152, 0.0722)))
    return '#000000' if luminance > 0.179 else '#ffffff'


class LayerAppearance:
    def __init__(self, layer=None, catalog=None):
        self.layer = deepcopy(layer or {})
        validate_visuals(self.layer)
        self.gradient = self.layer.get("gradient", DEFAULT_GRADIENT)
        self.rows = {(row["techniqueID"], row.get("tactic", "")): row for row in self.layer.get("techniques", [])}
        self.families = {}
        self.aggregate_cache = {}
        if catalog is not None and self.layer.get('layout', {}).get('showAggregateScores', False):
            records_by_id = {external_id(obj): obj for obj in catalog.records.values()}
            for child, parent in catalog.parents.items():
                for slug in tactic_phases(catalog.records[child], catalog.domain):
                    identity = (external_id(catalog.records[parent]), slug)
                    self.families.setdefault(identity, []).append(external_id(catalog.records[child]))
            for (parent_id, slug), children in self.families.items():
                parent = records_by_id[parent_id]
                if slug in tactic_phases(parent, catalog.domain):
                    children.insert(0, parent_id)

    def aggregate(self, technique_id, tactic):
        identity = (technique_id, tactic)
        if identity not in self.families:
            return None
        if identity not in self.aggregate_cache:
            scores, known = [], False
            layout = self.layer.get('layout', {})
            for attack_id in self.families[identity]:
                row = self.rows.get((attack_id, tactic), self.rows.get((attack_id, ''), {}))
                if not row.get('enabled', True):
                    continue
                if 'score' in row:
                    scores.append(row['score'])
                    known = True
                elif layout.get('countUnscored', False):
                    scores.append(0)
            result = None
            if known:
                try:
                    operation = layout.get('aggregateFunction', 'average')
                    result = (min(scores) if operation == 'min' else max(scores) if operation == 'max'
                              else math.fsum(value / len(scores) for value in scores) if operation == 'average' else math.fsum(scores))
                    if not math.isfinite(result):
                        result = None
                except OverflowError:
                    result = None
            self.aggregate_cache[identity] = result
        return self.aggregate_cache[identity]

    def cell(self, technique_id, tactic):
        row = self.rows.get((technique_id, tactic), self.rows.get((technique_id, ""), {}))
        enabled = row.get("enabled", True)
        color = row.get("color", "")
        score = row.get("score")
        aggregate = self.aggregate(technique_id, tactic)
        display_score = aggregate if aggregate is not None else score
        raw_color = color or (gradient_color(display_score, self.gradient, raw=True) if display_score is not None else '')
        background = display_color(raw_color) if raw_color else ''
        if not enabled:
            background = "#303436"
        return {"background": background,
                "opacity": rgba(raw_color)[3] / 255 if raw_color else 0,
                "foreground": foreground_color(background) if enabled and background else "#999999" if not enabled else "",
                "enabled": enabled, "hidden": not enabled and self.layer.get("hideDisabled", False),
                "score": score, "comment": row.get("comment", ""),
                "links": deepcopy(row.get('links', [])), "metadata": deepcopy(row.get('metadata', [])),
                "aggregateScore": aggregate,
                "showSubtechniques": row.get("showSubtechniques", False)}


def blend_colors(colors):
    """Equal-weight RGB mixing, independent of layer order (red + blue = purple)."""
    if not colors:
        raise ValueError("At least one color is required for blending.")
    channels = [rgba(color)[:3] for color in colors]
    return '#' + ''.join(f'{round(sum(color[index] for color in channels) / len(channels)):02x}'
                         for index in range(3))


class OverlayAppearance:
    """Read-only composite of compatible layers; enabled colored cells contribute."""
    def __init__(self, named_layers, active_layer, catalog=None):
        self.appearances = [(name, LayerAppearance(layer, catalog)) for name, layer in named_layers]
        self.active = LayerAppearance(active_layer, catalog)
        self.gradient = DEFAULT_GRADIENT
        self.rows = {}  # A composite has no single score scale.
        self.cache = {}
        legend = []
        for name, appearance in self.appearances:
            entries = appearance.layer.get('legendItems', [])
            if not entries:
                colors = dict.fromkeys(row['color'] for row in appearance.rows.values()
                                       if row.get('color') and row.get('enabled', True))
                if any('score' in row and row.get('enabled', True) for row in appearance.rows.values()):
                    colors.update(dict.fromkeys(appearance.gradient['colors']))
                entries = [{'color': color, 'label': color} for color in colors]
            legend.extend({'color': entry['color'], 'label': name + ': ' + entry['label']} for entry in entries)
        self.legend_truncated = len(legend) > 64
        self.layer = {'legendItems': legend[:64]}

    def cell(self, technique_id, tactic):
        identity = (technique_id, tactic)
        if identity not in self.cache:
            contributions, expand = [], False
            for name, appearance in self.appearances:
                cell = appearance.cell(technique_id, tactic)
                expand |= cell['showSubtechniques']
                if cell['enabled'] and cell['background'] and cell['opacity'] > 0:
                    contributions.append({'name': name, 'color': cell['background'],
                                          'score': cell['score'], 'comment': cell['comment'],
                                          'aggregateScore': cell.get('aggregateScore')})
            result = self.active.cell(technique_id, tactic)
            result['activeEnabled'] = result['enabled']
            if contributions:
                background = blend_colors([source['color'] for source in contributions])
                result.update(background=background, foreground=foreground_color(background),
                              enabled=True, hidden=False, score=None, comment='')
            result['sources'] = contributions
            result['showSubtechniques'] = expand
            self.cache[identity] = result
        # View-only color hiding must never overwrite the cached composite.
        return dict(self.cache[identity])
