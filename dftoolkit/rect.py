#
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
'''Rectangle operations'''

def rect_groups(rects):
    '''return a list of counts of adjacent rectangle groups'''
    if not rects:
        return [0]

    groups = []
    last_rect = None
    count = 0
    for rect in rects:
        if not last_rect:
            count = 1
        elif last_rect.is_adjacent_horizontal(rect):
            count += 1
        else:
            groups.append(count)
            count = 1

        last_rect = rect

    groups.append(count)
    return groups

class Rect:
    '''
    A Rectangle class that maintains the top left and height and width
    positions.
    '''
    def __init__(self, left, top, right, bottom):
        ''' Initial Rectangle '''
        self.left = self.top = self.right = self.bottom = 0
        self.set_values(left, top, right, bottom)

    def set_values(self, left, top, right, bottom):
        ''' Set Rectangle Points '''
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __eq__(self, other):
        return self.left == other.left and self.top == other.top and \
            self.right == other.right and self.bottom == other.bottom

    def __add__(self, rect):
        return Rect(min(self.left, rect.left),
                    min(self.top, rect.top),
                    max(self.right, rect.right),
                    max(self.bottom, rect.bottom))

    @property
    def top_left(self):
        ''' Returns top left coordinates '''
        return (self.left, self.top)

    @property
    def bottom_right(self):
        ''' Returns bottom right coordinates '''
        return (self.right, self.bottom)

    @property
    def width(self):
        '''Returns the width of a rectangle'''
        return self.right - self.left

    @property
    def height(self):
        '''Returns the height of a rectangle'''
        return self.bottom - self.top

    def translate(self, x_offset, y_offset):
        '''Move the rectange by x_offset, y_offset'''
        self.left += x_offset
        self.right += x_offset
        self.top += y_offset
        self.bottom += y_offset

    def expand(self, size):
        '''Returns a Rect that is larger by +size or smaller by -size'''
        return Rect(self.left-size, self.top-size,
                    self.right+size, self.bottom+size)

    def scale_centered(self, factor):
        '''Scale the rectangle around its center point'''
        center_x = (self.left + self.right)/2
        center_y = (self.top + self.bottom)/2
        half_width = self.width/2
        half_height = self.height/2
        self.left = center_x - half_width*factor
        self.right = center_x + half_width*factor
        self.top = center_y - half_height*factor
        self.bottom = center_y + half_height*factor

    def is_adjacent_horizontal(self, rect):
        ''' Checks whether rect is adjacent with self '''
        if rect.top-1 <= self.top <= rect.top+1 and \
            rect.bottom-1 <= self.bottom <= rect.bottom+1 and \
            rect.left-1 <= self.right < rect.right:
            return True
        return False

    def split_horizontal(self, num_boxes):
        ''' Splits a rect into num_boxes of equally spaced rects '''
        if num_boxes < 1:
            return []

        width = self.width // num_boxes
        extra = self.width % num_boxes
        left = self.left
        new_rects = []
        for _ in range(num_boxes):
            box_width = width + (1 if extra > 0 else 0)
            new_rects.append(Rect(left, self.top, left+box_width, self.bottom))
            left += box_width
            extra -= 1

        return new_rects

    def fit(self, width, height):
        '''Returns scale and x, y translation required to fit width, height'''
        # If no width or height, just leave everything as-is
        if width == 0 or height == 0:
            return (1, 0, 0)

        scale_x = float(self.width)/abs(width)
        scale_y = float(self.height)/abs(height)
        scale = scale_x if scale_x <= scale_y else scale_y

        translate_x = self.left + (self.width-(width*scale))/2
        translate_y = self.top

        return (scale, translate_x, translate_y)

    def __str__(self):
        return '(x=%d, y=%d, w=%d, h=%d)' % \
            (self.left, self.bottom, self.width, self.height)

    def __repr__(self):
        return '<Rect (%d,%d,%d,%d [%d,%d])>' % \
            (self.left, self.top, self.right, self.bottom,
             self.width, self.height)
