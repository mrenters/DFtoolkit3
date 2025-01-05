#
# Copyright 2020-2025, Martin Renters
#
# This file is part of DFtoolkit
#
# DFtoolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DFtoolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DFtoolkit.  If not, see <http://www.gnu.org/licenses/>.
#

'''Unicode text line breaking and handling'''

import os
import unicodedata
from io import StringIO
from html.parser import HTMLParser
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class TagStripper(HTMLParser):
    '''Strips HTML tages from a string'''
    def __init__(self):
        super().__init__()
        self.text = StringIO()

    def handle_starttag(self, tag, attrs):
        '''convert <br/> tag to a space and strip all others'''
        if tag.lower() == 'br':
            self.text.write(' ')

    def handle_data(self, data):
        '''handle regular data by passing it through'''
        self.text.write(data)

    def get_data(self):
        '''returns resulting string'''
        self.close()
        return self.text.getvalue()

def strip_tags(text):
    '''remove HTML tags from a string'''
    stripper = TagStripper()
    stripper.feed(text)
    return stripper.get_data()

font_groups = {}
def enable_multilingual_fonts():
    '''Register and enable Noto fonts for international language support'''
    fontdir = os.path.join(os.path.dirname(__file__), 'fonts')
    noto_fonts = [
        ('Noto-Regular', 'NotoSans-Regular.ttf'),
        ('Noto-Regular-CJK', 'NotoSansCJKsc-Regular.ttf'),
        ('Noto-Italic', 'NotoSans-Italic.ttf'),
        ('Noto-Bold', 'NotoSans-Bold.ttf'),
        ('Noto-Bold-CJK', 'NotoSansCJKsc-Bold.ttf')
    ]
    for fontname, filename in noto_fonts:
        ttfont = TTFont(fontname, os.path.join(fontdir, filename))
        pdfmetrics.registerFont(ttfont)

    font_groups['Noto-Regular'] = ['Noto-Regular', 'Noto-Regular-CJK']
    font_groups['Noto-Bold'] = ['Noto-Bold', 'Noto-Bold-CJK']
    font_groups['Noto-Italic'] = ['Noto-Italic', 'Noto-Regular-CJK']

def bold_font():
    '''Get the name of the bold fonte: Helvetica-Bold or Noto-Bold'''
    if 'Noto-Bold' in font_groups:
        return 'Noto-Bold'
    return 'Helvetica-Bold'

def regular_font():
    '''Get the name of the regular font: Helvetica or Noto-Regular'''
    if 'Noto-Regular' in font_groups:
        return 'Noto-Regular'
    return 'Helvetica'

def italic_font():
    '''Get the name of the italic font: Helvetica-Oblique or Noto-Italic'''
    if 'Noto-Bold' in font_groups:
        return 'Noto-Italic'
    return 'Helvetica-Oblique'

def break_opportunities(text):
    '''Find places where line breaks could occur.

    Current implementation uses unicode categories or any
    character code over 0x3000.

    Should be extended to use Unicode Line Breaking Algorithm UAX #14 or
    Unicode Text Segmentation Algorithm UAX #29

    >>> list(break_opportunities('abc def'))
    [False, False, False, True, False, False, False]
    >>> list(break_opportunities('a國家'))
    [False, True, True]
    '''

    for character in text:
        yield ord(character) >= 0x3000 or \
              unicodedata.category(character) in ('Cc', 'Cf', 'Pe', 'Pf',
                                                  'Zl', 'Zp', 'Zs')

def break_fragments(text):
    '''Return text fragments where breaks can occur

    >>> list(break_fragments('abc def'))
    ['abc ', 'def']
    >>> list(break_fragments('a國家'))
    ['a國', '家']
    '''

    start = 0
    for pos, breakable in enumerate(break_opportunities(text)):
        if breakable:
            yield text[start:pos+1]
            start = pos+1

    if text and start < len(text):
        yield text[start:]

