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
'''Plate related classes'''

from requests.structures import CaseInsensitiveDict
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from .module import ModuleRef
from .ecrf import ECRFLabel, ECRFScreen, ECRFShading
from .rect import Rect

class ScreenBreak:
    '''A screen break on an eCRF'''
    def __init__(self, plate, json):
        self.plate = plate
        self.first_field = json.get('firstFieldNum')
        self.last_field = json.get('lastFieldNum')
        self.label = json.get('label')

    def layout(self, page, page_rect, ypos):
        '''Layout the fields of a screen onto the page'''

        colors = ['#e6e6dc', '#f6f6f3']
        screen_block = None
        shading_block = None
        shading_color = 0
        groups = []
        for num, field in enumerate(self.plate.fields[self.first_field-1: \
                                                      self.last_field]):
            if field.is_system:
                continue

            # If this is the first field, or a group leader, start a new group
            if num == 0 or field.group_leader:
                group = []
                groups.append(group)
            group.append(field)

        for group in groups:
            # Account for field height and shading
            height_needed = sum([field.ecrf_height + 8 for field in group])

            # see if we can fit the entire group on a page together
            if page is None or (ypos + height_needed >= page_rect.bottom-10
                                and height_needed < page_rect.bottom-50):
                page = PlatePage(self.plate)
                ypos = page.add_title(page_rect)
                screen_block = None
                shading_block = None

            for field in group:
                height_needed = field.ecrf_height + 8
                if ypos + height_needed >= page_rect.bottom-10:
                    page = PlatePage(self.plate)
                    ypos = page.add_title(page_rect)
                    screen_block = None
                    shading_block = None
                if screen_block is None:
                    screen_block = ECRFScreen(Rect(page_rect.left,
                                                   ypos,
                                                   page_rect.right,
                                                   ypos), self.label)
                    page.add_element(screen_block)
                    shading_block = None
                    shading_color = 0

                if shading_block is None or field.group_leader:
                    shading_block = ECRFShading(screen_block.get_child_start(),
                                                colors[shading_color])
                    page.add_element(shading_block)
                    screen_block.add_height(shading_block.height)
                    shading_color ^= 1
                    ypos = shading_block.get_child_start().bottom

                page.add_userfield(field)
                field.translate(shading_block.left+5, ypos)
                ypos += height_needed
                shading_block.add_height(height_needed)
                screen_block.add_height(height_needed)

            screen_block.add_height(5)

        return page, ypos

    def __repr__(self):
        return 'ScreenBreak<%d, %d, %s>' % (self.first_field, self.last_field,
                                            self.label)

class PlatePage:
    '''An individual page of a multipage plate. eCRFs can be multiple pages'''
    def __init__(self, plate):
        self.plate = plate
        self.ecrf_elements = []
        self.user_fields = []
        self.pagesize = None
        plate.pages.append(self)

    def add_element(self, element):
        '''Add an element to this page'''
        self.ecrf_elements.append(element)

    def add_title(self, page_rect):
        '''Add title header to the page'''
        self.add_element(ECRFLabel(page_rect,
                                   '{}: {}'.format(self.plate.number,
                                                   self.plate.description),
                                   attribs={'font_size':20, 'align':'center'}))
        return page_rect.top + 24

    def set_pagesize(self, pagesize):
        '''Set pagesize in pixels'''
        self.pagesize = pagesize

    def add_userfield(self, field):
        '''Add a user field to this page'''
        self.user_fields.append(field)

    @property
    def bounding_box(self):
        '''Returns bounding box of all the user fields'''
        if not self.ecrf_elements:
            right = 864
            bottom = 1100
            for field in self.user_fields:
                field_bbox = field.bounding_box
                right = max(field_bbox.right + 5, right)
                bottom = max(field_bbox.bottom + 5, bottom)
        else:
            right = self.pagesize[0]
            bottom = self.pagesize[1]
        return Rect(0, 0, right, bottom)

    def page_params(self, img=None):
        '''Returns width, height and scaling information based on bkgd image'''
        bounds = self.bounding_box
        if img:
            width, height = img.size
            width = max(864, width) # Some images are only 864
            field_scale = width // 864
            width = max(width, bounds.width*field_scale)
            height = max(height, bounds.height*field_scale)
        else:
            width = bounds.width
            height = bounds.height
            field_scale = 1

        return width, height, field_scale

