#!/usr/bin/env python

import sys, os
import netCDF4

from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape

class Dataset(object):

    def __init__(self, root):
        self.root = root

    # Write this dataset to a ncml file with name 'name' in path 'dest'
    def ncml(self, name, dest, template='dataset.ncml.j2'):
        def get_files(path):
            files = []
            for dirpath, dirnames, filenames in os.walk(path):
                files.extend([os.path.join(path, dirpath, f) for f in filenames])
            files.sort()
            return files

        def get_ncoords(dataset, dimension='time'):
            return dataset.dimensions[dimension].size

        files = get_files(self.root)
        taggs = defaultdict(list)

        # Some datasets have directory but are empty
        if len(files) < 1:
            return

        for path in get_files(self.root):
            file = os.path.basename(path)
            var = '_'.join(file.split("_"))[0:2] # a variable is identified by (name,realm)

            dataset = netCDF4.Dataset(path)
            taggs[var].append( (path, get_ncoords(dataset)) )
            dataset.close()

        env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
        template = env.get_template(template)

        filepath = os.path.join(dest, name)
        with open(filepath, 'w+') as fh:
            fh.write(template.render(taggs=taggs))

if __name__ == '__main__':
    def get_directories(root):
        for dirpath, dirnames, filenames in os.walk(root):
            if not dirnames:
                yield os.path.split(dirpath)[0] # ignore versions

    root = sys.argv[1]
    dest = os.path.join(os.path.dirname(__file__), 'ncmls')
    for d in get_directories(root):
        ncml_name = d.replace(root,'').replace('/', '_') + '.ncml'
        Dataset(d).ncml(ncml_name, dest)
