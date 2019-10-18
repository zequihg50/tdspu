#!/usr/bin/env python

import os, sys
import argparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

def generate(template, **kwargs):
	templates = os.path.join(os.path.dirname(__file__), 'data')
	env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))
	template = env.get_template(template)

	return template.render(**kwargs)

def esgf_parameters(name, ncml_location, ncmls):
	rel_paths = [f.replace(ncml_location, '').lstrip('/') for f in ncmls]

	return {
		'name': name,
		'ncml_location': ncml_location,
		'ncmls': rel_paths
	}

def main():
	# Arguments, change this for multiple '-p data=whatever -p ncmls=whatever'
	parser = argparse.ArgumentParser(description='Create ncml for files in directory.')
	parser.add_argument('--template', dest='template', type=str, default='catalog.xml.j2', help='Template file')
	parser.add_argument('--name', dest='name', type=str, help='Catalog name')
	parser.add_argument('--ncmls', dest='ncmls', type=str, help='Path to NcML files')
	args = parser.parse_args()

	ncmls = sys.stdin.read().splitlines()
	params = esgf_parameters(args.name, args.ncmls, ncmls)
	print(generate(args.template, **params))

if __name__ == '__main__':
	main()