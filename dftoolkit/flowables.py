#
# Copyright 2021-2022, Martin Renters
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
'''
This module supplies Flowable listing objects that can have multiple
columns, one of which can be longer than a single page. The Listing
module will break the table accordingly.
'''

import bisect
import math
import re
import logging

from pdfrw.toreportlab import makerl
from PIL import Image

from reportlab.platypus import Flowable
from reportlab.lib.colors import (
    black, white, blue, lightgrey, dimgray, HexColor
)
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch

from .ecrf import layout_text
from .fieldbase import multibox_numeric
from .rect import Rect
from .texttools import bold_font, regular_font

truncated_color = HexColor(0xFFC0E2)
missing_color = HexColor(0x88F45A)

def tick_size(largest, most_ticks):
    '''Calculate an appropriate size for each tick on the graph'''
    minimum = largest // most_ticks
    if minimum == 0:
        return 1
    magnitude = 10 ** math.floor(math.log(minimum, 10))
    residual = minimum // magnitude
    table = [1, 2, 3, 5, 7, 10]
    tick = table[bisect.bisect(table, residual)] if residual < 10 else 10
    return int(tick * magnitude)

def watermark_page(doc, canvas, text):
    '''Draw a watermark in the middle of the page'''
    canvas.saveState()
    # Account for 30 degree rotation for X axis shift
    canvas.translate(doc.pagesize[0]/2 + 20, doc.pagesize[1]/2)
    canvas.rotate(30)
    canvas.setFillColor(HexColor(0x00000008, hasAlpha=True))
    canvas.setStrokeColor(HexColor(0x00000020, hasAlpha=True))
    canvas.setFont(bold_font(), 120)
    canvas.drawCentredString(0, 0, text, mode=2)
    canvas.restoreState()

class AttachedDoc(Flowable):
    '''A Flowable for an attached document'''
    def __init__(self, obj, label=None, bookmark=None):
        super().__init__()
        self.obj = obj
        self.label = label
        self.bookmark = bookmark

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = availHeight
        return (availWidth, availHeight)

    def draw(self):
        '''Draw the attachment'''
        canv = self.canv

        if self.label:
            canv.setFont(regular_font(), 10)
            canv.drawCentredString(self.width/2, 6, self.label)

        attachment_box = Rect(0, 0, self.width, self.height-20)
        if isinstance(self.obj, Image.Image):
            width, height = self.obj.size
        else:
            width, height = self.obj.BBox[2], self.obj.BBox[3]

        scale, translate_x, translate_y = attachment_box.fit(width, height)

        canv.setStrokeColor(black)
        canv.setFillColor(black)

        if isinstance(self.obj, Image.Image):
            canv.translate(translate_x, self.height-translate_y)
            canv.scale(scale, scale)
            canv.drawImage(ImageReader(self.obj), 0, -height)
            canv.setStrokeColor(lightgrey)
            canv.rect(0, 0, width, -height)
        else:
            canv.translate(translate_x, -translate_y+20)
            canv.scale(scale, scale)
            canv.doForm(makerl(canv, self.obj))
            canv.setStrokeColor(lightgrey)
            canv.rect(0, 0, width, height)


        if self.bookmark:
            canv.bookmarkPage(self.bookmark)

class Section(Flowable):
    '''A Flowable that generates the outlines/bookmarks'''
    def __init__(self, title, bookmark=None):
        super().__init__()
        self.title = title
        self.bookmark = bookmark

    def wrap(self, availWidth, availHeight):
        # No space needed if we're only using the flowable for a bookmark
        if not self.title:
            return (0, 0)
        # Make sure we still have at least 3 inchs of space
        if availHeight < 3*inch:
            return(availWidth, 3*inch)
        self.width = availWidth
        return (availWidth, 46)

    def draw(self):
        '''Draw the title'''
        canv = self.canv
        if self.bookmark:
            canv.bookmarkPage(self.bookmark)

        if not self.title:
            return
        canv.setStrokeColor(dimgray)
        canv.setLineWidth(3)
        path = canv.beginPath()
        path.moveTo(0, 36)
        path.lineTo(self.width, 36)
        path.moveTo(0, 4)
        path.lineTo(self.width, 4)
        path.close()
        canv.drawPath(path)
        canv.setFont(bold_font(), 24)
