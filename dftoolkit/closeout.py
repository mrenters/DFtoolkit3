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
'''Routines for generating closeout PDFs'''

import io
import logging
import os
from time import strftime, localtime

from pikepdf import Pdf

from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj

from PIL import Image

from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    PageBreak,
    Paragraph,
    Spacer
)
from reportlab.lib.colors import black, blue, lightgrey
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

from .audit import AuditOps
from .rect import Rect
from .ecrf import ECRFLabel
from .texttools import bold_font, regular_font, htmlify, para, href
from .flowables import (
    AttachedDoc, AuditSection, Bookmarks, CRF, Listing, ListEntry,
    Section, watermark_page
)
from .utils import format_pid

def build_attachment_pdf(record, attachment):
    '''Build flowables for PDF pages'''
    flowables = []
    primary = 'Primary' if attachment.primary else 'Secondary'
    mtime = strftime('%Y-%m-%d %H:%M:%S',
                     localtime(attachment.timestamp))
    try:
        pages = PdfReader(fdata=attachment.data).pages
        for page_num, page in enumerate([pagexobj(x) for x in pages]):
            label = 'Attached Document {}, ({}, PDF, Page {} of {}), ' \
                'dated {}'.format(attachment.raster, primary, page_num+1,
                                  len(pages), mtime)
            flowables.append(AttachedDoc(page, label))
    except Exception:
        logging.warning('%s incompatible PDF %s', record.keys,
                        attachment.raster)

    return flowables

def build_attachment_image(record, attachment):
    '''Build flowables for normal image'''
    flowables = []
    primary = 'Primary' if attachment.primary else 'Secondary'
    mtime = strftime('%Y-%m-%d %H:%M:%S',
                     localtime(attachment.timestamp))
    try:
        img = Image.open(io.BytesIO(attachment.data))
        label = 'Attached Document {}, ({}, Single Image), ' \
                'dated {}'.format(attachment.raster, primary, mtime)
        flowables.append(AttachedDoc(img, label))

    except Exception:
        logging.warning('%s incompatible attachment  %s',
                        record.keys, attachment.raster)

    return flowables

def build_audit_chrono(record, audit_ops):
    '''Build the chronological audit section'''
    flowables = [Section('Chronological Audit', record.keys_bookmark+'AU')]
    last = None
    listing = None
    for rec in audit_ops:
        # If nothing to report, skip this
        if not rec.ops:
            continue
        if last != (rec.who, rec.tdate, rec.ttime):
            last = (rec.who, rec.tdate, rec.ttime)
            listing = Listing([
                {'name': 'Field', 'width': 40, 'align': 'right'},
                {'name': 'Description', 'width': 130},
                {'name': 'Operation', 'width': 100, 'long': True,
                 'expandable': True}
            ])
            flowables.append(AuditSection(
                '{} {} {}'.format(rec.tdate, rec.ttime, rec.who)))
            flowables.append(listing)
            flowables.append(Spacer(0, 10))

        if rec.fnum < 0:
            field = '- .'
        elif rec.fnum == 0:
            field = ''
        else:
            field = str(rec.fnum) + '.'

        entry = ListEntry([
            Paragraph(para(htmlify(field, regular_font()), 'right')),
            Paragraph(htmlify(rec.desc, regular_font())),
            [Paragraph(op) for _, op in rec.ops]
        ])
        listing.add_row(entry)

    return flowables

