#!/usr/bin/env python
from lxml import etree
import re

try:  #python2
    from StringIO import StringIO
except ImportError:  #python3
    from io import StringIO

import robin
import srcgen

class XMLParser:
    def __init__(self, types_map, templates):
        self.types_map = types_map
        self.templates = templates

    # parses xml and returns dictionary with source components
    def get_src_from_xml(self, file_path='config/robin.xml'):
        self.xml_root = self.get_xml_root(file_path)
        self.src_gen = srcgen.SourceGenerator(self.types_map, self.templates, self.xml_root)
        self.parse_robins()
        return self.src_gen.get_source()

    # loads xml
    @staticmethod
    def get_xml_root(file_path):
        with open(file_path, 'r') as file:
            xml = file.read()
            while xml[:5] != '<?xml': xml = xml[1:]  # fix weird first character
            xml = re.sub('<\?xml version=.*encoding=.*\n', '', xml, count=1)  # remove encoding
            xml = re.sub(' xmlns=".*plcopen.org.*"', '', xml, count=1)  # remove namespace
            return etree.fromstring(xml)

    # parses robins from robin objects in xml
    def parse_robins(self):
        robin_objs = self.xml_root.xpath('instances//variable[descendant::derived[@name="Robin"]]/@name')
        for obj_name in robin_objs:
            src = self.xml_root.xpath('instances//addData/data/pou/body/ST/*[contains(text(), "{}();")]/text()'.format(obj_name))  #TODO handle spaces
            # src = self.xml_root.xpath('instances//addData/data/pou/body/ST/node()[contains(text(), "{}();")]/text()'.format(obj_name))  #TODO try
            if len(src) == 0:
                print_("Warning: no source found for robin object '{}'.".format(obj_name))
            elif len(src) > 1:
                raise RuntimeError("Robin object '{}' used in more than one POU.".format(obj_name))
            for line in StringIO(src[0]):
                # robins += self.get_robin_from_call(line, obj_name)
                robin = self.parse_robin_from_call(line, obj_name)
                if robin is not None:
                    self.src_gen.add_robin(robin)
        if len(self.src_gen.vars) == 0:
            raise RuntimeError('No valid robin objects found.')

    # parses robin from robin call
    def parse_robin_from_call(self, src, name):
        pat = "^[ ]*{}[ ]*\.[ ]*(read|write)[ ]*\([ ]*'([^ ,]+)'[ ]*,[ ]*([^ ,)]+)[ ]*\)[ ]*;".format(name)
        match = re.search(pat, src)
        if match is None:
            return None
        props = match.group(1, 2, 3)  # type, name, var_name
        if None in props:
            raise RuntimeError("Failed to parse robin call in '{}'.".format(src))
        return robin.Robin(self.types_map, self.xml_root, *props)