#        canv.setStrokeColor(HexColor(0xF0F0F0))
#        canv.setFillColor(HexColor(0xF0F0F0))
#        canv.rect(0, 0, self.width, 30, fill=1)
        canv.setFillColor(dimgray)
        canv.drawCentredString(self.width/2, 12, self.title)

class AuditSection(Flowable):
    '''A Flowable that generates the audit header outlines/bookmarks'''
    def __init__(self, title, bookmark=None):
        super().__init__()
        self.title = title
        self.bookmark = bookmark

    def wrap(self, availWidth, availHeight):
        # Make sure we still have at least 3 inchs of space
        if availHeight < 1.5*inch:
            return(availWidth, 1.5*inch)
        self.width = availWidth
        self.height = 18
        return (availWidth, self.height)

    def draw(self):
        '''Draw the title'''
        canv = self.canv
        canv.setFont(bold_font(), 12)
        canv.setStrokeColor(HexColor(0xF0F0F0))
        canv.setFillColor(HexColor(0xF0F0F0))
        canv.rect(0, 0, self.width, self.height, fill=1)
        canv.setFillColor(black)
        canv.drawString(6, 4, self.title)
        if self.bookmark:
            canv.bookmarkHorizontal(self.bookmark, 0, 18)


class Bookmarks(Flowable):
    '''A Flowable that generates the outlines/bookmarks'''
    def __init__(self, bookmarks):
        super().__init__()
        self.bookmarks = bookmarks

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        '''Draw the outlines'''
        canv = self.canv
        for title, key, level in self.bookmarks:
            canv.addOutlineEntry(title, key, level, level >= 1)

        canv.showOutline()

