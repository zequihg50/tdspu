#!/usr/bin/env python

import os
import argparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
    parser.add_argument('--dataset', dest='dataset', type=str, help='ZFS dataset path')
    args = parser.parse_args()

    catalogs_path = os.path.join(args.dataset, 'catalogs')
    ncmls_path = os.path.join(args.dataset, 'ncmls')
    ncmls = os.listdir(ncmls_path)

    # Jinja
    env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['xml']))
    template = env.get_template('catalog.xml.j2')

    with open(os.path.join(args.dataset, 'catalogs', 'catalog.xml'), 'w+') as fh:
        fh.write(template.render(
            name=os.path.basename(args.dataset),
            ncmls=map(lambda n: os.path.splitext(n)[0], ncmls),
            dataset=args.dataset))
