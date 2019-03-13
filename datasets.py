#!/usr/bin/env python

# Usage: python datasets.py --root $(pwd)/data/cmip5/output1/NOAA-GFDL/GFDL-ESM2M/historical --dest $(pwd) --name test.ncml

import sys, os
import argparse
import netCDF4
import itertools

from jinja2 import Environment, FileSystemLoader, select_autoescape

if __name__ == '__main__':
    def get_files(path):
        for dirpath, dirnames, filenames in os.walk(path):
            if filenames:
                yield map(lambda f: os.path.join(dirpath, f), filenames)

    def ncoords(file, dimension):
        dataset = netCDF4.Dataset(file)
        size = dataset.dimensions[dimension].size
        dataset.close()

        return size

    # Arguments
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--root', dest='root', type=str, help='Path containing files')
    parser.add_argument('--name', dest='name', type=str, help='ncml filename')
    parser.add_argument('--dest', dest='dest', type=str, help='Path to ncml')
    args = parser.parse_args()

    # Jinja
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    template = env.get_template('dataset.ncml.j2')

    # Generate aggregations
    files = list(itertools.chain.from_iterable(get_files(args.root)))
    files.sort()
    groups = []
    for k, g in itertools.groupby(files, lambda file: os.path.basename(file).split('_')[0:2]):
        groups.append((k, list(g))) # g is an iterator, we want a list

    # Write ncml
    if(args.name is None):
        parts = args.root.split('/')[::-1][:5]
        args.name = '-'.join(parts) + '.ncml'

    if(args.dest is None):
        args.dest = '/tmp'

    with open(os.path.join(args.dest, args.name), 'w+') as fh:
        fh.write(template.render(groups=groups))