def build_audit_byfield(record, audit_ops, blinded):
    '''Build the chronological audit section'''
    flowables = [Section('Audit by Field', record.keys_bookmark + 'FA')]
    for field in record.plate.user_fields:

        entry_bookmark = record.keys_bookmark + '_{}AF'.format(field.number)

        # If this field blinded?
        if field.blinded and blinded == 'skip':
            continue
        if field.blinded and blinded == 'redact':
            flowables.append(AuditSection(
                '{}. Internal Use Only Field'.format(field.number),
                entry_bookmark))
            flowables.append(Spacer(0, 10))
            continue

        flowables.append(AuditSection('{}. {}'.format(field.number,
                                                      field.description),
                                      entry_bookmark))

        listing = Listing([
            {'name': 'Date', 'width': 60},
            {'name': 'Time', 'width': 50},
            {'name': 'User', 'width': 40},
            {'name': 'Operation', 'width': 100, 'long': True,
             'expandable': True}
        ])
        flowables.append(listing)
        flowables.append(Spacer(0, 10))

        for rec in audit_ops:
            if rec.funiqueid not in (0, field.unique_id):
                continue

            # If nothing reportable happened, skip this entry
            if not rec.ops:
                continue

            entry = ListEntry([
                Paragraph(htmlify(rec.tdate, regular_font())),
                Paragraph(htmlify(rec.ttime, regular_font())),
                Paragraph(htmlify(rec.who, regular_font())),
                [Paragraph(op) for _, op in rec.ops]
            ])
            listing.add_row(entry)


    return flowables

