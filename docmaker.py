#! /usr/bin/env python

import json, sys, os, os.path
from distutils.dir_util import copy_tree
from jinja2 import Environment,Template,FileSystemLoader
from xml.etree import ElementTree
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

exe = os.path.realpath(sys.argv[0])
template_dir = os.path.dirname(exe) + '/template'
resource_dir = os.path.dirname(exe) + '/resources'

env = Environment(loader=FileSystemLoader(template_dir))


class DocIndex():
    json = {}

    def __init__(self, xml):
        self.xml = xml

    def parse(self):
        self.json = {
            'site_title': self.xml.get('title'),
            'author': 'Papyros',
            'modules': [self.parse_module(module) for module in self.xml.findall('./namespace')]
        }

    def parse_module(self, xml):
        return {
            'name': xml.get('module'),
            'classes': self.parse_list(xml, 'qmlclass', self.parse_class, 
                                       key=lambda cls: cls['name'])
        }

    def parse_class(self, xml):
        return {
            'name': xml.get('name'),
            'summary': xml.get('brief'),
            'url': xml.get('href').replace('.dita', '.html')
        }

    def render(self):
        template = env.get_template('index.html')
        return template.render(self.json)

    def parse_list(self, xml, tag, function, key):
        items = [function(item) for item in xml.findall('./' + tag)]
        
        return sorted(items, key=key)

class Docfile():
    json = {}

    def __init__(self, xml):
        self.xml = xml

    def parse(self):
        self.json = {
            'title': self.xml.findtext('./apiName'),
            'site_title': self.xml.findtext('./prolog/metadata/prodinfo/prodname'),
            'author': 'Papyros',
            'description': '',
            'class': {
                'name': self.xml.findtext('./apiName'),
                'summary': self.xml.findtext('./shortdesc'),
                'description': format_xml(self.xml.find('./qmlTypeDetail/apiDesc')),
                'import': ('import ' + self.xml.findtext('./qmlTypeDetail/qmlImportModule/apiItemName') +
                        ' ' + self.xml.findtext('./qmlTypeDetail/qmlImportModule/apiData')),
                'properties': self.parse_list('qmlProperty', self.parse_property, 
                                              key=lambda property: property['name']),
                'methods': self.parse_list('qmlMethod', self.parse_method, 
                                           key=lambda method: method['name']),
                'signals': self.parse_list('qmlSignal', self.parse_signal, 
                                           key=lambda signal: signal['name'])
            }
        }

    def parse_property(self, xml):
        return {
            'id': xml.get('id'),
            'name': format_xml(xml.find('./qmlPropertyDetail/qmlPropertyDef/apiData')),
            'description': format_xml(xml.find('./qmlPropertyDetail/apiDesc'))
        }

    def parse_method(self, xml):
        return {
            'id': xml.get('id'),
            'name': format_xml(xml.find('./qmlMethodDetail/qmlMethodDef/apiData')),
            'description': format_xml(xml.find('./qmlMethodDetail/apiDesc'))
        }

    def parse_signal(self, xml):
        return {
            'id': xml.get('id'),
            'name': format_xml(xml.find('./qmlSignalDetail/qmlSignalDef/apiData')),
            'description': format_xml(xml.find('./qmlSignalDetail/apiDesc'))
        }

    def render(self):
        template = env.get_template('qmltype.html')
        return template.render(self.json)

    def parse_list(self, tag, function, key):
        items = [function(item) for item in self.xml.findall('./' + tag)]

        return sorted(items, key=key)

def format_code(code, language):
    lexer = get_lexer_by_name(language, stripall=True)
    formatter = HtmlFormatter()
    return highlight(code, lexer, formatter)

def format_xml(xml):
    if xml is None:
        return None

    for item in xml.iter('xref'):
        item.tag = 'a'
        item.set('href', item.get('href').replace('.dita', '.html'))
    for item in xml.iter('codeblock'):
        tail = item.tail
        code = ''.join(item.itertext())
        language = item.get('outputclass')

        item.tag = 'blockquote'
        item.clear()
        item.tail = tail
        item.append(ElementTree.fromstring(format_code(code, language)))
    for item in xml.iter('fig'):
        src = item.find('./image').get('href')
        caption = item.findtext('./image/alt')
        tail = item.tail

        item.clear()
        item.tag = 'img'
        item.set('src', src)
        item.set('class', 'materialboxed')
        item.set('data-caption', caption)
        item.tail = tail
    
    elements = [ElementTree.tostring(item).decode("utf-8") for item in xml]

    return xml.text + ''.join(elements)

if __name__=='__main__':
    out_dir = sys.argv[2]

    copy_tree(resource_dir, out_dir)
    copy_tree(sys.argv[1] + '/images', out_dir + '/images')

    for filename in os.listdir(sys.argv[1]):
        if filename.endswith('.dita'):
            try:
                with open(sys.argv[1] + '/' + filename) as f:
                    docfile = Docfile(ElementTree.parse(f))
                docfile.parse()

                html_file = filename.replace('.dita', '.html')

                with open(out_dir + '/' + html_file, 'w') as out:
                    out.write(docfile.render().encode('utf8'))
            except Exception as e:
                print("Unable to render " + filename + ": " + str(e))
        elif filename.endswith('.index'):
            with open(sys.argv[1] + '/' + filename) as f:
                docindex = DocIndex(ElementTree.parse(f).getroot())
            docindex.parse()
                
            with open(out_dir + '/index.html', 'w') as out:
                out.write(docindex.render().encode('utf8'))