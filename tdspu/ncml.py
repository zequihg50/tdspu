#!/usr/bin/env python

import os, sys
import argparse
import pandas as pd

# ncml
import netCDF4
from jinja2 import Environment, FileSystemLoader, select_autoescape

def aggregate(group, group_spec):
    aggregations = []
    grouped = group.groupby(group_spec)

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
    parser.add_argument('--filename', dest='filename', type=str, default='',
        help='Template for NcML filenames using formatted strings. E.g. {project}_{product}_{model}_day.ncml')
    parser.add_argument('--dest', dest='dest', type=str,
        help='Template for destination directory of NcML files using formatted strings.')
    parser.add_argument('--template', dest='template', type=str, default='esgf.ncml.j2', help='Template file')
    parser.add_argument('--group-spec', dest='group_spec', type=str,
        help='Comma separated facet names, e.g "project,product,model"')
    args = parser.parse_args()

    df = pd.read_csv(sys.stdin)

    if args.group_spec is None:
        with open(args.filename, 'w+') as fh:
            params = { 'aggregations': aggregate(df, ['variable_id']),
                       'size': df['size'].sum()
            }

            fh.write(template('esgf.ncml.j2', **params))
            sys.exit(0)

    group_spec = list(args.group_spec.split(','))
    grouped = df[df.table_id != 'fx'].groupby(group_spec)

    template_file = args.template
    # each group is a ncml file and
    # each group contains the netCDF files that belong to that ncml file
    for name,group in grouped:
        # create dest path, formatted string values come from group name
        d = dict(zip(group_spec, name))
        path = args.dest.format(**d)
        os.makedirs(path, exist_ok=True)

        # ncml filename
        if args.filename == '':
            filename = '_'.join(name) + '.ncml'
        else:
            filename = args.filename.format(**d)

        size = group['size'].sum()
        with open(os.path.join(path, filename), 'w+') as fh:
            # https://stackoverflow.com/questions/34157811/filter-a-pandas-dataframe-using-values-from-a-dict
            df_fx = df[df.table_id == 'fx']
            df_fx.loc[:, 'table_id'] = d['table_id']
            fxs = df_fx.loc[(df_fx[list(d)] == pd.Series(d)).all(axis=1)].file

            params = { 'aggregations': aggregate(group, ['variable_id', 'table_id']),
                       'fxs': list(fxs),
                       'size': size
            }

            fh.write(template(template_file, **params))

if __name__ == '__main__':
    main()
