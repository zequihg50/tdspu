#!/usr/bin/env python

# Conventions:
# 1 - The parameter is the ZFS dataset path
# 2 - Every ZFS dataset contains the directories: data, ncmls, catalogs

import sys, os
import argparse
import netCDF4
import itertools

from jinja2 import Environment, FileSystemLoader, select_autoescape

def aggregate(files):
    aggregations = []
    files.sort() # itertools.groupby requires order
    for _, g in itertools.groupby(files, lambda file: os.path.basename(file).split('_')[0:2]):
        aggregations.append(list(g)) # g is an iterator, we want a list

    return aggregations

def ncoords(file, dimension):
    dataset = netCDF4.Dataset(file)
    size = dataset.dimensions[dimension].size
    dataset.close()

    return size

# class ncml_aggregator(object)
# def ncml_aggregator(files, dataset, aggregate=aggregate, template='ncml.j2')

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--dataset', dest='dataset', type=str, help='ZFS dataset path')
    args = parser.parse_args()

    # Generate aggregations
    files =  sys.stdin.read().splitlines()
    aggregations = aggregate(files)

    # Jinja
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    template = env.get_template('dataset.ncml.j2')

    # Generate ncml
    root = os.path.join(args.dataset, 'data')
    ncml = '-'.join(files[0].replace(root, '')[1:].split('/')[:5])
    file = ncml + '.ncml'

    with open(os.path.join(args.dataset, 'ncmls', file), 'w+') as fh:
        fh.write(template.render(aggregations=aggregations))
