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
        raise NotImplementedError('aggregate() is not implemented in your ncml generator')

    def generate(self):
        templates = os.path.join(os.path.dirname(__file__), 'data')
        env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))
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
    def __init__(self, files, template='esgf.ncml.j2'):
        super().__init__(files, template)

    def aggregate(self):
        aggregations = []
        self.files.sort() # itertools.groupby requires order
        for _, g in itertools.groupby(self.files, lambda file: os.path.basename(file).split('_')[0:2]):
            aggregations.append(list(g)) # g is an iterator, we want a list

        return aggregations

def main():
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--generator', dest='generator', type=str, default='EsgfNcmlGenerator', help='NcML generator class')
    args = parser.parse_args()

    files =  sys.stdin.read().splitlines()
    generator = globals()[args.generator](files)

    print(generator.generate())