class CRF(Flowable):
    '''A Flowable that displays a CRF page with data values'''
    def __init__(self, record, page, bkgd_image, context, callback=None):
        super().__init__()
        self.record = record
        self.page = page
        self.bkgd_image = bkgd_image
        self.context = context
        self.callback = callback

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = availHeight
        return (availWidth, availHeight)

    @property
    def blinded(self):
        '''Gets field blinded status'''
        return self.context.get('blinded', None)

    @property
    def exclude_datalisting(self):
        '''Should we exclude the data listing section'''
        return self.context.get('exclude_datalisting', False)

    def draw(self):
        '''Draws the flowable'''
        canv = self.canv

        # Callback to document to set the current record if we are the
        # first page in the plate
        if self.record.plate.first_page == self.page:
            if self.callback:
                self.callback(self.record)
            for bookmark in range(8):
                canv.bookmarkPage(self.record.keys_bookmark + \
                                  'B' + str(bookmark))

        canv.saveState()
        canv.translate(0, self.height)

        self.draw_crf_background()

        for field in self.page.user_fields:
            # If not an ecrf, make sure we fully erase boxes on background
            if not self.record.plate.ecrf:
                canv.setFillColor(white)
                canv.setStrokeColor(white)
                for rect in field.rects or []:
                    rect = rect.expand(2)
                    canv.rect(rect.left, -rect.top, rect.width, -rect.height,
                              fill=1)

            self.draw_field(field)

        canv.restoreState()
        self.draw_legend()

    def draw_boxes(self, field, stroke, fill):
        '''Draw the field boxes on the page in stroke/fill color'''
        canv = self.canv
        canv.setStrokeColor(stroke)
        canv.setFillColor(fill)
        for rect in field.rects or []:
            canv.rect(rect.left, -rect.top, rect.width, -rect.height,
                      fill=1)
        if not self.record.missing and not self.record.deleted \
            and not self.exclude_datalisting:
            linkname = self.record.keys_bookmark + '_{}'.format(field.number)
            bbox = field.bounding_box
            canv.linkRect(linkname, linkname,
                          (bbox.left, -bbox.top, bbox.right, -bbox.bottom),
                          relative=1)

    def draw_field(self, field):
        '''Draw the field values on the page'''
        canv = self.canv

        # If the record is missing(lost) or deleted, grey out field
        if self.record.missing or self.record.deleted:
            self.draw_boxes(field, dimgray, white)
            return

        # If the field is hidden and we're asked to blind, draw in black
        if field.blinded and self.blinded:
            if self.blinded == 'redact':
                self.draw_boxes(field, black, black)
            return

        # If the field is a missing value, draw in missing_color
        if self.record.field_missing_value(field.number):
            self.draw_boxes(field, blue, missing_color)
            return

        # No boxes, nothing to do
        if not field.rects:
            return

        # Draw box outlines
        self.draw_boxes(field, blue, white)

        value = self.record.field(field.number)

        # If value is blank, nothing to draw
        if not value:
            return

        canv.setFillColor(blue)
        canv.setFont(regular_font(), min(field.rects[0].height-4, 20))

        # Handle check/choice boxes
        if field.data_type == 'Check' or \
            (field.data_type == 'Choice' and len(field.rects) > 1):
            self.draw_check_choice(field, value)

        # Dates need to have formatting stripped
        elif field.data_type == 'Date' and len(field.rects) > 1:
            self.draw_date(field, value)

        # Times with two boxes
        elif field.data_type == 'Time' and len(field.rects) > 1:
            self.draw_time(field, value)

        elif field.data_type == 'Number' and len(field.rects) == 2 and \
            field.data_format == 'nn:nn' and (':' in value or value == ''):
            self.draw_numeric_time(field, value)

        # Number field with multiple boxes
        elif field.data_type == 'Number' and len(field.rects) > 1:
            self.draw_numeric_multibox(field, value)

        # Non-choice multibox values
        elif field.data_type != 'Choice' and len(field.rects) > 1:
            error = 'truncated value' if len(value) > len(field.rects) else None
            if error:
                logging.warning('%s Field %d: %s (value="%s", boxes=%d)',
                                self.record.keys, field.number, error, value,
                                len(field.rects))
            self.draw_multibox_value(field, value, error)

        else:
            if field.data_type == 'Choice':
                _, value = field.decode(value)
            self.draw_singlebox_value(field, value)

    def draw_check_choice(self, field, value):
        '''Draws an X in a check or choicebox field'''
        canv = self.canv
        box, _ = field.decode(value)
        if box is not None:
            # Draw X in the box
            rect = field.rects[box]
            canv.saveState()
            canv.setLineWidth(3)
            path = canv.beginPath()
            path.moveTo(rect.left, -rect.top)
            path.lineTo(rect.right, -rect.bottom)
            path.moveTo(rect.left, -rect.bottom)
            path.lineTo(rect.right, -rect.top)
            path.close()
            canv.drawPath(path)
            canv.restoreState()

    def draw_date(self, field, value):
        '''Draw a multibox date'''
        cleaned = re.sub('[^0-9A-Za-z]', '', value)
        self.draw_multibox_value(field, cleaned)

    def draw_time(self, field, value):
        '''Draw a multibox time'''
        cleaned = re.sub('[^0-9]', '', value)
        self.draw_multibox_value(field, cleaned)

    def draw_numeric_time(self, field, value):
        '''Draw a numeric time field'''
        if value == '':
            value = '  :  '
        cleaned = value.split(':')
        self.draw_multibox_value(field, cleaned)

    def draw_numeric_multibox(self, field, value):
        '''Draw a numeric time field'''
        rvalue, error = multibox_numeric(field.data_format, value, field.rects)

        if error:
            logging.warning('%s Field %d: %s (value="%s", format="%s")',
                            self.record.keys, field.number, error, value,
                            field.data_format)

        self.draw_multibox_value(field, rvalue, error)

    def draw_multibox_value(self, field, value, error=None):
        '''Draw a multi-box value'''
        canv = self.canv
        for box, rect in enumerate(field.rects):
            if error:
                canv.setFillColor(truncated_color)
                canv.rect(rect.left, -rect.top, rect.width, -rect.height,
                          fill=1)
                canv.setFillColor(blue)
            if box < len(value):
                canv.drawCentredString(rect.left + rect.width/2,
                                       -(rect.top+(4*rect.height/5)),
                                       value[box])

    def draw_singlebox_value(self, field, value):
        '''Draw a value in a single box'''
        canv = self.canv
        rect = field.rects[0]
        attribs = {
            'font_size': min(20, rect.height-4)
        }
        if field.data_type != 'String':
            attribs['align'] = 'center'

        elements = layout_text(value, rect.width-10, attribs)

        # Nothing to draw?
        if not elements:
            return

        truncated = list(filter(lambda e: e.label_width >= rect.width,
                                elements))
        if elements[-1].bottom + rect.top > rect.bottom or truncated:
            canv.setStrokeColor(blue)
            canv.setFillColor(truncated_color)
            canv.rect(rect.left, -rect.top, rect.width, -rect.height,
                      fill=1)
            logging.warning('%s Field %d: truncated value displayed on CRF.',
                            self.record.keys, field.number)
            # Force left alignment if truncated
            for element in elements:
                element.set_align('left')

        # Clip the path because the elements may exceed the field rect
        # if no suitable breakpoints can be found
        canv.saveState()
        path = canv.beginPath()
        path.rect(rect.left, -rect.top, rect.width, -rect.height)
        path.close()
        canv.clipPath(path, stroke=0)
        for element in elements:
            element.translate(rect.left + 5, rect.top)
            if element.bottom > rect.bottom:
                break
            element.draw(canv, blue)

        canv.restoreState()

    def draw_crf_background(self):
        '''Draws the CRF background and sets up scaling for fields'''
        canv = self.canv
        crf_box = Rect(0, 0, self.width, self.height-20)
        bkgd_img = self.bkgd_image

        width, height, field_scale = self.page.page_params(bkgd_img)
        scale, translate_x, translate_y = crf_box.fit(width, height)

        canv.translate(translate_x, -translate_y)
        canv.scale(scale, scale)
        canv.setStrokeColor(black)
        canv.setFillColor(black)
        if bkgd_img:
            canv.drawImage(ImageReader(bkgd_img), 0, -bkgd_img.height)
            canv.scale(field_scale, field_scale)

        canv.setStrokeColor(lightgrey)
        canv.rect(0, 0, width/field_scale, -height/field_scale)

        for element in self.page.ecrf_elements:
            element.draw(canv)

        for field in self.page.user_fields:
            for element in field.ecrf_elements:
                element.draw(canv)

    def draw_legend(self):
        '''Draws the color legend at the bottom of the CRF page'''
        canv = self.canv
        canv.saveState()
        canv.setStrokeColor(black)
        canv.setFillColor(black)
        if self.record.missing or self.record.deleted:
            canv.setFont(regular_font(), 8)
            canv.drawString(0, 2,
                            self.record.missing_reason if self.record.missing \
                            else self.record.deleted_reason)
            canv.setFont(bold_font(), 60)
            canv.setLineWidth(2)
            canv.translate(self.width/2, self.height/2)
            canv.rotate(30)
            canv.drawCentredString(30, 0,
                                   'NO DATA' if self.record.missing else \
                                   'DELETED', mode=1)
        else:
            canv.setFont(bold_font(), 8)
            canv.drawString(0, 2, 'Legend:')
            canv.setFont(regular_font(), 8)
            canv.setLineWidth(0.2)
            labels = [
                (missing_color, 40, 'Missing Value'),
                (truncated_color, 112,
                 'Insufficient Box Space, Displayed Value Truncated')
            ]
            if self.blinded == 'redact':
                labels.append((black, 330, 'Internal/Administrative Data'))
            for color, xpos, label in labels:
                canv.setFillColor(color)
                canv.rect(xpos, 0, 10, 10, fill=1)
                canv.setFillColor(black)
                canv.drawString(xpos+13, 2, label)


        canv.restoreState()

