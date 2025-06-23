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

'''FieldBase abstract class used by Styles, Fields and FieldRefs'''

from operator import lt, gt
from requests.structures import CaseInsensitiveDict
from .changerecord import ChangeList, ChangeTest, ChangeRecord
from .rect import Rect, rect_groups
from .ecrf import layout_text, ECRFLabel
from .texttools import bold_font
from .utils import parse_editchecks

##########################################################################
# zeropad_numeric - correctly zeropad a numeric according to format
##########################################################################
def zeropad_numeric(fmt, val):
    '''zero pad a numeric field according to number positions in format'''
    error = None

    # Save sign if negative and then break into groups by decimal point
    negative = (val[0] == '-')
    numbers = ''.join(filter(lambda x: x.isdigit() or x == '.', val)).split('.')
    numbers[0] = numbers[0].lstrip('0')

    # Strip leading zeros before decimal and trailing zeros after decimal
    if len(numbers) > 1:
        numbers[1] = numbers[1].rstrip('0')
    sections = ''.join(filter(lambda x: x.isdigit() or x in ('n', 's', '.'),
                              fmt)).split('.')

    # Now zero pad numbers according to format specification
    for num, section in enumerate(sections):
        if len(numbers) <= num:
            numbers.append('')
        num_len = len(numbers[num])

        # If we have a 's' (but not an 'S') and the number is negative,
        # leave space for the sign which was stripped off earlier
        if negative and 's' in section and not 'S' in fmt and num == 0:
            num_len += 1
        sec_len = len(section)
        if sec_len < num_len:
            error = 'value truncated'
            if num:     # Trim off RHS if decimal part
                numbers[num] = numbers[num][:sec_len]
            else:           # Trim off LHS if integer part
                numbers[num] = numbers[num][-sec_len:]
        if sec_len > num_len:
            if num:
                numbers[num] = numbers[num] + ('0' * (sec_len - num_len))
            else:
                numbers[num] = ('0' * (sec_len - num_len)) + numbers[num]

    # Make sure we have the same number of format sections as number sections
    if not error and len(sections) != len(numbers):
        error = 'mismatched format and value'

    return error, negative, '.'.join(numbers)

##########################################################################
# reformat_numeric - reformat a numeric value according to format spec
##########################################################################
def reformat_numeric(fmt, val):
    '''formats a numeric field according to the field format specificiation'''
    # If not format or no number, just return
    if not fmt or not val:
        return val, None

    error, negative, newval = zeropad_numeric(fmt, val)

    # re-assemble value according to full format specification
    ret = ''
    val_idx = 0
    sign_output = False
    for fmt_chr in fmt:
        if fmt_chr == 'S':
            ret += '-' if negative else '+'
            sign_output = True
        elif fmt_chr == 's':
            if negative and not sign_output:
                ret += '-'
                sign_output = True
            else:
                ret += newval[val_idx]
                val_idx += 1
        elif fmt_chr == 'n':
            ret += newval[val_idx]
            val_idx += 1
        elif fmt_chr == '.' or fmt_chr.isdigit():
            ret += fmt_chr
            if newval[val_idx] != fmt_chr:
                error = 'formatting'
            val_idx += 1
        else:
            ret += fmt_chr

    if negative and not sign_output:
        error = 'negative value and mismatched format'

    return ret, error

##########################################################################
# multibox_numeric
##########################################################################
def multibox_numeric(fmt, val, rects):
    '''Returns the value formatted to the boxes'''
    if not val:
        return val, None

    reformatted, error = reformat_numeric(fmt, val)

    val_groups = [len(section) for section in reformatted.split('.')]
    box_groups = rect_groups(rects)

    # remove decimal point in [][] [][] case (12.34 -> 1234)
    if len(val_groups) == 2 and len(box_groups) == 2:
        reformatted = reformatted.replace('.', '')
        if val_groups[0] < box_groups[0]:
            reformatted = (' ' * (box_groups[0] - val_groups[0])) + reformatted
        if val_groups[0] > box_groups[0]:
            reformatted = reformatted[val_groups[0]-box_groups[0]:]
            error = error or 'value truncated'
        if val_groups[1] > box_groups[1]:
            error = error or 'value truncated'
    else:
        if len(reformatted) < len(rects):
            reformatted = (' ' * (len(rects) - len(reformatted))) + reformatted
        elif len(reformatted) > len(rects):
            reformatted = reformatted[-len(rects):]
            error = error or 'value truncated'

    return reformatted, error

