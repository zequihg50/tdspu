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

def template(template, files, size, aggregator=aggregate):
    def ncoords(file, dimension):
        dataset = netCDF4.Dataset(file)
        size = dataset.dimensions[dimension].size
        dataset.close()

        return size

    templates = os.path.join(os.path.dirname(__file__), 'data')
    env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    template = env.get_template(template)
    params = { 'aggregations': aggregator(files),
               'size': size
    }

    return template.render(**params)

def main():
    parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
    parser.add_argument('--ncmls', dest='ncmls', type=str, help='Dest directory for NcML files')
    parser.add_argument('--template', dest='template', type=str, default='esgf.ncml.j2', help='Template file')
    parser.add_argument('--aggregation', dest='aggregation', type=str, default='project,product,model,experiment,ensemble,table', help='Aggregation spec. Comma separated facets, e.g "project,product,model"')
    parser.add_argument('--path-spec', dest='path_spec', type=str, default='', help='NcMLs file hierarchy e.g: experiment/frequency/ensemble')

    args = parser.parse_args()

    df = pd.read_csv(sys.stdin)
    group_spec = list(args.aggregation.split(','))
    grouped = df.groupby(group_spec)

    template_file = args.template
    for name,group in grouped:
        # create path according to path_spec
        if args.path_spec != '':
            path_spec = list(args.path_spec.split('/'))
            indices = [i for i,x in enumerate(group_spec) if x in path_spec]
            path_spec_values = [name[i] for i in indices]

            path = os.path.join(args.ncmls, *path_spec_values)
            os.makedirs(path, exist_ok=True)
        else:
            path = args.ncmls

        # write the ncml
        filename = '_'.join(name) + '.ncml'
        size = group['size'].sum()
        with open(os.path.join(path, filename), 'w+') as fh:
            fh.write(template(template_file, group['file'].values, size))

if __name__ == '__main__':
    main()
