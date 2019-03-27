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
        env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)), autoescape=select_autoescape(['xml']))
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

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--generator', dest='generator', type=str, default='EsgfNcmlGenerator', help='NcML generator class')
    args = parser.parse_args()

    files =  sys.stdin.read().splitlines()
    generator = locals()[args.generator](files)

    print(generator.generate())