class CloseoutPDF:
    '''Generates a closeout PDF'''
    def __init__(self, context, pid):
        self.context = context
        self.doc = None
        self.pid = pid
        self.record = None

    def set_record(self, record):
        '''Callback to set the record we are currently processing'''
        logging.debug('rendering record: %s', record.keys)
        self.record = record

    @property
    def study(self):
        '''returns study object'''
        return self.context.get('study')

    @property
    def sql(self):
        '''returns sql object'''
        return self.context.get('sql')

    @property
    def need_attachments(self):
        '''Do we need an attachment section'''
        record = self.record
        return record.plate_num in self.context.get('attachments', []) and \
            record.has_attachment(self.context.get('secondaries', False))

    @property
    def blinded(self):
        '''Gets field blinded status'''
        return self.context.get('blinded', None)

    @property
    def exclude_datalisting(self):
        '''Should we exclude the data listing section'''
        return self.context.get('exclude_datalisting', False)

    @property
    def exclude_field_audit(self):
        '''Should we exclude the field audit section'''
        return self.context.get('exclude_field_audit', False)

    @property
    def exclude_chronological_audit(self):
        '''Should we exclude the chronological audit section'''
        return self.context.get('exclude_chronological_audit', False)

    def page_header(self, canv, doc):
        '''Draw the page header and footer'''
        if not self.record:
            return
        properties_centered_bold = {
            'align': 'center',
            'font_size': 10,
            'font': bold_font()
        }
        properties_left = {
            'align': 'left',
            'font_size': 10,
            'font': bold_font()
        }
        canv.saveState()
        canv.translate(0, doc.pagesize[1])

        # Box around header
        canv.setStrokeColor(lightgrey)
        canv.setLineWidth(2)
        canv.rect(inch, -inch, doc.pagesize[0]-2*inch, -45)

        # Study name, patient ID, visit number and plate information
        # Use ECRFLabel because the text can contain non-ASCII characters
        label = ECRFLabel(Rect(inch, inch+4, doc.pagesize[0]-inch, inch+20),
                          self.study.study_name, properties_centered_bold)
        label.draw(canv, color=black)
        label = ECRFLabel(Rect(inch+5, inch+4, doc.pagesize[0]/2, inch+20),
                          format_pid(self.context.get('format_pid'), self.pid),
                          properties_left)
        label.draw(canv, color=black)
        label = ECRFLabel(Rect(inch+5, inch+16, doc.pagesize[0]*0.7, inch+28),
                          self.record.visit_label, properties_left)
        label.draw(canv, color=black)
        label = ECRFLabel(Rect(inch+5, inch+28, doc.pagesize[0]*0.7, inch+40),
                          self.record.page_label, properties_left)
        label.draw(canv, color=black)

        # Footer message
        if self.context.get('footer'):
            label = ECRFLabel(Rect(inch, doc.pagesize[1]-60,
                                   doc.pagesize[0]-inch, doc.pagesize[1]-48),
                              self.context.get('footer'),
                              {
                                  'align': 'left',
                                  'font_size': 8,
                                  'font': regular_font()
                              })
            label.draw(canv, color=black)

        # Page Number
        label = ECRFLabel(Rect(inch, doc.pagesize[1]-60,
                               doc.pagesize[0]-inch, doc.pagesize[1]-48),
                          'Page %d' % canv.getPageNumber(),
                          {
                              'align': 'right',
                              'font_size': 10,
                              'font': regular_font()
                          })
        label.draw(canv, color=black)


        canv.setStrokeColor(blue)
        canv.setLineWidth(0.1)
        canv.setFillColor(blue)
        canv.setFont(regular_font(), 10)

        rmargin = self.doc.leftMargin + self.doc.width
        key = self.record.keys_bookmark

        labels = []
        if not self.exclude_field_audit:
            labels.append(('ByField Audit', 'FA'))
        if not self.exclude_chronological_audit:
            labels.append(('Audit', 'AU'))
        if not self.exclude_datalisting:
            labels.append(('Data Values', 'DL'))
        if self.need_attachments:
            labels.append(('Attachments', 'AT'))

        labels.append(('CRF', 'B0'))

        for label, bookmark in labels:
            rect = Rect(rmargin-66, inch-16, rmargin, inch-4)
            canv.rect(rect.left, -rect.top, rect.width, -rect.height)
            canv.linkRect(key + bookmark, key + bookmark,
                          (rect.left, -rect.top, rect.right, -rect.bottom))
            canv.drawCentredString(rect.left + rect.width/2, -(rect.top+10),
                                   label)
            rmargin -= 72

        canv.restoreState()
        if self.context.get('watermark'):
            watermark_page(doc, canv, self.context.get('watermark'))

    def build_bookmarks(self, records):
        '''Build the bookmarks for the record list'''
        pid_formatted = format_pid(self.context.get('format_pid'), self.pid)
        bookmarks = []
        domains = {}
        last_visit_label = None
        for num, record in enumerate(records):
            key = record.keys_bookmark
            if num == 0:
                bookmarks.append((pid_formatted, key + 'B0', 0))
                bookmarks.append(('By Visit', key + 'B1', 1))

            visit_label = record.visit_label
            if visit_label != last_visit_label:
                bookmarks.append((visit_label, key + 'B2', 2))
                last_visit_label = visit_label

            bookmarks.append((record.page_label, key + 'B3', 3))
            domain = domains.setdefault(record.plate.domain, [])
            domain.append(record)

        for d_num, domain in enumerate(sorted(domains.keys())):
            key = domains[domain][0].keys_bookmark
            if d_num == 0:
                if len(domains) > 1:
                    bookmarks.append(('By Domain', key + 'B4', 1))
                else:
                    break
            bookmarks.append((domain, key + 'B5', 2))
            last_visit_label = None
            for record in domains[domain]:
                key = record.keys_bookmark
                visit_label = record.visit_label
                if visit_label != last_visit_label:
                    bookmarks.append((visit_label, key + 'B6', 3))
                    last_visit_label = visit_label

                bookmarks.append((record.page_label, key + 'B7', 4))

        return [Bookmarks(bookmarks)]

    def build_datalisting(self, record):
        '''Build the data values listing'''
        flowables = [Section('Data Field Values', record.keys_bookmark + 'DL')]

        if not record.missing and not record.deleted:
            listing = Listing([
                {'name': 'Field', 'width': 40, 'align': 'right'},
                {'name': 'Description', 'width': 130},
                {'name': 'Value', 'width': 100, 'long': True,
                 'expandable': True}
            ])
            for field in record.plate.user_fields:
                value = record.field(field.number)
                desc = field.description

                if record.field_missing_value(field.number):
                    value = '[' + value + ', ' + \
                        record.field_missing_value_label(field.number) + ']'
                else:
                    _, decoded = field.decode(value)
                    if field.data_type == 'Check' or \
                        field.data_type == 'Choice':
                        value = value + ', ' + decoded

                    if not value:
                        value = '[blank]'

                if field.blinded and self.blinded == 'skip':
                    continue
                if field.blinded and self.blinded == 'redact':
                    value = 'Internal Use Only Field'
                    desc = 'Internal Use Only Field'

                entry_bookmark = record.keys_bookmark + \
                    '_{}'.format(field.number)

                value = htmlify(value, bold_font())
                if not self.exclude_field_audit:
                    value = href('#' + entry_bookmark + 'AF', value)
                entry = ListEntry([
                    Paragraph(para(htmlify(str(field.number) + '.',
                                           regular_font()), 'right')),
                    Paragraph(htmlify(desc, regular_font())),
                    Paragraph(value)])
                entry.bookmark = entry_bookmark
                listing.add_row(entry)

            flowables.append(listing)
        else:
            flowables.append(Paragraph(
                htmlify(record.missing_reason if record.missing \
                        else record.deleted_reason, regular_font())))
        return flowables

    def build_attachments(self, record):
        '''Build the attachments section'''
        flowables = [PageBreak(),
                     Section(None, record.keys_bookmark+'AT')]
        incl_sec = self.context.get('secondaries', False)
        for attachment in record.attachments(incl_sec):
            if not attachment.load(self.study.api):
                logging.warning('%s Unable to get attachment %s',
                                record.keys, attachment.raster)
                continue

            if attachment.is_pdf:
                flowables.extend(build_attachment_pdf(record, attachment))
            else:
                flowables.extend(build_attachment_image(record, attachment))

        return flowables

    def build_auditlistings(self, record):
        '''Build the flowables for the audit sections'''
        # No audit requested, skip
        if self.exclude_chronological_audit and self.exclude_field_audit:
            return []

        auditdb = AuditOps(self.study, self.sql)
        audit_ops = auditdb.auditop_records(record, self.blinded)

        flowables = [] if self.exclude_chronological_audit else \
            build_audit_chrono(record, audit_ops)

        if not self.exclude_field_audit:
            flowables.extend(build_audit_byfield(record, audit_ops,
                                                 self.blinded))

        return flowables

    def build_flowables(self, records):
        '''Build the flowables for a closeout PDF'''
        flowables = self.build_bookmarks(records)

        prefer_background = self.context.get('prefer_background')
        for record in records:
            logging.debug('processing record: %s', record.keys)
            self.record = record
            plate = record.plate
            if plate is None:
                logging.warning('%s Skipping undefined plate %d',
                                record.keys, record.plate_num)
                continue

            bkgd_image = self.study.api.background(
                plate, record.visit_num, preferred_types=prefer_background
            )
            for page in plate.pages:
                flowables.append(CRF(record, page, bkgd_image,
                                     self.context, self.set_record))

            if self.need_attachments:
                flowables.extend(self.build_attachments(record))
            if not self.exclude_datalisting:
                flowables.extend(self.build_datalisting(record))
            flowables.extend(self.build_auditlistings(record))
            flowables.append(PageBreak())

        self.record = None
        return flowables

    def build(self, pagesize=letter):
        '''build a closeout PDF'''
        context = self.context
        site = self.study.sites.pid_to_site_number(self.pid)
        pid_formatted = format_pid(context.get('format_pid'), self.pid)
        path = os.path.join(context.get('destdir', '.'), str(site),
                            pid_formatted + '.pdf')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc = BaseDocTemplate(path, leftMargin=inch, rightMargin=inch,
                              bottomMargin=inch, topMargin=inch,
                              pagesize=pagesize)
        templates = [PageTemplate('normal', [Frame(inch, inch, doc.width,
                                                   doc.height-45,
                                                   leftPadding=0,
                                                   rightPadding=0,
                                                   bottomPadding=0,
                                                   showBoundary=0)],
                                  onPageEnd=self.page_header)]
        doc.addPageTemplates(templates)
        doc.title = 'Closeout PDF ' + pid_formatted
        doc.subject = 'Subject ID ' + pid_formatted
        doc.author = 'DFtoolkit CloseoutPDF'
        doc.creator = 'DFtoolkit CloseoutPDF'
        self.doc = doc
        records = list(self.sql.sorted_record_keys(self.pid, self.context))
        doc.build(self.build_flowables(records))

        # Linearize if requested
        if context.get('linearize', False):
            logging.info('Linearizing %s', path)
            pdf = Pdf.open(path, allow_overwriting_input=True)
            pdf.save(path, linearize=True)
