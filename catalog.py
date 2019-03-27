#!/usr/bin/env python

import os
import argparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

def generate(template, **kwargs):
    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)), autoescape=select_autoescape(['xml']))
    template = env.get_template(template)

    return template.render(**kwargs)

def esgf_parameters(name, ncml_location, data_location):
    ncmls = os.listdir(ncml_location)

    return {
        'name': name,
        'ncml_location': ncml_location,
        'data_location': data_location,
        'ncmls': ncmls
    }

if __name__ == '__main__':
    # Arguments, change this for multiple '-p data=whatever -p ncmls=whatever'
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--template', dest='template', type=str, default='catalog.xml.j2', help='Template file')
    parser.add_argument('--name', dest='name', type=str, help='Catalog name')
    parser.add_argument('--ncmls', dest='ncmls', type=str, help='Path to NcML files')
    parser.add_argument('--data', dest='data', type=str, help='Root of datasetScan')
    args = parser.parse_args()

    params = esgf_parameters(args.name, args.ncmls, args.data)
    print(generate(args.template, **params))
