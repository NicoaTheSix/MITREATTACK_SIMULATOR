"""SVG-only theme palettes and alpha-aware projections. Workflow: README.md."""
from navigator_visuals import blend_colors, display_color, foreground_color

PALETTES = {
    'dark': dict(canvas='#1e1e1e', neutral='#222526', text='#dddddd', link='#6caedf',
                 disabled='#303436', disabled_text='#aaaaaa', legend='#252526',
                 legend_border='#666666', mini_header='#000000'),
    'light': dict(canvas='#ffffff', neutral='#f2f4f5', text='#202124', link='#0969a8',
                  disabled='#e1e4e8', disabled_text='#5d6268', legend='#f4f5f6',
                  legend_border='#6b7280', mini_header='#e8eaed'),
}


def palette(theme):
    if not isinstance(theme, str) or theme not in PALETTES:
        raise ValueError('SVG theme must be light or dark.')
    return dict(PALETTES[theme])


def project_scene(scene, theme):
    """Return a presentation copy; raw layer colors and native/Excel scenes stay intact."""
    colors = palette(theme)
    result = {**scene, 'svg_theme': theme}
    columns = []
    for column in scene['columns']:
        cells = []
        for cell in column['cells']:
            style = cell['style']
            background, foreground = colors['neutral'], colors['link']
            if not style['enabled']:
                foreground = colors['disabled_text']
                if scene['colors']:
                    background = colors['disabled']
            elif scene['colors']:
                sources = style.get('sources', [])
                raw = style.get('rawColor', style.get('background', ''))
                if sources:
                    projected_sources = [{**s, 'color': display_color(s.get('rawColor', s['color']), colors['neutral'])} for s in sources]
                    background = blend_colors([s['color'] for s in projected_sources])
                    foreground = foreground_color(background)
                    style = {**style, 'sources': projected_sources}
                elif raw:
                    background = display_color(raw, colors['neutral'])
                    foreground = foreground_color(background)
            cells.append({**cell, 'style': style, 'background': background, 'foreground': foreground})
        columns.append({**column, 'cells': cells})
    result['columns'] = columns
    return result
