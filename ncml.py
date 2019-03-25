#!/usr/bin/env python

# Conventions:
# 1 - The parameter is the ZFS dataset path
# 2 - Every ZFS dataset contains the directories: data, ncmls

import sys, os
import argparse
import netCDF4
import itertools

from jinja2 import Environment, FileSystemLoader, select_autoescape

class NcmlGenerator(object):
    def __init__(self, files, template='default.ncml.j2'):
        self.files = files
        self.template = template

    def aggregate(self):
        return self.files

    def generate(self):
        env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
        env.globals['ncoords'] = self.ncoords
        template = env.get_template(self.template)
        params = { 'aggregations': self.aggregate() }

        return template.render(**params)

    # Required in the jinja env to extract ncoords
    def ncoords(self, file, dimension):
        dataset = netCDF4.Dataset(file)
        size = dataset.dimensions[dimension].size
        dataset.close()

        return size

class EsgfNcmlGenerator(NcmlGenerator):
    def __init__(self):
        super().__init__(files, 'esgf.ncml.j2')

    def aggregate(self):
        aggregations = []
        self.files.sort() # itertools.groupby requires order
        for _, g in itertools.groupby(self.files, lambda file: os.path.basename(file).split('_')[0:2]):
            aggregations.append(list(g)) # g is an iterator, we want a list

        return aggregations

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--dataset', dest='dataset', type=str, help='ZFS dataset path')
    args = parser.parse_args()

    files =  sys.stdin.read().splitlines()

    # Generate ncml
    root = os.path.join(args.dataset, 'data')
    ncml = '_'.join(files[0].replace(root, '')[1:].split('/')[:5])
    file = ncml + '.ncml'

    generator = EsgfNcmlGenerator()

    with open(os.path.join(args.dataset, 'ncmls', file), 'w+') as fh:
        fh.write(generator.generate())
