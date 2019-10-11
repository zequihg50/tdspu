#!/usr/bin/env python

import os, sys
import argparse
import pandas as pd

import netCDF4, cftime
from jinja2 import Environment, FileSystemLoader, select_autoescape

VARS_FX = ['areacella', 'areacellr', 'orog', 'sftlf', 'sftgif', 'mrsofc', 'rootd', 'zfull']

def to_ncml(name, template, **kwargs):
	templates = os.path.join(os.path.dirname(__file__), 'data')
	env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))

	t = env.get_template(template)
	with open(name, 'w+') as fh:
		fh.write(t.render(**kwargs))

def ncdata(file):
	ds = netCDF4.Dataset(file)

	if 'time' not in ds.variables:
		return {	'time_ncoords': None,
					'time_units': None,
					'time_start': None,
					'time_increment': None
		}

	ncoords = ds.dimensions['time'].size
	units = ds.variables['time'].units
	value0 = ds.variables['time'][0].data.item()
	value1 = ds.variables['time'][1].data.item()

	ds.close()

	return {	'time_ncoords': ncoords,
				'time_units': units,
				'time_start': value0,
				'time_increment': value1 - value0
	}

def main():
	parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
	parser.add_argument('--dest', dest='dest', type=str, help='Full path to destination file using formatted strings.')
	parser.add_argument('--template', dest='template', type=str, default='default.ncml.j2', help='Template file')
	parser.add_argument('--group-spec', dest='group_spec', type=str, help='Comma separated facet names, e.g "project,product,model"')
	parser.add_argument('--aggregation-spec', dest='aggregation_spec', type=str, default='variable', help='Comma separated facet names.')
	parser.add_argument('--drs', dest='drs', type=str, help='Directory Reference Syntax: e.g. project/product/model/...')
	parser.add_argument('--root', dest='root', type=str, help='Directory substring before DRS')
	parser.add_argument('--stdin', action='store_true', help='Instead of recursively find .nc files in root, read list of files from stdin')
	args = parser.parse_args()

	# Get all files
	files = []
	if args.stdin:
		files = sys.stdin.readlines()
	else:
		for dirpath, dirnames, filenames in os.walk(args.root):
			files.extend( [os.path.join(dirpath, f) for f in filenames if f.endswith('.nc')] )

	drs = args.drs.split('/')
	df_facets = pd.DataFrame([os.path.dirname(os.path.relpath(f, args.root)).split('/') for f in files], columns=drs)
	df_ncdata = pd.DataFrame([ncdata(f) for f in files])

	df = pd.concat([df_facets, df_ncdata], axis=1)
	df['size'] = [os.stat(f).st_size for f in files]
	df['mtime'] = [os.stat(f).st_mtime for f in files]
	df.index = pd.Index(files, name='file')

	if args.group_spec is None:
		params = {	'aggregations': df[~df.variable.isin(VARS_FX)].groupby(args.aggregation_spec),
					'fxs': list( df[df.variable.isin(VARS_FX)].index ),
					'size': df['size'].sum()
		}

		to_ncml(args.dest, args.template, **params)
	else:
		group_spec = args.group_spec.split(',')
		grouped = df[~df.variable.isin(VARS_FX)].groupby(group_spec)

		# each group contains .nc files for one .ncml
		for name,group in grouped:
			# create dest path, formatted string values come from group name
			d = dict(zip(group_spec, name))
			dest = args.dest.format(**d)

			# get fx files for this group
			fxs = df[df.variable.isin(VARS_FX)].loc[(df[list(d)] == pd.Series(d)).all(axis=1)]

			params = {	'aggregations': group.groupby(args.aggregation_spec),
						'fxs': list(fxs.index),
						'size': group['size'].sum() + fxs['size'].sum(),
						'time_units': group.iloc[0].time_units,
						'time_start': group.iloc[0].time_start,
						'time_increment': group.iloc[0].time_increment
			}

			os.makedirs(os.path.dirname(dest), exist_ok=True)
			to_ncml(dest, args.template, **params)

if __name__ == '__main__':
	main()
