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
'''Routines for annotating CRFs'''

import logging

from datetime import date
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    TableStyle,
    LongTable,
    Spacer,
    Flowable,
    Paragraph
)
from reportlab.lib.colors import black, white, purple, HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import landscape, legal
from reportlab.lib.utils import ImageReader

from .rect import Rect
from .ecrf import ECRFLabel
from .texttools import bold_font, regular_font, italic_font, htmlify
from .rangelist import PlateList
from .flowables import Listing, ListEntry, watermark_page

# Colors for priority coding
# Active box, Active Text, Inactive Box, Inactive Text
priority_colors = [
    (black, white, black, white),
    (HexColor(0xB21616), white, HexColor(0xF39d9d), HexColor(0x505050)),
    (HexColor(0xED7D31), black, HexColor(0xF8CBAD), HexColor(0x505050)),
    (HexColor(0xFFC000), black, HexColor(0xFFE699), HexColor(0x505050)),
    (HexColor(0x70AD47), white, HexColor(0xC6E0B4), HexColor(0x505050)),
    (HexColor(0x4472C4), white, HexColor(0xB4C6E7), HexColor(0x505050)),
]

default_style = ParagraphStyle(
    'default',
    fontSize=8,
    leading=10
)

title_style = ParagraphStyle(
    'title',
    fontSize=12,
    leading=14,
    textColor=HexColor(0xC0C0C0)
)

class BeginXRef(Flowable):
    '''A Flowable that starts the variable cross reference section'''
    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        '''Generate a bookmark for the cross reference section'''
        key = 'XRef'
        canv = self.canv
        canv.bookmarkPage(key)
        canv.addOutlineEntry('Variable Cross-Reference', key, 0)
        canv.showOutline()

class BeginPlate(Flowable):
    '''A Flowable for marking the beginning of a plate'''
    def __init__(self, annotate, plate):
        super().__init__()
        self.annotate = annotate
        self.plate = plate

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        '''Tell the annotation object that we have started a new plate'''
        bookmark = 'P{0}'.format(self.plate.number)
        self.canv.bookmarkPage(bookmark)
        self.canv.addOutlineEntry('{0}: {1}'.format(self.plate.number,
                                                    self.plate.description),
                                  bookmark, 0)
        self.canv.showOutline()
        self.annotate.set_plate(self.plate)

class BeginPlatePage(Flowable):
    '''A Flowable for marking the beginning of a page'''
    def __init__(self, annotate, page):
        super().__init__()
        self.annotate = annotate
        self.page = page

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        '''Tell the annotation object that we have started a new page'''
        self.annotate.set_plate_page(self.page)

def make_field_entry(field, annotate):
    '''A Flowable for marking the beginning of a field'''
    num = \
        Paragraph('<para alignment="right">' +
                  htmlify(str(field.number), regular_font()) + \
                  '</para>', default_style)
    lbl = htmlify(field.name, bold_font()) + '<br/>' + \
        htmlify(field.moduleref.identifier, regular_font()) + '<br/>' + \
        htmlify(field.expanded_alias, italic_font())
    name = Paragraph(lbl, default_style)
    ftype = \
        Paragraph(htmlify(field.data_type + ' ({})'.format(field.store),
                          regular_font()) + '<br/>' + \
                  htmlify(field.data_format or '', italic_font()),
                  default_style)
    desc = \
        Paragraph(htmlify(field.expanded_description, regular_font()),
                  default_style)
    legal_vals = \
        Paragraph(htmlify(field.expanded_legal_range, regular_font()),
                  default_style)
    codes = [Paragraph(
        htmlify('{}\u2192'.format(code[0]), bold_font()) + \
        htmlify(code[1], italic_font()), default_style) \
        for code in field.codes]
    flowables = [num, name, ftype, desc, legal_vals, codes]
    list_entry = ListEntry(flowables)
    list_entry.set_callback(annotate.begin_field, field.number)
    list_entry.bookmark_page = 'P{}F{}'.format(field.plate.number, field.number)
    return list_entry

