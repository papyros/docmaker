#! /usr/bin/env python3

import json, sys, os, os.path
from distutils.dir_util import copy_tree
from jinja2 import Environment,Template,FileSystemLoader
from xml.etree import ElementTree
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

exe = os.path.realpath(sys.argv[0])
resource_dir = os.path.dirname(exe) + '/resources'

env = Environment(loader=FileSystemLoader('template'), 
        extensions=['jinja2_highlight.HighlightExtension'])

class Docfile():
    json = {}

    def __init__(self, xml):
        self.xml = xml

    def parse(self):
        self.json['docs'] = {
            'title': self.xml.findtext('./prolog/metadata/prodinfo/prodname')
        }

        properties = []

        for prop in self.xml.findall('./qmlProperty'):
            info = {
                'id': prop.findtext('./apiName'),
                'name': format_xml(prop.find('./qmlPropertyDetail/qmlPropertyDef/apiData')),
                'description': format_xml(prop.find('./qmlPropertyDetail/apiDesc'))
            }

            properties.append(info)

        methods = []

        for method in self.xml.findall('./qmlMethod'):
            info = {
                'id': method.findtext('./apiName'),
                'name': format_xml(method.find('./qmlMethodDetail/qmlMethodDef/apiData')),
                'description': format_xml(method.find('./qmlMethodDetail/apiDesc'))
            }

            methods.append(info)

        self.json['item'] = {
            'name': self.xml.findtext('./apiName'),
            'summary': self.xml.findtext('./shortdesc'),
            'description': format_xml(self.xml.find('./qmlTypeDetail/apiDesc')),
            'import': ('import ' + self.xml.findtext('./qmlTypeDetail/qmlImportModule/apiItemName') +
                    ' ' + self.xml.findtext('./qmlTypeDetail/qmlImportModule/apiData')),
            'properties': properties,
            'methods': methods
        }

    def render(self):
        template = env.get_template('qmltype.html')
        return template.render(self.json)

def format_code(code, language):
    lexer = get_lexer_by_name(language, stripall=True)
    formatter = HtmlFormatter()
    return highlight(code, lexer, formatter)

def format_xml(xml):
    if xml is None:
        return None

    for item in xml.iter('xref'):
        item.tag = 'a'
    for item in xml.iter('codeblock'):
        tail = item.tail
        code = ''.join(item.itertext())
        language = item.get('outputclass')

        item.tag = 'blockquote'
        item.clear()
        item.tail = tail
        item.append(ElementTree.fromstring(format_code(code, language)))
    
    elements = [ElementTree.tostring(item).decode("utf-8") for item in xml]

    return xml.text + ''.join(elements)

if __name__=='__main__':
    out_dir = sys.argv[2]

    for filename in os.listdir(sys.argv[1]):
        if filename.endswith('.dita'):
            try:
                with open(sys.argv[1] + '/' + filename) as f:
                    docfile = Docfile(ElementTree.parse(f))
                    docfile.parse()

                html_file = filename.replace('.dita', '.html')

                with open(out_dir + '/' + html_file, 'w') as out:
                    out.write(docfile.render())
            except Exception as e:
                print("Unable to render " + filename + ": " + str(e))

    copy_tree(resource_dir, out_dir)