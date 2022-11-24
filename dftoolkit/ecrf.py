# Copyright 2020-2022, Martin Renters
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
'''ECRF related classes'''

from reportlab.lib.colors import black, blue
from .rect import Rect
from .texttools import TextSegment, segment_into_lines, get_font_info, \
                       regular_font, strip_tags

def layout_text(text, width, attribs=None):
    '''Layout text as ECRFLabel elements, breaking lines at width
    '''
    if attribs is None:
        attribs = {}

    text = strip_tags(text)

    font = attribs.setdefault('font', regular_font())
    font_size = attribs.setdefault('font_size', 10)
    leading = attribs.setdefault('leading', font_size+4)

    elements = []
    ypos = 0

    # Create a label for each line of text
    for line in segment_into_lines(text, width, font, font_size):
        elements.append(ECRFLabel(Rect(0, ypos, width, ypos+leading),
                                  line, attribs=attribs))
        ypos += leading

    return elements

class ECRFLabel(Rect):
    '''A single line block of text for an eCRF'''
    def __init__(self, rect, label, attribs=None):
        if attribs is None:
            attribs = {}
        super().__init__(rect.left, rect.top, rect.right, rect.bottom)
        self.align = attribs.get('align', 'left')
        if isinstance(label, str):
            font = attribs.get('font', regular_font())
            font_size = attribs.get('font_size', 14)
            try_label = label
            while True:
                width, fragments = get_font_info(try_label, font)
                width = (width * font_size) / 1000.0
                # If the label fits, we're good
                if width <= rect.width-5:
                    break

                # Are we allowed to scale to fit?
                if attribs.get('allow_scaling', False):
                    scale = (rect.width-5)/width
                    width *= scale
                    font_size *= scale
                    self.scale_centered(scale)
                    break

                # Otherwise reduce by a letter at a time until it fits
                label = label[:-1]
                if not label:
                    break
                try_label = label + '\u2026'

            label = TextSegment(width, font_size, fragments)

        self.label = label

    @property
    def label_width(self):
        '''Returns the width of the label'''
        return self.label.width

    def set_align(self, align):
        '''Set label alignment'''
        self.align = align

    def draw(self, pdf_canvas, color=black):
        '''Draw ECRFLabel block on a PDF canvas'''
        pdf_canvas.setFillColor(color)
        self.label.draw(pdf_canvas, self, self.align)
        #pdf_canvas.setStrokeColor(blue)
        #pdf_canvas.rect(self.left, -self.top, self.width, -self.height)

    def __repr__(self):
        return 'ECRFLabel<(%d, %d, %d, %d), %s>' % (self.left, self.top,
                                                    self.right, self.bottom,
                                                    self.label)

class ECRFScreen(Rect):
    '''A screen block for an eCRF'''
    def __init__(self, rect, label):
        super().__init__(rect.left, rect.top, rect.right, rect.top+17)
        self.label = label

    def get_child_start(self):
        '''Returns the position the child should start at'''
        return Rect(self.left+5, self.bottom, self.right-5, self.bottom)

    def add_height(self, height):
        '''Expand the height of the screen'''
        self.bottom += height

    def draw(self, pdf_canvas):
        '''Draw ECRFScreen block on a PDF canvas'''
        pdf_canvas.setStrokeColor(black)
        pdf_canvas.setFillColor(black)
        pdf_canvas.setFont(regular_font(), 10)
        pdf_canvas.drawString(self.left, -(self.top+10), self.label)
        pdf_canvas.rect(self.left, -(self.top+12),
                        self.width, -(self.height-10))

    def __repr__(self):
        return 'ECRFScreen<(%d, %d, %d, %d), %s>' % (self.left, self.top,
                                                     self.right, self.bottom,
                                                     self.label)
class ECRFShading(Rect):
    '''A shaded block for an eCRF'''
    def __init__(self, rect, color='#e6e6dc'):
        super().__init__(rect.left, rect.top, rect.right, rect.top+5)
        self.color = color

    def get_child_start(self):
        '''Returns the position the child should start at'''
        return Rect(self.left+2, self.bottom, self.right-2, self.bottom)

    def add_height(self, height):
        '''Expand the height of the shading'''
        self.bottom += height

    def draw(self, pdf_canvas):
        '''Draw ECRFShading block on a PDF canvas'''
        pdf_canvas.setStrokeColor(black)
        pdf_canvas.setFillColor(self.color)
        pdf_canvas.rect(self.left, -self.top, self.width, -self.height,
                        stroke=0, fill=1)

    def __repr__(self):
        return 'ECRFShading<%d, %d, %d, %d>' % (self.left,
                                                self.top,
                                                self.right,
                                                self.bottom)