class AnnotateCRF:
    '''A class for handling the generation of annotated CRFs in PDF format'''
    def __init__(self, study):
        self.study = study
        self.doc = None
        self.gutter = 0.1*inch
        self.plate = None
        self.plate_background = None
        self.plate_page = None
        self.field_list = []
        self.crf_rect = None
        self.margins = None
        self.module_boundaries = False
        self.preferred_types = None
        self.watermark = None

    def set_plate(self, plate):
        '''A Callback to let us know that a new plate has started'''
        self.plate = plate
        img = self.study.api.background(plate,
                                        preferred_types=self.preferred_types)
        if img:
            if img.mode != 'P':
                img = img.convert('P')

            # Color version
            palette = [int(color*0.5+128) for color in img.getpalette()]
            img.putpalette(palette)
            #BW version
            #img = img.convert('L').point(lambda p: p*0.5+128)
        self.plate_background = img

    def set_plate_page(self, plate_page):
        '''A Callback to let us know that a new page of a plate has started'''
        self.plate_page = plate_page

    def begin_field(self, field_num):
        '''A Callback to let us know that a field is starting'''
        self.field_list.append(field_num)

    def show_module_boundaries(self, value):
        '''Turn off module boundaries on the CRF pages'''
        self.module_boundaries = value

    def set_preferred_types(self, value):
        '''Set preferred background types'''
        self.preferred_types = value

    def setup_document(self, output, pagesize=legal, watermark=None):
        '''Set up PDF document drawing areas'''
        self.watermark = watermark
        crf_listing_percent = 0.55
        lr_margin = 0.5*inch
        tb_margin = 0.75*inch

        self.doc = BaseDocTemplate(output,
                                   leftMargin=lr_margin,
                                   rightMargin=lr_margin,
                                   bottomMargin=tb_margin,
                                   topMargin=tb_margin,
                                   pagesize=landscape(pagesize))
        self.crf_rect = Rect(lr_margin, tb_margin,
                             lr_margin + \
                             self.doc.width * (1-crf_listing_percent) - \
                             self.gutter,
                             tb_margin+self.doc.height)

        self.margins = Rect(lr_margin, tb_margin, lr_margin + self.doc.width,
                            tb_margin + self.doc.height)


        # Frames
        crf_frames = [
            Frame(lr_margin + self.doc.width*(1-crf_listing_percent),
                  tb_margin,
                  self.doc.width*crf_listing_percent,
                  self.doc.height,
                  id='right',
                  showBoundary=0,
                  leftPadding=self.gutter/2)
        ]

        xref_frames = [
            Frame(lr_margin,
                  tb_margin,
                  self.doc.width/4,
                  self.doc.height,
                  id='col1',
                  showBoundary=0,
                  rightPadding=self.gutter/2),
            Frame(lr_margin + self.doc.width/4,
                  tb_margin,
                  self.doc.width/4,
                  self.doc.height,
                  id='col2',
                  showBoundary=0,
                  leftPadding=self.gutter/2,
                  rightPadding=self.gutter/2),
            Frame(lr_margin + 2*self.doc.width/4,
                  tb_margin,
                  self.doc.width/4,
                  self.doc.height,
                  id='col3',
                  showBoundary=0,
                  leftPadding=self.gutter/2,
                  rightPadding=self.gutter/2),
            Frame(lr_margin + 3*self.doc.width/4,
                  tb_margin,
                  self.doc.width/4,
                  self.doc.height,
                  id='col3',
                  showBoundary=0,
                  leftPadding=self.gutter/2,
                  rightPadding=self.gutter/2)
        ]

        templates = [
            PageTemplate(id='crf', frames=crf_frames,
                         onPageEnd=self.crf_page_header),
            PageTemplate(id='xref', frames=xref_frames,
                         onPageEnd=self.xref_page_header)
        ]
        self.doc.addPageTemplates(templates)

    def draw_labels(self, canvas, top_right_label):
        '''Draw the labels on the output page'''
        properties_left = {
            'align': 'left',
            'font_size': 10,
            'font': regular_font()
        }
        properties_centered = {
            'align': 'center',
            'font_size': 10,
            'font': regular_font()
        }
        properties_right = {
            'align': 'right',
            'font_size': 10,
            'font': regular_font()
        }
        tl_label = ECRFLabel(Rect(self.margins.left,
                                  self.margins.top-14,
                                  self.margins.left + self.crf_rect.width,
                                  self.margins.top-8),
                             self.study.study_name, properties_centered)
        tr_label = ECRFLabel(Rect(self.margins.left + self.margins.width / 2,
                                  self.margins.top-14,
                                  self.margins.right,
                                  self.margins.top-8),
                             top_right_label, properties_centered)
        bl_label = ECRFLabel(Rect(self.margins.left,
                                  self.margins.bottom + 4,
                                  self.margins.left + self.margins.width / 2,
                                  self.margins.bottom + 14),
                             date.today().isoformat(), properties_left)
        br_label = ECRFLabel(Rect(self.margins.left + self.margins.width / 2,
                                  self.margins.bottom + 4,
                                  self.margins.right,
                                  self.margins.bottom + 14),
                             'Page {}'.format(canvas.getPageNumber()),
                             properties_right)
        tl_label.draw(canvas, color=black)
        tr_label.draw(canvas, color=black)
        bl_label.draw(canvas, color=black)
        br_label.draw(canvas, color=black)

    def draw_priority_labels(self, canvas):
        '''Draw the priority labels on the bottom ot the page'''
        canvas.setFont(regular_font(), 8)
        middle = self.margins.left + self.margins.width / 2
        bottom = self.margins.bottom
        canvas.drawRightString(middle-55, -(bottom+20), 'Priority:')
        canvas.drawString(middle+5, -(bottom+15), 'detailed on this page')
        canvas.drawString(middle+5, -(bottom+25), 'detailed on another page')
        for i in range(1, 6):
            canvas.setFillColor(priority_colors[i][0])
            canvas.rect(middle+(i-6)*10, -(bottom+17), 10, 10, fill=1)
            canvas.setFillColor(priority_colors[i][1])
            canvas.drawCentredString(middle+(i-6)*10+5, -(bottom+15),
                                     '{0}'.format(i))
            canvas.setFillColor(priority_colors[i][2])
            canvas.rect(middle+(i-6)*10, -(bottom+27), 10, 10, fill=1)
            canvas.setFillColor(black)
            canvas.drawCentredString(middle+(i-6)*10+5, -(bottom+25),
                                     '{0}'.format(i))

    def crf_page_header(self, canvas, doc):
        '''Draw the CRF pages with headers and the CRF image'''
        canvas.saveState()
        canvas.translate(0, doc.pagesize[1])
        label = 'Plate {0}: {1}'.format(self.plate.number,
                                        self.plate.description)
        self.draw_labels(canvas, label)
        self.draw_priority_labels(canvas)

        bkgd_img = self.plate_background
        width, height, field_scale = self.plate_page.page_params(bkgd_img)
        scale, translate_x, translate_y = \
            self.crf_rect.expand(-2).fit(width, height)

        canvas.translate(translate_x, -translate_y)
        canvas.scale(scale, scale)
        canvas.setStrokeColor(black)
        canvas.setFillColor(black)

        if bkgd_img:
            canvas.drawImage(ImageReader(bkgd_img),
                             0, -bkgd_img.height)
            canvas.scale(field_scale, field_scale)

        canvas.setStrokeColor(HexColor(0xC0C0C0))
        canvas.rect(0, 0, width/field_scale, -height/field_scale)

        canvas.setStrokeColor(black)

        for element in self.plate_page.ecrf_elements:
            element.draw(canvas)

        modulerefs = {}
        for field in self.plate_page.user_fields:
            for element in field.ecrf_elements:
                element.draw(canvas)
            # blank out existing boxes
            canvas.setStrokeColor(white)
            canvas.setFillColor(white)
            for rect in field.rects or []:
                rect = rect.expand(2)
                canvas.rect(rect.left, -rect.top, rect.width, -rect.height,
                            fill=1)
            # draw new boxes
            canvas.setStrokeColor(black)
            for rect in field.rects or []:
                canvas.rect(rect.left, -rect.top, rect.width, -rect.height,
                            fill=1)

                # Calculate module bounding box
                module_bb = modulerefs.get(field.moduleref, rect)
                modulerefs[field.moduleref] = module_bb + rect

            if field.rects:
                color = 0 if field.number in self.field_list else 2
                box_color = priority_colors[field.priority][0 + color]
                txt_color = priority_colors[field.priority][1 + color]
                canvas.setStrokeColor(box_color)
                canvas.setFillColor(white)
                bounding_box = field.bounding_box.expand(2)
                canvas.rect(bounding_box.left, -bounding_box.top,
                            bounding_box.width, -bounding_box.height)
                bookmark = 'P{}F{}'.format(field.plate.number, field.number)
                canvas.linkRect(bookmark, bookmark,
                                (bounding_box.left, -bounding_box.top,
                                 bounding_box.right, -bounding_box.bottom),
                                relative=1)
                canvas.setStrokeColor(black)
                canvas.setFillColor(box_color)
                rect = field.rects[0].expand(2)
                canvas.rect(rect.left, -rect.top,
                            rect.width, -rect.height, fill=1)

                label = ECRFLabel(field.rects[0], str(field.number),
                                  {'align': 'center',
                                   'allow_scaling': True,
                                   'font_size': min(field.rects[0].height-4,
                                                    20),
                                   'font': bold_font()})
                label.draw(canvas, color=txt_color)


        if self.module_boundaries:
            canvas.setStrokeColor(purple)
            canvas.setDash([25, 5])
            for bbox in modulerefs.values():
                bbox = bbox.expand(6)
                canvas.rect(bbox.left, -bbox.top, bbox.width, -bbox.height)

        canvas.restoreState()

        self.field_list = []

        if self.watermark:
            watermark_page(doc, canvas, self.watermark)

    def xref_page_header(self, canvas, doc):
        '''Draw the XRef page header'''
        canvas.saveState()
        canvas.translate(0, doc.pagesize[1])
        self.draw_labels(canvas, 'Cross Reference')
        canvas.restoreState()

        if self.watermark:
            watermark_page(doc, canvas, self.watermark)

    def build_xref(self, xref):
        '''Build the variable cross reference section'''
        flowables = [NextPageTemplate('xref'), PageBreak(), BeginXRef()]

        table_style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0, 0), (-1, -1), 1, HexColor(0xE0E0E0))
        ])

        first_char = None
        rows = []
        # First sort case insentive and then case senstive on matches
        for variable in sorted(xref.keys(), key=lambda x: (x.lower(), x)):
            if first_char != variable[0].upper():
                if first_char is not None:
                    table = LongTable(rows, colWidths=[65, 90, 33, 32],
                                      splitByRow=1, repeatRows=2,
                                      hAlign='LEFT')
                    table.setStyle(table_style)
                    flowables.append(table)
                    flowables.append(Spacer(0, 20))
                first_char = variable[0].upper()
                rows = [[
                    Paragraph(htmlify(first_char, bold_font()), title_style),
                    Paragraph('', default_style),
                    Paragraph('', default_style),
                    Paragraph('', default_style)
                ], [
                    Paragraph(htmlify('Name', bold_font()), default_style),
                    Paragraph(htmlify('Description', bold_font()),
                              default_style),
                    Paragraph('<para alignment="right">' + \
                              htmlify('Plate', bold_font()) + \
                              '</para>', default_style),
                    Paragraph('<para alignment="right">' + \
                              htmlify('Field', bold_font()) + \
                              '</para>', default_style)
                ]]
            for fieldref in sorted(xref[variable], key=lambda x: \
                                   (x.plate.number, x.number)):
                bookmark = '#P{0}F{1}'.format(fieldref.plate.number,
                                              fieldref.number)
                rows.append([
                    Paragraph('<a href="' + bookmark + '" color="blue">' + \
                              htmlify(fieldref.name, regular_font()) + \
                              '</a>', default_style),
                    Paragraph(htmlify(fieldref.expanded_description,
                                      regular_font()),
                              default_style),
                    Paragraph('<para alignment="right">' + \
                              htmlify(str(fieldref.plate.number),
                                      regular_font()) + \
                              '</para>', default_style),
                    Paragraph('<para alignment="right">' + \
                              htmlify(str(fieldref.number), regular_font()) + \
                              '</para>', default_style)
                ])

        if rows:
            table = LongTable(rows, colWidths=[65, 90, 33, 32],
                              splitByRow=1, repeatRows=2,
                              hAlign='LEFT')
            table.setStyle(table_style)
            flowables.append(table)
        return flowables

    def build_pdf(self, plate_filter=PlateList(default_all=True)):
        '''Build the annotated CRF document'''
        columns = [
            {'name': 'Field', 'align': 'right', 'width': 25},
            {'name': 'Name/Module/Alias', 'width': 75},
            {'name': 'Type/Len/Fmt', 'width': 60, 'expandable': True},
            {'name': 'Description', 'width': 95, 'expandable': False},
            {'name': 'Legal Range', 'width': 100, 'expandable': True},
            {'name': 'Coding', 'width': 95, 'long': True, 'expandable': True}
        ]
        flowables = []
        first_page = True
        xref = {}
        for plate in self.study.user_plates:
            if plate.number not in plate_filter:
                continue
            if not first_page:
                flowables.append(PageBreak())
            first_page = False
            flowables.append(BeginPlate(self, plate))
            for page_num, page in enumerate(plate.pages):
                if page_num:
                    flowables.append(PageBreak())
                flowables.append(BeginPlatePage(self, page))
                self.plate_page = page
                listing = Listing(columns)
                listing.font_size = 8
                for field in page.user_fields:
                    entry = make_field_entry(field, self)
                    listing.add_row(entry)
                    varlist = xref.setdefault(field.name, [])
                    varlist.append(field)
                flowables.append(listing)

        if xref:
            flowables.extend(self.build_xref(xref))

        self.doc.title = 'Annotated CRFs for ' + self.study.study_name
        self.doc.author = 'DFtoolkit AnnotateCRF'
        self.doc.subject = 'Annotated CRFs for ' + self.study.study_name

        if flowables:
            self.doc.build(flowables)
        else:
            logging.warning('No pages to generate')
