"""Physical SVG sizing and presentation settings. Workflow: README.md."""
from copy import deepcopy
from app_identity import APP_NAME
import math
import re
import textwrap
from xml.etree import ElementTree as ET
from svg_themes import palette
from svg_sizing import UNITS, PAPER_SIZES, validate_page, paper_dimensions, custom_orientation

SVG_NS = 'http://www.w3.org/2000/svg'
FONTS = {'sans-serif': 'Arial, sans-serif', 'serif': 'Georgia, serif', 'monospace': 'Consolas, monospace'}
DEFAULT_SVG = {'theme': 'dark', 'unit': 'px', 'width': 0, 'height': 0, 'header_height': 0, 'font': 'sans-serif',
               'size': 'custom', 'orientation': 'portrait',
               'show_header': True, 'show_about': True, 'show_domain': True, 'show_filters': True,
               'show_legend': True, 'legend_undocked': False, 'legend_x': 18, 'legend_y': 18,
               'legend_width': 300, 'legend_height': 0, 'cell_border': '#41484d', 'subtechniques': 'all'}


def validate_svg_options(options):
    if not isinstance(options, dict) or set(options) - set(DEFAULT_SVG):
        raise ValueError('Unknown SVG setting.')
    result = {**DEFAULT_SVG, **options}
    palette(result['theme'])
    validate_page(result['size'], result['orientation'])
    if (not isinstance(result['unit'],str) or result['unit'] not in UNITS or
            not isinstance(result['font'],str) or result['font'] not in FONTS or
            result['subtechniques'] not in ('all','expanded','none')):
        raise ValueError('Invalid SVG unit, font or sub-technique mode.')
    for field in ('show_header','show_about','show_domain','show_filters','show_legend','legend_undocked'):
        if type(result[field]) is not bool:
            raise ValueError(field + ' must be a boolean.')
    for field in ('width','height','header_height','legend_x','legend_y','legend_width','legend_height'):
        value = result[field]
        if type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value * UNITS[result['unit']] <= 100000:
            raise ValueError(field + ' must be a finite nonnegative size within 100000 pixels.')
    if result['size'] in PAPER_SIZES:
        result['width'], result['height'] = paper_dimensions(result['size'], result['orientation'], result['unit'])
    else:
        result['orientation'] = custom_orientation(result['width'], result['height'], result['orientation'])
    if result['legend_width'] * UNITS[result['unit']] < 40:
        raise ValueError('Legend width must be at least 40 pixels.')
    if not isinstance(result['cell_border'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',result['cell_border']):
        raise ValueError('Cell border must be #RRGGBB.')
    return result


def render_svg(scene, options, base_renderer):
    options = validate_svg_options(options)
    theme = palette(options['theme'])
    factor = UNITS[options['unit']]
    pixels = lambda field: options[field] * factor
    body_scene = {**scene, 'legend': [], 'description': '', 'svg_theme': options['theme']}
    base = ET.fromstring(base_renderer(body_scene))
    natural_width, natural_height = float(base.get('width')), float(base.get('height')) - 100
    width = pixels('width') or natural_width
    if width < 80:
        raise ValueError('SVG width must be at least 80 pixels.')
    ET.register_namespace('', SVG_NS)
    root = ET.Element(f'{{{SVG_NS}}}svg')
    def element(parent, tag, **attrs):
        return ET.SubElement(parent, f'{{{SVG_NS}}}{tag}', {key.replace('_','-'):str(value) for key,value in attrs.items()})
    def text(parent,x,y,value,size=12):
        item=element(parent,'text',x=x,y=y,fill=theme['text'],font_size=size,font_family=FONTS[options['font']])
        item.text=value
        return item
    header = ET.Element(f'{{{SVG_NS}}}g', {'id':'header'})
    y = 24
    if options['show_header']:
        lines=[]
        if options['show_about']:
            lines.append((scene['name'],20))
            if scene['description']:
                lines.append((scene['description'],12))
        if options['show_domain']:
            lines.append((scene['scope'],12))
        if options['show_filters']:
            lines.append(('Platforms: '+scene['platform']+(' · Search: '+scene['query'] if scene['query'] else ''),12))
        for value,size in lines:
            for line in textwrap.wrap(value,width=max(8,int((width-36)/(size*.65))),break_long_words=True) or ['']:
                text(header,18,y,line,size)
                y += size+6
    def legend(parent,x,y,legend_width,requested_height):
        group=element(parent,'g',id='legend')
        box=element(group,'rect',x=x,y=y,width=legend_width,height=1,fill=theme['legend'],stroke=theme['legend_border'])
        cursor=y+18
        for entry in scene['legend']:
            lines=textwrap.wrap(entry['label'],width=max(1,int((legend_width-38)/7)),break_long_words=True) or ['']
            from navigator_visuals import display_color
            swatch = element(group,'rect',x=x+8,y=cursor-10,width=10,height=10,
                             fill=display_color(entry['color'], theme['legend']))
            if options['theme'] == 'light':
                swatch.set('stroke', theme['legend_border'])
            for line in lines:
                text(group,x+26,cursor,line,11)
                cursor+=15
            cursor+=6
        needed=cursor-y+4
        actual=requested_height or needed
        box.set('height',str(needed))
        if requested_height:
            # Fit all legend content inside its requested rectangle without dropping entries.
            scale=min(1,requested_height/needed)
            group.set('transform',f'translate({x*(1-scale):g} {y*(1-scale):g}) scale({scale:g})')
        return actual
    has_legend=options['show_legend'] and bool(scene['legend'])
    if options['show_header'] and has_legend and not options['legend_undocked']:
        y += legend(header,18,y,min(width-36,pixels('legend_width')),pixels('legend_height')) + 10
    natural_header = y+6 if options['show_header'] else 0
    header_height = (pixels('header_height') or natural_header) if options['show_header'] else 0
    if natural_header and header_height < natural_header:
        scale=header_height/natural_header
        header.set('transform',f'scale({scale:g})')
    scaled_body_height=natural_height * width/natural_width
    height=pixels('height') or header_height+scaled_body_height
    detached_height=0
    if has_legend and options['legend_undocked']:
        detached_height=legend(root,pixels('legend_x'),pixels('legend_y'),pixels('legend_width'),pixels('legend_height'))
        if not pixels('height'):
            height=max(height,pixels('legend_y')+detached_height+12)
        if pixels('legend_x')+pixels('legend_width') > width or pixels('legend_y')+detached_height > height:
            raise ValueError('Undocked legend is outside the image; change its position/size or image dimensions.')
    if height-header_height < 40:
        raise ValueError('Image height must leave at least 40 pixels below the header for the matrix.')
    scale=min(width/natural_width,(height-header_height)/natural_height)
    background=element(root,'rect',x=0,y=0,width=width,height=height,fill=theme['canvas'])
    root.remove(background)
    root.insert(0,background)
    root.insert(1,header)
    body=ET.Element(f'{{{SVG_NS}}}g', {'id':'matrix','transform':f'translate(0 {header_height:g}) scale({scale:g}) translate(0 -100)'})
    # The first four base nodes are its background and three fixed header labels.
    for item in list(base)[4:]:
        for node in item.iter():
            if node.tag == f'{{{SVG_NS}}}text':
                node.set('font-family',FONTS[options['font']])
            if node.tag == f'{{{SVG_NS}}}rect' and 'stroke' in node.attrib and node.get('data-selected') != 'true':
                node.set('stroke',options['cell_border'])
        body.append(deepcopy(item))
    root.insert(2,body)
    root.set('width',f'{width/factor:g}'+options['unit'])
    root.set('height',f'{height/factor:g}'+options['unit'])
    root.set('viewBox',f'0 0 {width:g} {height:g}')
    description=element(root,'desc')
    description.text=APP_NAME+' matrix export; theme: '+options['theme']+'; sub-techniques: '+options['subtechniques']
    payload=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    try:
        ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError('SVG header/legend text contains characters that are invalid in XML; use JSON.') from error
    return payload
