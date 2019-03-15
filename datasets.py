#!/usr/bin/env python

# Usage:
# python datasets.py --root $(pwd)/data/cmip5/output1/NOAA-GFDL/GFDL-ESM2M/historical --dest $(pwd) --name test.ncml
# find $(pwd)/data -maxdepth 5 -mindepth 5 -type d | xargs -I{} -n1 python datasets.py --root {} --dest datasets/


# python datasets.py --dataset /oceano/gmeteo/WORK/zequi/DATASETS/cmip5-esm-subset --root data/cmip5/output1/NOAA-GFDL/GFDL-ESM2M/historical

import sys, os
import argparse
import netCDF4
import itertools
import xml.etree.ElementTree as ET

from jinja2 import Environment, FileSystemLoader, select_autoescape

if __name__ == '__main__':
    def get_files(path):
        for dirpath, dirnames, filenames in os.walk(path):
            if filenames:
                # exclude seaIce
                if dirpath.split('/')[::-1][3] != 'seaIce':
                    yield map(lambda f: os.path.join(dirpath, f), filenames)

    def ncoords(file, dimension):
        dataset = netCDF4.Dataset(file)
        size = dataset.dimensions[dimension].size
        dataset.close()

        return size

    # Arguments
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--root', dest='root', type=str, help='Path containing files')
    parser.add_argument('--dataset', dest='DATASET', type=str, help='ZFS dataset path')
    args = parser.parse_args()

    DATASET = args.DATASET

    # Jinja
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    dataset_template = env.get_template('dataset.ncml.j2')

    # Generate aggregations
    datapath = os.path.join(DATASET, args.root)
    files = list(itertools.chain.from_iterable(get_files(datapath)))
    files.sort()
    groups = []
    for k, g in itertools.groupby(files, lambda file: os.path.basename(file).split('_')[0:2]):
        groups.append((k, list(g))) # g is an iterator, we want a list

    # Conventions:
    # 1 - The parameter is the ZFS dataset path
    # 2 - Every ZFS dataset contains the directories: data, ncmls, catalogs

    # Write ncml
    parts = args.root.split('/')[::-1][:3]
    ncml = '-'.join(parts)

    with open(os.path.join(DATASET, 'ncmls', (ncml + '.xml')), 'w+') as fh:
        fh.write(dataset_template.render(groups=groups))

    # Create catalogs for each (variable, realm) and keep catalogs name for later
    catalogs = []
    for variable, files in groups:
        # Jinja template variables
        catalog = ncml + '-' + '-'.join(variable)
        location = os.path.dirname(files[0])

        catalogs.append(catalog)
        template = env.get_template('catalog-var-agg.xml.j2')

        with open(os.path.join(DATASET, 'catalogs', (catalog + '.xml')), 'w+') as fh:
            fh.write(template.render(name=catalog,location=location,path=catalog,variable=variable, files=files))

    # Create catalog for virtual dataset
    template = env.get_template('catalog-dataset.xml.j2')

    with open(os.path.join(DATASET, 'catalogs', (ncml + '.xml')), 'w+') as fh:
        fh.write(template.render(DATASET=DATASET,ncml=ncml,path=os.path.basename(DATASET),catalog_name=ncml,catalogs=catalogs))
