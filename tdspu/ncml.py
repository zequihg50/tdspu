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

def filter_project_facets(project, d):
	d.pop('frequency')
	if project.lower() == 'cmip5':
		d.pop('ensemble')

	return d

def aggregate(df, agg_spec):
	return df.sort_index().groupby(agg_spec, sort=False)

def main():
	parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
	parser.add_argument('--project', dest='project', type=str, help='CMIP5, CMIP6, CORDEX...')
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
		files = sys.stdin.read().splitlines()
	else:
		for dirpath, dirnames, filenames in os.walk(args.root):
			files.extend( [os.path.join(dirpath, f) for f in filenames if f.endswith('.nc')] )

	drs = args.drs.split('/')
	df_facets = pd.DataFrame([os.path.dirname(os.path.relpath(f, args.root)).split('/') for f in files], columns=drs)
	df_ncdata = pd.DataFrame([ncdata(f) for f in files])

	df = pd.concat([df_facets, df_ncdata], axis=1)
	df['size'] = [os.stat(f).st_size for f in files]
	#df['mtime'] = [os.stat(f).st_mtime for f in files]
	df.index = pd.Index(files, name='file')

	if args.group_spec is None:
		params = {	'aggregations': aggregate(df[~df.variable.isin(VARS_FX)], args.aggregation_spec),
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
			# because of r0i0p0 for cmip5 and cordex
			d = filter_project_facets(args.project, d)
			fxs = df[df.variable.isin(VARS_FX)].loc[(df[list(d)] == pd.Series(d)).all(axis=1)]

			aggregations = aggregate(group, args.aggregation_spec)

			params = {	'aggregations': aggregations,
						'fxs': list(fxs.index),
						'size': group['size'].sum() + fxs['size'].sum(),
						'time_units': aggregations.first().iloc[0].time_units,
						'time_start': aggregations.first().iloc[0].time_start,
						'time_increment': aggregations.first().iloc[0].time_increment
			}

			os.makedirs(os.path.dirname(dest), exist_ok=True)
			to_ncml(dest, args.template, **params)

if __name__ == '__main__':
	main()
