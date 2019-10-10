#!/usr/bin/env python

import os, sys
import argparse
import pandas as pd

# ncml
import netCDF4, cftime
from jinja2 import Environment, FileSystemLoader, select_autoescape

VARS_FX = ['areacella', 'areacellr', 'orog', 'sftlf', 'sftgif', 'mrsofc', 'rootd', 'zfull']

def aggregate(group, group_spec):
	aggregations = []
	first_dates = []
	grouped = group.groupby(group_spec, sort=False)

	for name,df in grouped:
		df.sort_values(by='file', inplace=True)

		aggregations.append(list(df['file']))

	return aggregations

def aggregation_data(file):
	ds = netCDF4.Dataset(file)
	units = ds.variables['time'].units
	value0 = ds.variables['time'][0].data.item()
	value1 = ds.variables['time'][1].data.item()
	ds.close()

	date = cftime.num2date(value0, units)
#	first_dates.append(date)

	return {	'time_units': units,
				'time_start': value0,
				'time_increment': value1 - value0
	}

def to_ncml(name, template, **kwargs):
	def ncoords(file, dimension):
		dataset = netCDF4.Dataset(file)
		size = dataset.dimensions[dimension].size
		dataset.close()

		return size

	templates = os.path.join(os.path.dirname(__file__), 'data')
	env = Environment(loader=FileSystemLoader(templates), autoescape=select_autoescape(['xml']))
	env.globals['ncoords'] = ncoords

	t = env.get_template(template)
	with open(name, 'w+') as fh:
		fh.write(t.render(**kwargs))

def main():
	parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
	parser.add_argument('--dest', dest='dest', type=str, help='Full path to destination file using formatted strings.')
	parser.add_argument('--template', dest='template', type=str, default='esgf.ncml.j2', help='Template file')
	parser.add_argument('--group-spec', dest='group_spec', type=str, help='Comma separated facet names, e.g "project,product,model"')
	parser.add_argument('--aggregation-spec', dest='aggregation_spec', type=str, default='variable', help='Comma separated facet names.')
	parser.add_argument('--drs', dest='drs', type=str, help='Directory Reference Syntax: e.g. project/product/model/...')
	parser.add_argument('--root', dest='root', type=str, help='Directory substring before DRS')
	args = parser.parse_args()

	# Get all files
	files = pd.Series(dtype=str)
	for dirpath, dirnames, filenames in os.walk(args.root):
		ncs = [os.path.join(dirpath, f) for f in filenames if f.endswith('.nc')]
		files = pd.concat([files, pd.Series(ncs)])

	# Size and last modification date for all files
	sizes = [os.stat(f).st_size for f in files]
	mtimes = [os.stat(f).st_mtime for f in files]

	drs = args.drs.split('/')
	df = pd.DataFrame(	[os.path.dirname(os.path.relpath(f, args.root)).split('/') for f in files],
						columns=drs)

	df['file'] = list(files)
	df['size'] = sizes
	df['mtime'] = mtimes

	# df = pd.read_csv(sys.stdin)

	if args.group_spec is None:
		params = {	'aggregations': aggregate(df[~df.variable.isin(VARS_FX)], args.aggregation_spec),
					'fxs': list( df[df.variable.isin(VARS_FX)].file ),
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
			# https://stackoverflow.com/questions/34157811/filter-a-pandas-dataframe-using-values-from-a-dict
			fxs = df[df.variable.isin(VARS_FX)].loc[(df[list(d)] == pd.Series(d)).all(axis=1)].file

			#build aggregations
			aggregations = []
			lists = aggregate(group, args.aggregation_spec)
			for l in lists:
				p = aggregation_data(l[0])
				adic = { 'files': l }
				adic.update(p)
				aggregations.append(adic)

			params = {	'aggregations': aggregations,
						'fxs': list(fxs),
						'size': group.size.sum() + fxs.size.sum()
			}

			os.makedirs(os.path.dirname(dest), exist_ok=True)
			to_ncml(dest, args.template, **params)

if __name__ == '__main__':
	main()