##########################################################################
# FieldBase - Abstract base class for Styles, Fields and FieldRefs
##########################################################################
class FieldBase:
    '''Abstract Field class, used for styles, fields and fieldrefs'''
    def __init__(self, study):
        self._study = study
        self.number = None
        self.name = None
        self.alias = None
        self.style_name = None
        self.description = None
        self.data_type = None
        self.legal_range = None
        self.data_format = None
        self.help_text = None
        self.constant = None
        self.constant_value = ''
        self.prompt = None
        self.comment = None
        self.units = None
        self.field_enter = None
        self.field_exit = None
        self.plate_enter = None
        self.plate_exit = None
        self.skip_number = None
        self.skip_condition = None
        self.inherited = None
        self.locked = None
        self.reason_level = None
        self.reason_nonblank = False
        self.blinded = False
        self.required = 'Optional'
        self.store = 1
        self.display = 1
        self.use = 'Standard'
        self.mapping = None
        self.year_cutoff = None
        self.date_rounding = None
        self.codes = []
        self._unique_id = None
        self.vas_left_value = 0
        self.vas_right_value = 0
        self.priority = 5       # DFtoolkit attribute
        self.user_properties = CaseInsensitiveDict()

    ##########################################################################
    # loadSetup - Initialize from JSON setup data
    ##########################################################################
    def load_setup(self, json):
        '''Load the JSON format data'''
        self._unique_id = json.get('id')
        self.number = json.get('number')
        self.name = json.get('name')
        self.style_name = json.get('styleName')
        self.alias = json.get('alias')
        self.description = json.get('description')
        self.data_type = json.get('type')
        self.legal_range = json.get('legal')
        self.data_format = json.get('format')
        self.help_text = json.get('help')
        self.constant = json.get('constant')
        self.constant_value = json.get('constantValue', '')
        self.prompt = json.get('prompt')
        self.comment = json.get('comment')
        self.units = json.get('units')
        self.field_enter = json.get('fieldEnter')
        self.field_exit = json.get('fieldExit')
        self.plate_enter = json.get('plateEnter')
        self.plate_exit = json.get('plateExit')
        self.skip_number = json.get('skipTo')
        self.skip_condition = json.get('skipCondition')
        self.inherited = json.get('inheritedBitmap')
        self.locked = json.get('lockedBitmap')
        self.reason_level = json.get('level')
        self.reason_nonblank = json.get('reasonIfNonBlank', False)
        self.blinded = json.get('blinded') != 'No'
        self.required = json.get('required')
        self.store = json.get('store', 1)
        self.display = json.get('display', self.store)
        self.use = json.get('use', 'Standard')
        self.mapping = json.get('mapping')
        self.year_cutoff = json.get('yearCutoff')
        self.date_rounding = json.get('dateRounding')
        self.vas_left_value = json.get('leftValue')
        self.vas_right_value = json.get('rightValue')
        self.codes = []
        for code in json.get('codes', []):
            self.codes.append((code['number'], code['label'],
                               code.get('subLabel', '')))

        for userprop in json.get('userProperties', []):
            alias = self._study.user_property_tags.get(userprop.get('name'))
            if alias:
                self.user_properties[alias] = userprop.get('value')

        self.priority = self.user_properties.get('priority', '5')
        self.priority = int(self.priority) if '1' <= self.priority <= '5' else 5

    @property
    def unique_id(self):
        '''Returns a field's unique ID'''
        return self._unique_id

    @property
    def ecs(self):
        '''Returns a list of edit checks on the field'''
        ecnames = []
        ecnames.extend(parse_editchecks(self.plate_enter))
        ecnames.extend(parse_editchecks(self.field_enter))
        ecnames.extend(parse_editchecks(self.field_exit))
        ecnames.extend(parse_editchecks(self.plate_exit))
        return ecnames

    @property
    def allows_partial_date(self):
        '''Does this field allow partial dates?'''
        return self.data_type == 'Date' and self.data_format and \
            ('mm' in self.data_format or 'dd' in self.data_format)

    ##########################################################################
    # decode
    ##########################################################################
    def decode(self, value):
        '''Decode a value returning its code'''
        box, label, _ = self.decode_with_submission(value)
        return (box, label)

    ##########################################################################
    # decode_submission
    ##########################################################################
    def decode_with_submission(self, value):
        '''Decode a value returning its box number, label, submission values'''
        box = None
        if self.data_type in ('Choice', 'Check', 'Number'):
            for code, label, submission in self.codes:
                if str(code) == str(value):
                    return (box, label, submission)
                if box is None:
                    box = 0
                else:
                    box += 1
        return (None, value, value)

    ##########################################################################
    # missing_value
    ##########################################################################
    def missing_value(self, value):
        '''Check whether value is a missing value and return status, label'''
        if value in self._study.missingmap:
            return (True, self._study.missingmap.get(value))
        return (False, '')

    @property
    def export_max_storage(self):
        '''returns the maximum amount of storage needed for export'''
        max_len = self.store
        for _, label, submission in self.codes:
            if label:
                max_len = max(max_len, len(label))
            if submission:
                max_len = max(max_len, len(submission))
        return max_len

    ##########################################################################
    # Changes - build a list of changes between two versions
    ##########################################################################
    def changes(self, prev):
        '''build a list of differences between the previous and current defn'''
        changelist = ChangeList()
        for attrib, test in [
                ('name',
                 ChangeTest('Name', impact_level=10,
                            impact_text='Review Edit Checks and SAS')),
                ('alias',
                 ChangeTest('Alias', impact_level=10,
                            impact_text='Review Edit Checks and SAS')),
                ('style_name',
                 ChangeTest('Style Name', impact_level=10,
                            impact_text='Potential meaning change')),
                ('description', ChangeTest('Description')),
                ('data_type',
                 ChangeTest('Data Type', impact_level=10,
                            impact_text='Potential data loss, review EC/SAS')),
                ('legal_range',
                 ChangeTest('Legal Range', impact_level=5,
                            impact_text='Potential meaning change')),
                ('data_format',
                 ChangeTest('Format', impact_level=10,
                            impact_text='Potential data loss, review EC/SAS')),
                ('help_text', ChangeTest('Help Text')),
                ('constant',
                 ChangeTest('Constant Field', impact_level=5,
                            impact_text='Potential data loss/meaning change')),
                ('constant_value',
                 ChangeTest('Constant Value', impact_level=5,
                            impact_text='Potential data loss/meaning change')),
                ('prompt',
                 ChangeTest('Prompt', impact_level=5,
                            impact_text='Potential meaning change')),
                ('comment', ChangeTest('Comment')),
                ('units',
                 ChangeTest('Units', impact_level=5,
                            impact_text='Potential meaning change')),
                ('plate_enter', ChangeTest('Plate Enter Edit Checks')),
                ('field_enter', ChangeTest('Field Enter Edit Checks')),
                ('field_exit', ChangeTest('Field Exit Edit Checks')),
                ('plate_exit', ChangeTest('Plate Exit Edit Checks')),
                ('skip_number', ChangeTest('Skip Number')),
                ('skip_condition', ChangeTest('Skip Condition')),
                ('vas_left_value',
                 ChangeTest('Left Value', impact_level=5,
                            impact_text='Potential meaning change')),
                ('vas_right_value',
                 ChangeTest('Right Value', impact_level=5,
                            impact_text='Potential meaning change')),
                ('reason_level', ChangeTest('Reason Level')),
                ('reason_nonblank', ChangeTest('Reason Non-Blank')),
                ('blinded', ChangeTest('Hidden')),
                ('required', ChangeTest('Need')),
                ('store',
                 ChangeTest('Store Length', compare_op=gt, impact_level=10,
                            impact_text='Potential data loss')),
                ('store', ChangeTest('Store Length', compare_op=lt)),
                ('display', ChangeTest('Display Length')),
                ('use', ChangeTest('Use')),
                ('mapping',
                 ChangeTest(
                     'Mapping', impact_level=10,
                     impact_text='Potential data change, review EC/SAS')),
                ('year_cutoff',
                 ChangeTest(
                     'Year Cutoff', impact_level=10,
                     impact_text='Potential data change, review EC/SAS')),
                ('date_rounding',
                 ChangeTest(
                     'Date Rounding', impact_level=10,
                     impact_text='Potential data change, review EC/SAS')),
        ]:
            changelist.evaluate_attr(prev, self, attrib, test)

        # Check coding
        for box in range(max(len(prev.codes), len(self.codes))):
            if box >= len(prev.codes):
                changelist.append(ChangeRecord(
                    self, f'Code box {box} added', None, self.codes[box]))
            elif box >= len(self.codes):
                changelist.append(ChangeRecord(
                    self, f'Code box {box} deleted', prev.codes[box], None,
                    impact_level=10,
                    impact_text='May invalidate data. Review EC/SAS'))
            elif prev.codes[box] != self.codes[box]:
                changelist.append(ChangeRecord(
                    self, f'Code box {box} changed',
                    prev.codes[box], self.codes[box],
                    impact_level=10,
                    impact_text='May invalidate data. Review EC/SAS'))

        changelist.evaluate_user_properties(prev, self)
        return changelist