class ListEntry(Flowable):
    '''A ListEntry (i.e. row) in a Listing'''
    def __init__(self, flowables):
        super().__init__()
        self.flowables = flowables
        self.height_min_needed = 0
        self.height = 0
        self.listing = None
        self.wrap_called = False
        self.was_split = False
        self.continuation = False
        self.bookmark = None
        self.bookmark_page = None
        self.callback = None
        self.callback_args = None

    def set_parent(self, listing):
        '''Associate this ListEntry with a Listing Object'''
        self.listing = listing
        if len(listing.columns) != len(self.flowables):
            raise ValueError('incorrect number of columns')

    def set_callback(self, callback, args):
        '''Set a callback funcation that gets called when this entry is drawn'''
        self.callback = callback
        self.callback_args = args

    @property
    def min_height(self):
        '''Returns the minimum height. Try and keep short rows together'''
        return self.height if (self.height - self.height_min_needed) < 144 \
            else self.height_min_needed

    def wrap(self, availWidth, availHeight):
        if self.wrap_called:
            return (availWidth, self.height)

        self.height = 0
        self.height_min_needed = 0
        for colnum, column in enumerate(self.listing.columns):
            width = column.get('width')
            islong = column.get('long', False)
            coldata = self.flowables[colnum]
            if not isinstance(coldata, (list, tuple)):
                coldata = [coldata]

            height = 0
            for row in coldata:
                _, row_height = row.wrap(width, availHeight-height)
                height += row_height

            if not islong:
                self.height_min_needed = max(self.height_min_needed, height)

            self.height = max(self.height, height)

        self.wrap_called = True
        return (availWidth, self.height)

    def split(self, availWidth, availheight):
        flowables1 = [[]] * len(self.listing.columns)
        flowables2 = [[]] * len(self.listing.columns)
        split1 = ListEntry(flowables1)
        split2 = ListEntry(flowables2)
        for colnum, column in enumerate(self.listing.columns):
            width = column.get('width')
            islong = column.get('long', False)
            coldata = self.flowables[colnum]
            if not isinstance(coldata, (list, tuple)):
                coldata = [coldata]

            if not islong:
                flowables1[colnum] = coldata
                flowables2[colnum] = coldata
                continue

            available = availheight
            for row_num, row in enumerate(coldata):
                _, row_height = row.wrap(width, max(self.min_height,
                                                    available))
                if row_height < available:
                    flowables1[colnum].append(row)
                    available -= row_height
                    split1.height += row_height
                else:
                    splits = row.split(width, available)
                    if len(splits) >= 2:
                        flowables1[colnum].append(splits[0])
                        split1.height += splits[0].height
                        splits = splits[1:]
                    elif not splits:
                        splits = [row]

                    splits.extend(coldata[row_num+1:])
                    for flowable in splits:
                        flowables2[colnum].append(flowable)
                        _, row_height = flowable.wrap(width, 1000)
                        split2.height += row_height

                    break

        split1.was_split = True
        split1.callback = self.callback
        split1.callback_args = self.callback_args
        split1.bookmark = self.bookmark
        split1.bookmark_page = self.bookmark_page
        split1.height_min_needed = self.height_min_needed
        split1.height = max(split1.height, self.height_min_needed)

        split2.continuation = True
        split2.height_min_needed = self.height_min_needed
        split2.height = max(split2.height, self.height_min_needed)
        return [split1, split2]

    def draw(self):
        '''Draw outself on the canvas'''
        xpos = 0
        canv = self.canv

        # If we have a callback, call it now
        if self.callback:
            self.callback(self.callback_args)

        # If we have a bookmark, output it now
        if self.bookmark:
            canv.bookmarkHorizontal(self.bookmark, 0, self.height)
        if self.bookmark_page:
            canv.bookmarkPage(self.bookmark_page)

        for colnum, column in enumerate(self.listing.columns):
            coldata = self.flowables[colnum]
            if not isinstance(coldata, (list, tuple)):
                coldata = [coldata]

            height = self.height
            for row in coldata:
                height -= row.height
                row.drawOn(canv, xpos, height)

            xpos += column.get('width') + self.listing.column_gap

