#!/usr/bin/env python

import os, sys
import argparse
import pandas as pd

# ncml
import netCDF4, itertools
from jinja2 import Environment, FileSystemLoader, select_autoescape

def aggregate(files):
    aggregations = []
    files.sort() # itertools.groupby requires order
    for _, g in itertools.groupby(files, lambda file: os.path.basename(file).split('_')[0:2]):
        aggregations.append(list(g)) # g is an iterator, we want a list

    return aggregations

def template(template, files, aggregator=aggregate):
    def ncoords(file, dimension):
        dataset = netCDF4.Dataset(file)
        size = dataset.dimensions[dimension].size
        dataset.close()

        return size

    templates = os.path.join(os.path.dirname(__file__), 'data')
    env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    template = env.get_template(template)
    params = { 'aggregations': aggregator(files) }

    return template.render(**params)

def main():
    parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
    parser.add_argument('--ncmls', dest='ncmls', type=str, help='Dest directory for NcML files')
    parser.add_argument('--root', dest='root', type=str, help='Directory to scan for netCDF files')
    parser.add_argument('--template', dest='template', type=str, default='esgf.ncml.j2', help='Template file')
    parser.add_argument('--aggregation', dest='aggregation', type=str, help='Aggregation spec. Comma separated facets, e.g "project,product,model"')
    args = parser.parse_args()

    df = pd.read_csv(sys.stdin)
    group = list(args.aggregation.split(','))
    grouped = df.groupby(group)

    template_file = args.template
    for name,group in grouped:
        ncml_name = '_'.join(name) + '.ncml'
        with open(os.path.join(args.ncmls, ncml_name), 'w+') as fh:
            fh.write(template(template_file, group['file'].values))

if __name__ == '__main__':
    main()