##############################################################################
# Style Class
##############################################################################
class Style(FieldBase):
    '''Style class'''
    def __init__(self, study, json):
        super().__init__(study)
        self._study = study
        super().load_setup(json)
        study.add_style(self)

    def __repr__(self):
        return f'<Style {self.style_name}>'

##############################################################################
# Field Class
##############################################################################
class Field(FieldBase):
    '''A Field within a module'''
    def __init__(self, module, json):
        super().__init__(module.study)
        self._module = module
        super().load_setup(json)
        module.add_field(self)

    @property
    def module(self):
        '''Get the module this field belongs to'''
        return self._module

    def __repr__(self):
        return f'<Field {self.unique_id} {self.name} ({self.description})>'

##############################################################################
# FieldRef Class - FieldRefs of a ModuleRef
##############################################################################
class FieldRef(FieldBase):
    '''A field reference (instance of a field on a plate)'''
    def __init__(self, moduleref, json):
        super().__init__(moduleref.study)
        self._moduleref = moduleref
        super().load_setup(json)
        rects = [Rect(rect['x'], rect['y'],
                      rect['x'] + rect['w'],
                      rect['y'] +  rect['h']) \
                 for rect in json.get('rects', [])]

        # Get the Field ID that this FieldRef is from and retrieve the style
        self.field = self._study.field(json.get('fieldId'))
        self.style_name = self.field.style_name

        self.group_field_id = json.get('groupFieldId', self.unique_id)
        self.coding_columns = json.get('codingColumns', 1)
        # convert coding_label_position to lowercase as setup isn't
        # consistent. It is sometimes Right, sometimes right
        self.coding_label_position = json.get('codingLabelPosition',
                                              'right').lower()

        # Combine adjacent rectangles and straighten them out
        combined_rect = None
        num_boxes = 0
        self.rects = []
        for rect in rects:
            if combined_rect is None:
                combined_rect = rect
                num_boxes = 1
            elif combined_rect.is_adjacent_horizontal(rect):
                combined_rect.right = rect.right
                num_boxes += 1
            else:
                self.rects.extend(combined_rect.split_horizontal(num_boxes))
                combined_rect = rect
                num_boxes = 1
        if combined_rect is not None:
            self.rects.extend(combined_rect.split_horizontal(num_boxes))

        moduleref.add_fieldref(self)
        self.ecrf_elements = []

    def expand_meta(self, text):
        '''Expands $(plate), $(rplate) and $(field) meta words'''
        plate_num = self._moduleref.plate.number
        text = text.replace('$(plate)', f'{plate_num:03d}')
        text = text.replace('$(rplate)', str(plate_num))
        text = text.replace('$(field)', str(self.number))
        return text

    @property
    def expanded_alias(self):
        '''Expands $(plate), $(rplate) and $(field) from the alias'''
        return self.expand_meta(self.alias)

    @property
    def expanded_description(self):
        '''Expands $(plate), $(rplate) and $(field) in the description'''
        return self.expand_meta(self.description)

    @property
    def expanded_legal_range(self):
        '''Expands $(choices) from the legal range'''
        choices = sorted([code[0] for code in self.codes])
        choice_range = ', '.join(map(str, choices))
        legal_range = self.legal_range.replace('$(choices)', choice_range)
        return legal_range

    @property
    def plate(self):
        '''Returns the plate that this field belongs to'''
        return self._moduleref.plate

    @property
    def moduleref(self):
        '''Returns the moduleref that this field belongs to'''
        return self._moduleref

    @property
    def is_system(self):
        '''Return whether this is a system meta variable'''
        return self._moduleref.name == 'DFSYSTEM'

    @property
    def group_leader(self):
        '''Is this field standalone or a group leader?'''
        return self.unique_id == self.group_field_id

    @property
    def display_max(self):
        '''Returns the display length based on defined length or drop-down
        coding labelss'''
        return max([len(code[1]) for code in self.codes]) \
            if self.data_type in ('Check', 'Choice') and \
               self.coding_columns == 0 \
            else min(self.store, 1024)      # Limit to something reasonable

    @property
    def bounding_box(self):
        '''Return the bounding box for all the field's boxes'''
        return sum(self.rects, self.rects[0]) if self.rects else None

    def __repr__(self):
        return f'<FieldRef {self.number} ({self.description})>'

    def layout_ecrf(self, width):
        '''Layout an ECRF question text on a page'''

        self.ecrf_elements = []
        self.rects = []

        question_width = (width/3) - 5
        response_width = width - question_width - 10
        response_x = question_width + 10

        # Layout question text starting at (0,0) if this field is a
        # group leader or just by itself
        if self.group_leader:
            self.ecrf_elements = layout_text(self.prompt or self.description,
                                             width/3,
                                             attribs={'font': bold_font(),
                                                      'font_size':14})


        # Layout boxes and choice/check labels
        # responses are located starting at second third of the width of page
        ypos = 0

        if self.data_type in ('Choice', 'Check') and self.coding_columns:
            choice_width = response_width / self.coding_columns
            for option, code in enumerate(self.codes[1:]):
                column = option % self.coding_columns
                if option and column == 0:
                    ypos += 50 if self.coding_label_position in \
                        ('top', 'bottom') else 25
                xpos = response_x + (column * choice_width)

                delta_x = 0 if self.coding_label_position == 'right' else \
                    choice_width-20 if self.coding_label_position == 'left' \
                    else (choice_width-20)/2
                delta_y = 0 if self.coding_label_position != 'top' else 25

                self.rects.append(Rect(xpos + delta_x, ypos + delta_y,
                                       xpos + delta_x + 20,
                                       ypos + delta_y + 20))

                # Add label
                if self.coding_label_position != 'none':
                    label_width = choice_width - 25 - 5
                    delta_x = 0
                    delta_y = 0
                    align = 'right'
                    if self.coding_label_position == 'right':
                        delta_x = 25
                        align = 'left'
                    if self.coding_label_position == 'top':
                        align = 'center'
                        label_width = choice_width
                    if self.coding_label_position == 'bottom':
                        delta_y = 25
                        align = 'center'
                        label_width = choice_width

                    label = ECRFLabel(Rect(xpos + delta_x,
                                           ypos + delta_y + 3,
                                           xpos + delta_x + label_width,
                                           ypos + delta_y + 3 + 14),
                                      code[1],
                                      attribs={'font_size': 12,
                                               'align': align})
                    self.ecrf_elements.append(label)
        else:
            char_width = 16
            max_chars = response_width / char_width
            lines = self.display_max // max_chars+1
            if lines == 1:
                boxes = self.display_max % max_chars
                self.rects = [Rect(response_x, ypos,
                                   response_x+(char_width*boxes), ypos+25)]
                if boxes < 15 and self.units or self.data_type == 'VAS':
                    if self.data_type == 'VAS':
                        label_text = '{} - {}'.format(self.vas_left_value,
                                                      self.vas_right_value)
                    else:
                        label_text = self.units

                    label = ECRFLabel(Rect(response_x + (char_width * boxes)+5,
                                           ypos + 5,
                                           response_x + response_width,
                                           ypos + 5 + 14),
                                      label_text,
                                      attribs={'font_size': 10})
                    self.ecrf_elements.append(label)
            else:
                self.rects = [Rect(response_x, ypos,
                                   response_x+response_width, ypos+(25*lines))]

    @property
    def ecrf_height(self):
        '''Returns the height that the rects and ecrf elements need'''
        label_height = max([rect.bottom for rect in self.ecrf_elements]) \
            if self.ecrf_elements else 0
        box_height = max([rect.bottom for rect in self.rects]) \
            if self.rects else 0
        return max(label_height, box_height)

    def translate(self, x_offset, y_offset):
        '''Translate boxes by x_offset, y_offset'''
        for element in self.ecrf_elements:
            element.translate(x_offset, y_offset)
        for rect in self.rects:
            rect.translate(x_offset, y_offset)

    def changes(self, prev):
        '''Return a list of changes between two versions of a FieldRef'''
        changelist = super().changes(prev)
        changelist.evaluate_attr(
            prev, self, 'number',
            ChangeTest('Field Number', impact_level=10,
                       impact_text='Review Edit Checks'))
        changelist.evaluate_attr(
            prev, self, 'expanded_alias',
            ChangeTest('Alias (Expanded Name)', impact_level=10,
                       impact_text='Review Edit Checks and SAS'))
        # Check boxes
        for box in range(max(len(prev.rects), len(self.rects))):
            if box >= len(prev.rects):
                changelist.append(ChangeRecord(
                    self, f'Field Box {box} added', None, self.rects[box],
                    impact_level=5,
                    impact_text='Review all backgrounds to ensure they match'))
            elif box >= len(self.rects):
                changelist.append(ChangeRecord(
                    self, f'Field Box {box} deleted', prev.rects[box], None,
                    impact_level=5,
                    impact_text='Review all backgrounds to ensure they match'))
            elif prev.rects[box] != self.rects[box]:
                changelist.append(ChangeRecord(
                    self, f'Field Box {box} changed',
                    prev.rects[box], self.rects[box],
                    impact_level=5,
                    impact_text='Review all backgrounds to ensure they match'))

        return changelist