class Listing(Flowable):
    '''A table-like object of ListEntrys that can break rows across pages'''
    column_gap = 10
    line_height = 5
    header_height = line_height*2 + 12

    def __init__(self, columns):
        super().__init__()
        self.columns = columns
        self.height = self.header_height
        self.rows = []
        self.font_size = 10

    def add_row(self, child):
        '''Add a ListEntry to outselves'''
        child.set_parent(self)
        self.rows.append(child)

    def adjust_widths(self, avail_width):
        '''Adjusts expanable columns to use up extra available space'''
        needed_width = 0
        expandables = []
        for column in self.columns:
            needed_width += column.get('width', 10)
            if column.get('expandable', False):
                expandables.append(column)

        if not expandables:
            return

        needed_width += self.column_gap * (len(self.columns)-1)
        change_width = (avail_width - needed_width) / len(expandables)
        for column in expandables:
            column['width'] = column.get('width', 10) + change_width


    def wrap(self, availWidth, availHeight):
        if not self.rows or not self.columns:
            return (availWidth, self.header_height)

        self.adjust_widths(availWidth)

        self.width = availWidth
        self.height = self.header_height
        for row in self.rows:
            _, row_height = row.wrap(availWidth, 0)
            self.height += row_height + self.line_height

        return (availWidth, self.height)

    def split(self, availWidth, availheight):
        if not self.rows:
            return [self]

        if availheight <= self.header_height + self.rows[0].height_min_needed:
            return []

        split1 = Listing(self.columns)
        split1.font_size = self.font_size
        split2 = Listing(self.columns)
        split2.font_size = self.font_size
        for num, row in enumerate(self.rows):
            available = availheight - split1.height - self.line_height
            # If the whole row fits, add it to the split1 segment
            if row.height <= available:
                split1.add_row(row)
                split1.height += row.height + self.line_height
                continue

            if row.min_height >= available:
                # Even the minimum won't fit, push to next
                row_splits = self.rows[num:]
            else:
                # Split the ListEntry, possibly still adding part to the
                # split1 segment, the rest of the ListEntry and all remaining
                # ones move to the split2 segment
                row_splits = row.split(availWidth,
                                       availheight - split1.height - \
                                       self.line_height)

                split1.add_row(row_splits[0])
                split1.height += row_splits[0].height + self.line_height

                row_splits = row_splits[1:]     # Kill off first element
                row_splits.extend(self.rows[num+1:])

            for row2 in row_splits:
                split2.add_row(row2)
                split2.height += row2.height + self.line_height
            break

        return [split1, split2]

    def draw(self):
        '''Draw the Listing'''
        canv = self.canv
        xpos = 0

        if not self.rows:
            return

        height = self.height

        # Draw top and bottom lines
        canv.setStrokeColor(HexColor(0xE0E0E0))
        path = canv.beginPath()
        path.moveTo(0, height - 2)
        path.lineTo(self.width, height - 2)
        path.moveTo(0, height - self.header_height + 2)
        path.lineTo(self.width, height - self.header_height + 2)
        path.close()
        canv.drawPath(path)

        canv.setStrokeColor(black)
        canv.setFillColor(black)
        canv.setFont(bold_font(), self.font_size)
        for column in self.columns:
            width = column.get('width', 10)
            name = column.get('name', '')
            align = column.get('align', 'left')
            if align == 'right':
                canv.drawRightString(xpos+width, height-15, name)
            else:
                canv.drawString(xpos, height-15, name)
            xpos += width + self.column_gap

        height -= self.header_height
        for row in self.rows:
            canv.setStrokeColor(black)
            row.drawOn(canv, 0, height - row.height)
            height -= row.height + self.line_height

            # Draw line at bottom of row
            if row.was_split:
                canv.setDash([1, 8])
            canv.setStrokeColor(HexColor(0xE0E0E0))
            path = canv.beginPath()
            path.moveTo(0, height + 2)
            path.lineTo(self.width, height + 2)
            path.close()
            canv.drawPath(path)