def get_font_info(text, font):
    '''Returns the width of a text as well as a list of (font, text) tuples'''
    current_fontname = None
    text_width = 0
    start_position = 0
    fragments = []
    fontgroup = font_groups.get(font)
    fontname = None

    if fontgroup:
        for position, char in enumerate(text):
            for fontname in fontgroup:
                fontmetrics = pdfmetrics.getFont(fontname)
                if ord(char) in fontmetrics.face.charWidths:
                    break

            text_width += fontmetrics.face.getCharWidth(ord(char))
            if current_fontname != fontname:
                if current_fontname is not None:
                    fragments.append((current_fontname,
                                      text[start_position:position]))
                    start_position = position
                current_fontname = fontname

        if text and start_position < len(text):
            fragments.append((current_fontname, text[start_position:]))

    else:
        fontmetrics = pdfmetrics.getFont(font)
        text_width = fontmetrics.stringWidth(text, 1000)
        fragments.append((font, text))

    return text_width, fragments

def coalesce_fragments(fragments):
    '''Coalesce (font, text) tuples if the fonts are the same'''
    last_font = None
    last_text = None
    new_fragments = []
    for font, text in fragments:
        if last_font != font:
            if last_font is not None:
                new_fragments.append((last_font, last_text))
                last_text = ''
            last_font = font
            last_text = text
        else:
            last_text += text
    if fragments:
        new_fragments.append((last_font, last_text))
    return new_fragments

def segment_into_lines(text, width, font, fontsize):
    '''Breaks text into lines no longer than width points, using font at
    size points. Font can be Noto which will use the various font files
    corresponding to different languages.

    Returns the space used in points and a list of (font, segment text) tuples
    '''
    cur_width = 0
    text_fragments = []
    for fragment in break_fragments(text):
        fragment_width, blocks = get_font_info(fragment, font)
        fragment_width = (fragment_width * fontsize)/1000.0
        if text_fragments and cur_width + fragment_width > width:
            yield TextSegment(cur_width, fontsize,
                              coalesce_fragments(text_fragments))
            cur_width = 0
            text_fragments = []

        # Don't start new line with a space
        if not cur_width and blocks[0][1] == ' ':
            continue
        text_fragments.extend(blocks)
        cur_width += fragment_width

    if text_fragments:
        yield TextSegment(cur_width, fontsize,
                          coalesce_fragments(text_fragments))

def escape_string(text):
    '''Escapes a string to make it HTML compatible'''
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def htmlify(text, font):
    '''Returns text with HTML font tags and properly escaped'''
    html = ''
    _, fragments = get_font_info(text, font)
    for face, textfrag in fragments:
        html += '<font face="{0}">{1}</font>'.format(face,
                                                     escape_string(textfrag))
    return html

def para(text, align=None):
    '''Returns text wrapped in <para></para> tags'''
    if align:
        html = '<para alignment="' + align + '">'
    else:
        html = '<para>'
    return html + text + '</para>'

def anchor(key, text):
    '''Returns an <a name=""/> string'''
    return '<a name="' + key + '"/>' + text

def href(key, text):
    '''Returns an <a href=""> wrapped string'''
    return '<a href="' + key + '" color="blue">' + text + '</a>'

class TextSegment:
    '''A representation of a line of text with multiple fonts'''
    def __init__(self, width, fontsize, fragments):
        self.width = width
        self.fontsize = fontsize
        self.fragments = fragments

    def draw(self, pdf_canvas, rect, align='left'):
        '''Draw a TextSegment onto a PDF Canvas'''
        textobject = pdf_canvas.beginText()
        if align == 'left':
            xpos = rect.left
        elif align == 'right':
            xpos = rect.right - self.width
        else:
            xpos = rect.left + (rect.width - self.width)/2

        textobject.setTextOrigin(xpos, -(rect.top+self.fontsize))
        for font, text in self.fragments:
            textobject.setFont(font, self.fontsize)
            textobject.textOut(text)

        pdf_canvas.drawText(textobject)

    def __repr__(self):
        return 'TextSegment<width=%d, fontsize=%d, text=%s>' % (self.width,
                                                                self.fontsize,
                                                                self.fragments)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
