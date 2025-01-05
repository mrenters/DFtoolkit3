#
# Copyright 2021-2025, Martin Renters
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
This module implements basic report card functionality
'''

import logging
import PIL
from openpyxl import load_workbook
from reportlab.lib.colors import black, white, grey
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Image,
    ListItem, ListFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

def evaluate(expression, data_fields):
    '''a safe eval function'''
    code = compile(expression, '<string>', 'eval')
    for name in code.co_names:
        if name not in data_fields:
            raise NameError(f'"{name}" is not defined')
    return eval(code, {'__builtins__': {}}, data_fields)

def excel_rules(filename):
    '''load reportcard rules from an Excel workbook'''
    rules = []
    workbook = load_workbook(filename)
    for row in workbook.active.rows:
        operation = row[0].value.strip() \
            if len(row) > 0 and row[0].value else ''
        expression = row[1].value if len(row) > 1 else None
        text = row[2].value if len(row) > 2 else ''
        rules.append((operation, expression, text))
    return rules

class ReportCard:
    '''An abstract report card class'''
    def __init__(self, filename):
        self.filename = filename
        default_style = ParagraphStyle(
            'default',
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            leftIndent=0,
            rightIndent=0,
            firstLineIndent=0,
            alignment=TA_LEFT,
            spaceBefore=3,
            spaceAfter=3,
            bulletFontName='Helvetica',
            bulletFontsize=10,
            bulletIndent=0,
            textColor=black,
            backColor=None,
            wordWrap=None,
            borderWidth=0,
            borderPadding=0,
            borderColor=None,
            borderRadius=None,
            allowWidows=1,
            allowOrphans=0,
            textTransform=None,  # 'uppercase' | 'lowercase' | None
            endDots=None,
            splitLongWords=1,
        )
        self.styles = {
            'default': default_style,
            'title': ParagraphStyle(
                'title',
                parent=default_style,
                fontName='Helvetica-Bold',
                fontSize=12,
                leading=14,
                alignment=TA_CENTER,
                textColor=grey
            ),
            'smalltitle': ParagraphStyle(
                'title',
                parent=default_style,
                fontName='Helvetica',
                fontSize=8,
                leading=10,
                spaceBefore=6,
                spaceAfter=6,
                alignment=TA_CENTER,
                textColor=grey
            ),
            'section': ParagraphStyle(
                'section',
                parent=default_style,
                fontName='Helvetica',
                fontSize=12,
                leading=16,
                spaceBefore=5,
                spaceAfter=5,
                firstLineIndent=6,
                alignment=TA_LEFT,
                textColor=white,
                backColor=grey,
                borderWidth=1,
                borderPadding=1,
                borderColor=black
            )
        }
        self.doc = BaseDocTemplate(filename,
                                   leftMargin=18, rightMargin=18,
                                   bottomMargin=36, topMargin=18,
                                   pagesize=(8.5*72, 11*72))
        self.doc.addPageTemplates([
            PageTemplate(id='normal', frames=[
                Frame(18, 36, self.doc.width, self.doc.height, showBoundary=0)
            ])
        ])
        self.flowables = []
        self.statements = []
        self.text_style = None
        self.handlers = {
            'title': self.header_handler,
            'smalltitle': self.header_handler,
            'section': self.header_handler,
            'logo': self.logo_handler,
            'text': self.text_handler,
            'break': self.text_handler,
            'bullet': self.text_handler,
            'variables': self.variables_handler
        }

    def flush_statements(self):
        '''flush any queued statements to the output'''
        if not self.statements:
            return
        if self.text_style == 'bullet':
            flowables = [ListItem(Paragraph(statement,
                                            self.styles['default']),
                                  bulletFontSize=8, leftIndent=36,
                                  value='circle') \
                for statement in self.statements]
            self.flowables.append(ListFlowable(flowables,
                                               bulletType='bullet'))
        else:
            self.flowables.append(Paragraph(' '.join(self.statements),
                                            self.styles['default']))
        self.statements = []

    def header_handler(self, operation, text, data_fields):
        '''deal with titles, smalltitles, and sections'''
        self.flush_statements()
        text = '' if text is None else text
        try:
            self.flowables.append(Paragraph(text.format(**data_fields),
                                            self.styles[operation]))
        except (ValueError, NameError, KeyError) as err:
            raise ValueError(f'{err} in message: "{text}"')

    def variables_handler(self, _operation, _text, data_fields):
        '''dump all the data fields'''
        self.flush_statements()
        for key, value in sorted(data_fields.items()):
            if key.startswith('_'):
                continue
            self.flowables.append(Paragraph(f'{key} = {value}',
                                            self.styles['default']))

    def logo_handler(self, _operation, img_path, _data_fields):
        '''insert a logo into the reportcard'''
        self.flush_statements()
        try:
            img = PIL.Image.open(img_path)
            width, height = img.size
            flow_height = 36 if width > height * 4 else 72
            self.flowables.append(Image(img_path, height=flow_height,
                                        width=(width * flow_height) / height,
                                        hAlign='CENTER'))
        except IOError:
            raise ValueError(f'unable to open image: "{img_path}"')

    def text_handler(self, operation, text, data_fields):
        '''handle conditional expressions'''
        if operation != self.text_style:
            self.flush_statements()

        self.text_style = operation

        text = '' if text is None else text

        try:
            self.statements.append(text.format(**data_fields))
        except (ValueError, NameError, KeyError) as err:
            raise ValueError(f'{err} in message: "{text}"')

    def build(self, rules, data_fields):
        '''build the document'''
        ret = True
        for operation, expression, text  in rules:
            data_fields['statements'] = self.statements
            if not operation or operation == 'operation':
                continue
            function = self.handlers.get(operation)
            if not function:
                logging.error('%s: unknown operation: "%s"', self.filename,
                              operation)
                ret = False
                continue

            # Evaluate expression
            if isinstance(expression, str) and expression != '':
                try:
                    condition = evaluate(expression, data_fields)
                except (ValueError, NameError) as err:
                    logging.error('%s: %s in condition "%s"', self.filename,
                                  err, expression)
                    ret = False
                    continue
                except SyntaxError as err:
                    logging.error('%s: syntax error in condition "%s"',
                                  self.filename, expression)
                    ret = False
                    continue
            elif expression is None or expression == '':
                condition = True
            else:
                condition = expression

            # if expression is False then skip this operation
            if not condition:
                continue

            # Call the operation handler
            try:
                function(operation, text, data_fields)
            except ValueError as err:
                logging.error('%s: %s', self.filename, err)
                ret = False

        self.flush_statements()
        self.doc.build(self.flowables)

        return ret