#####################################################################
# QCChart
#####################################################################
class QCChart(Flowable):
    '''A QC Chart for report cards'''
    def __init__(self, qc_types, metrics, grade=True):
        super().__init__()
        self.qc_types = qc_types
        self.metrics = metrics
        self.grade = grade

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = len(self.qc_types)*14 + 28
        return (availWidth, self.height)

    def draw_grade(self, canvas):
        '''draw the letter grade'''
        grades = ['A+', 'A', 'A-', 'B', 'C', 'D']
        breakpoints = [0.2, 0.5, 1, 2, 3]
        qcs_per_pt = self.metrics.qcs_per_patient
        letter = grades[bisect.bisect(breakpoints, qcs_per_pt)]
        mid_y = self.height/2
        canvas.setFont('Helvetica', 72)
        canvas.setFillColor(HexColor('#1565C0'))
        canvas.drawCentredString(60, mid_y-30, letter, mode=2)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(black)
        canvas.drawCentredString(60, mid_y-56,
                                 'A+: <0.2; A: 0.2 < 0.5; A-: 0.5 < 1.0')
        canvas.drawCentredString(60, mid_y-65,
                                 'B: 1.0 < 2.0; C: 2.0 < 3.0; D: \u2265 3.0')
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(60, mid_y-45, str(qcs_per_pt))

    def draw_score(self, canvas):
        '''draw a box with a numeric score'''
        qcs_per_pt = self.metrics.qcs_per_patient
        mid_y = self.height/2
        canvas.setFont('Helvetica', 30)
        canvas.setFillColor(HexColor('#1565C0'))
        canvas.drawCentredString(60, mid_y-15, str(qcs_per_pt), mode=2)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(black)
        canvas.drawCentredString(60, mid_y-45, 'Queries/Subject')

    def draw(self):
        '''draws the QCChart'''
        canvas = self.canv
        canvas.saveState()
        labels = [label for _, label in self.qc_types]
        values = [self.metrics.qc_types[qc_type] \
            for qc_type, _ in self.qc_types]

        canvas.setStrokeColor(black)
        canvas.setLineWidth(1)
        canvas.rect(0, 0, 120, self.height)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(black)
        canvas.drawCentredString(60, self.height-25, 'Your Site')
        canvas.drawCentredString(60, self.height-37, 'Queries/Subject Score')

        if self.grade:
            self.draw_grade(canvas)
        else:
            self.draw_score(canvas)

        tick = tick_size(max(values), 10)

        min_x = 215
        max_x = self.width - 20
        min_y = 20
        path = canvas.beginPath()
        path.moveTo(min_x, self.height)
        path.lineTo(min_x, min_y)
        path.lineTo(max_x, min_y)
        canvas.drawPath(path)
        canvas.setFont('Helvetica', 10)
        step = float(max_x - min_x)/10
        for i in range(0, 11):
            x_pos = min_x + (step*i)
            path = canvas.beginPath()
            path.moveTo(x_pos, min_y)
            path.lineTo(x_pos, min_y-5)
            canvas.drawPath(path)
            canvas.drawCentredString(min_x + (step*i), 5, str(tick*i))

        for i, label in enumerate(labels):
            y_pos = (min_y+5) + (i*14)
            bar_len = (values[i]/(10*tick))*(max_x-min_x)
            canvas.setFillColor(black)
            canvas.drawRightString(min_x-5, y_pos, label[0:18])
            canvas.drawString(min_x + bar_len + 5, y_pos, str(values[i]))
            canvas.setFillColor(HexColor('#1565C0'))
            canvas.rect(min_x, y_pos-2, bar_len, 11, fill=True)

        canvas.restoreState()

