#!/usr/bin/env python

import os, sys
import argparse
import pandas as pd

# ncml
import netCDF4
from jinja2 import Environment, FileSystemLoader, select_autoescape

def aggregate(group):
    aggregations = []
    grouped = group.groupby(['variable_id', 'table_id'])

    for name,aggregation in grouped:
        aggregations.append(sorted(list(aggregation['file'])))

    return aggregations

def template(template, **kwargs):
    def ncoords(file, dimension):
        dataset = netCDF4.Dataset(file)
        size = dataset.dimensions[dimension].size
        dataset.close()

        return size

    templates = os.path.join(os.path.dirname(__file__), 'data')
    env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    template = env.get_template(template)

    return template.render(**kwargs)

def main():
    parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
    parser.add_argument('--dest', dest='dest', type=str, help='Dest directory for NcML files. Allows formatted strings.')
    parser.add_argument('--template', dest='template', type=str, default='esgf.ncml.j2', help='Template file')
    parser.add_argument('--aggregation', dest='aggregation', type=str, default='project,product,model,experiment,ensemble,table', help='Aggregation spec. Comma separated facets, e.g "project,product,model"')

    args = parser.parse_args()

    df = pd.read_csv(sys.stdin)
    group_spec = list(args.aggregation.split(','))
    grouped = df.groupby(group_spec)

    template_file = args.template
    for name,group in grouped:
        # create dest path, formatted string values come from group name
        d = dict(zip(group_spec, name))
        path = args.dest.format(**d)
        os.makedirs(path, exist_ok=True)

        # write the ncml
        filename = '_'.join(name) + '.ncml'
        size = group['size'].sum()
        with open(os.path.join(path, filename), 'w+') as fh:
            params = { 'aggregations': aggregate(group),
                       'size': size
            }

            fh.write(template(template_file, **params))

if __name__ == '__main__':
    main()