class Plate:
    '''Plate representation class'''
    def __init__(self, study, json):
        self._study = study
        self._fields = None
        self._module_refs = {}
        self.arrival_trigger = json.get('arrivalTrigger')
        self.description = json.get('description')
        self.ecrf = json.get('eCRF')
        self.eligible_for_signing = json.get('eligibleForSigning')
        self.help_text = json.get('help')
        self.icr = json.get('icr')
        self._number = json.get('number')
        self.sequence_coded = json.get('sequenceCoded')
        self.term_plate = json.get('termPlate')
        self.user_properties = CaseInsensitiveDict()

        for userprop in json.get('userProperties', []):
            alias = self._study.user_property_tags.get(userprop.get('name'))
            if alias:
                self.user_properties[alias] = userprop.get('value')

        self.domain = self.user_properties.get('domain', 'Other')

        for moduleref_json in json.get('moduleRefs', []):
            ModuleRef(self, moduleref_json)

        self.screen_breaks = [ScreenBreak(self, data) \
                             for data in json.get('screenBreaks', [])]

        # Not all setup files have screenBreaks!
        if not self.screen_breaks:
            userfields = sorted(self.user_fields, key=lambda x: x.number)
            if userfields:
                first = userfields[0].number
                last = userfields[len(userfields)-1].number
                self.screen_breaks = [ScreenBreak(self,
                                                  {'firstFieldNum': first,
                                                   'lastFieldNum': last,
                                                   'label': 'Main Screen'})]
        self.layout_pages()
        study.add_plate(self)

    @property
    def study(self):
        '''Returns a pointer to the study'''
        return self._study

    @property
    def number(self):
        '''Returns the plate number'''
        return self._number

    def set_domain(self, domain):
        '''Sets the domain for the plate'''
        self.domain = domain

    def add_moduleref(self, moduleref):
        '''adds a moduleRef to the plate'''
        self._module_refs[moduleref.unique_id] = moduleref

    @property
    def modulerefs(self):
        '''returns a list of all modulerefs'''
        return self._module_refs.values()

    @property
    def first_page(self):
        '''Returns the first page of the plate'''
        return self.pages[0] if self.pages else None

    @property
    def fields(self):
        '''returns the list of fields, sorted by field number'''
        # If the field list exists and is current, simply return it
        if self._fields is not None:
            return self._fields

        # We need to build a new field list as it has never been created
        # or a field change invalidated it
        fieldlist = []
        for moduleref in self._module_refs.values():
            fieldlist.extend(moduleref.fieldrefs)
        fieldlist.sort(key=lambda x: x.number)
        self._fields = fieldlist

        return self._fields

    def field(self, field_num):
        '''returns the field at position field_num (1-based)'''
        fields = self.fields
        if field_num < 1 or field_num > len(fields):
            raise ValueError('field number {} out of range'.format(field_num))
        return fields[field_num-1]

    @property
    def user_fields(self):
        '''Returns a list of fields that aren't system fields'''
        return [field for field in self.fields if not field.is_system]

    def __repr__(self):
        return '<Plate %d (%s)>' % (self._number, self.description)

    def layout_pages(self, pagesize=letter, margin=0.5*inch):
        '''Lay out the CRF onto pages'''
        self.pages = []

        # If this isn't an eCRF, it is already laid out onto paper
        # so just move all the fields to this page
        if not self.ecrf:
            page = PlatePage(self)
            page.user_fields = self.user_fields
            return

        scale = (72.0/102, 72.0/98)     # Scale to DFdiscover fax units
        page_rect = Rect(margin/scale[0], margin/scale[1],
                         (pagesize[0]-margin)/scale[0],
                         (pagesize[1]-margin)/scale[1])

        # Calculate field layout and heights, reduce width to account
        # for later screen and shading offset
        for field in self.user_fields:
            field.layout_ecrf(page_rect.width-20)

        # Now layout into pages
        page = None
        ypos = page_rect.top + 24

        for screen in self.screen_breaks:
            page, ypos = screen.layout(page, page_rect, ypos)
            ypos += 20      # add space between screens

        # Add page numbers if the plate has more than one page
        if len(self.pages) > 1:
            for number, page in enumerate(self.pages):
                page.add_element(ECRFLabel(page_rect,
                                           'Page {}/{}'.format(number+1,
                                                               len(self.pages)),
                                           attribs={'font_size': 10,
                                                    'align': 'right'}))

        # Add page boundaries
        for page in self.pages:
            page.set_pagesize((pagesize[0]/scale[0], pagesize[1]/scale[1]))