#####################################################################
# RankingChart
#####################################################################
class RankingChart(Flowable):
    '''a site ranking chart for report cards'''
    def __init__(self, rankings, my_rank, grade=True):
        super().__init__()
        self.my_rank = my_rank     # 1-based
        self.rankings = rankings
        self.grade = grade

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = 140
        return (availWidth, self.height)

    def draw_grade(self, completeness):
        '''draw the letter grade'''
        canvas = self.canv
        grades = ['D', 'C', 'B', 'A-', 'A', 'A+']
        breakpoints = [90, 95, 97, 98, 99]
        letter = grades[bisect.bisect(breakpoints, completeness)]
        canvas.setFont('Helvetica', 72)
        canvas.drawCentredString(60, 40, letter, mode=2)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(black)
        canvas.drawCentredString(
            60, 14, 'A+: >99; A: 98 \u2264 99; A-: 97 \u2264 98;')
        canvas.drawCentredString(
            60, 5, 'B: 95 \u2264 97; C: 90 \u2264 95; D: \u2264 90')
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(60, 25, '{0:6.2f}%'.format(completeness))

    def draw(self):
        '''draws the QCChart'''
        # We list a maximum of 10 sites, so if we're higher than that
        # skip rank 10 to us and make us the last one
        if self.my_rank > 10:
            ranking_list = self.rankings[0:9]
            ranking_list.append(self.rankings[self.my_rank-1])
            my_rank = 10
        else:
            ranking_list = self.rankings[0:10]
            my_rank = self.my_rank

        _, metrics = ranking_list[my_rank-1]
        completeness = metrics.percent_complete

        canvas = self.canv
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setStrokeColor(black)
        canvas.setFillColor(black)
        canvas.drawCentredString(60, 115, 'Your Site')
        canvas.drawCentredString(60, 103, 'Completeness Score')
        canvas.setFillColor(HexColor('#1565C0'))
        if self.grade:
            self.draw_grade(completeness)
        else:
            canvas.setFont('Helvetica', 30)
            canvas.drawCentredString(60, 55, str(completeness), mode=2)
            canvas.setFont('Helvetica-Bold', 10)
            canvas.setFillColor(black)

        # Column headers
        canvas.drawRightString(150, self.height-14, 'Rank')
        canvas.drawString(155, self.height-14, 'Country')
        canvas.drawString(250, self.height-14, 'Site')
        canvas.drawRightString(500, self.height-14, 'Records')
        canvas.drawRightString(564, self.height-14, '%Complete')

        y_pos = 112
        canvas.setFont('Helvetica', 10)
        for rank, (site, metrics) in enumerate(ranking_list, 1):
            if rank == my_rank:
                canvas.setFont('Helvetica-Bold', 10)
                canvas.setFillColor(HexColor('#1565C0'))
            else:
                canvas.setFont('Helvetica', 10)
                canvas.setFillColor(black)
            canvas.drawRightString(150, y_pos, str(metrics.global_rank))
            canvas.drawString(155, y_pos, site.decoded_country)
            canvas.drawString(250, y_pos, site.name[0:35])
            canvas.drawRightString(500, y_pos, str(metrics.nrecs))
            canvas.drawRightString(564, y_pos, str(metrics.percent_complete))
            y_pos = y_pos-12

        canvas.setLineWidth(1)
        path = canvas.beginPath()
        path.moveTo(0, 0)
        path.lineTo(0, self.height)
        path.lineTo(120, self.height)
        path.lineTo(120, 0)
        path.close()
        canvas.drawPath(path)
        canvas.restoreState()
