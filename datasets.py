#!/usr/bin/env python

# Usage:
# python datasets.py --root $(pwd)/data/cmip5/output1/NOAA-GFDL/GFDL-ESM2M/historical --dest $(pwd) --name test.ncml
# find $(pwd)/data -maxdepth 5 -mindepth 5 -type d | xargs -I{} -n1 python datasets.py --root {} --dest datasets/

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
    parser.add_argument('--name', dest='name', type=str, help='ncml filename')
    parser.add_argument('--dest', dest='dest', type=str, help='Path to ncml')
    args = parser.parse_args()

    # Jinja
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
    env.globals['ncoords'] = ncoords
    dataset_template = env.get_template('dataset.ncml.j2')

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
        fh.write(dataset_template.render(groups=groups))

    # Open the catalog and append the dataset
    ET.register_namespace("", "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0")
    tree = ET.parse('catalog-template.xml')
    root = tree.getroot()
    dataset_root = root.find('{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}datasetRoot')

    print(args.name)
    nested_dataset = ET.SubElement(root, 'dataset')
    nested_dataset.attrib = {
        'name': args.name.split('.')[0],
        'ID': args.name.split('.')[0],
    }

    access = ET.SubElement(nested_dataset, 'access')
    access.attrib = {
        'serviceName': 'virtual',
        'urlPath': os.path.join(dataset_root.attrib['path'], 'datasets', args.name),
        'dataFormat': 'NcML'
    }

    for variable, files in groups:
        path = os.path.join(dataset_root.attrib['path'], '-'.join(variable))

        dataset = ET.SubElement(root, 'datasetScan')
        dataset.attrib = {
            'name': ' '.join(variable),
            'path': '-'.join(variable),
            'location': os.path.dirname(files[0])
        }

        filter = ET.SubElement(dataset, 'filter')
        filter_include = ET.SubElement(filter, 'include')
        filter_include.attrib = { 'wildcard': '_'.join(variable) + '*' }

    tree.write('catalog.xml')
