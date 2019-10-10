#!/usr/bin/env python

import os, sys
import argparse
import pandas as pd

# ncml
import netCDF4, cftime
from jinja2 import Environment, FileSystemLoader, select_autoescape

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

def generate_ncml(df, template):
	fxs = df[df.table_id == 'fx'].file
	params = {	'aggregations': aggregate(df[df.table_id != 'fx'], ['variable_id', 'table_id']),
				'fxs': list(fxs),
				'size': df['size'].sum()
	}

	with open(args.filename, 'w+') as fh:
		fh.write(template(args.template, **params))

def main():
	parser = argparse.ArgumentParser(description='Read a csv formatted table of facets and files and generate NcMLs')
	parser.add_argument('--filename', dest='filename', type=str, default='', help='Template for NcML filenames using formatted strings. E.g. {project}_{product}_{model}_day.ncml')
	parser.add_argument('--dest', dest='dest', type=str, help='Template for destination directory of NcML files using formatted strings.')
	parser.add_argument('--template', dest='template', type=str, default='esgf.ncml.j2', help='Template file')
	parser.add_argument('--group-spec', dest='group_spec', type=str, help='Comma separated facet names, e.g "project,product,model"')

	parser.add_argument('--drs', dest='drs', type=str, help='Directory Reference Syntax: e.g. project/product/model/...')
	parser.add_argument('--root', dest='root', type=str, help='Directory substring before DRS')
	args = parser.parse_args()

	# Get all files
	files = pd.Series(dtype=str)
	for dirpath, dirnames, filenames in os.walk(args.root):
		ncs = [os.path.join(dirpath, f) for f in filenames if f.endswith('.nc')]
		files = pd.concat([files, pd.Series(ncs)])

	# Files size and last modification date
	sizes = pd.Series([os.stat(f).st_size for f in files], index=files.index)
	mtimes = pd.Series([os.stat(f).st_mtime for f in files], index=files.index)

	drs = args.drs.split('/')
	df = pd.DataFrame(	[os.path.dirname(os.path.relpath(f, args.root)).split('/') for f in files],
						columns=drs,
						index=files.index	)

	df['file'] = files
	df['size'] = sizes
	df['mtime'] = mtimes

	# df = pd.read_csv(sys.stdin)

	if args.group_spec is None:
		generate_ncml(df, args.template)
	else:
		group_spec = list(args.group_spec.split(','))
		grouped = df[df.table_id != 'fx'].groupby(group_spec)

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

			# ncml size
			size = group['size'].sum()

			# https://stackoverflow.com/questions/34157811/filter-a-pandas-dataframe-using-values-from-a-dict
			df_fx = df[df.table_id == 'fx']
			df_fx.loc[:, 'table_id'] = d['table_id']
			fxs = df_fx.loc[(df_fx[list(d)] == pd.Series(d)).all(axis=1)].file

			#build aggregations
			aggregations = []
			lists = aggregate(group, ['variable_id', 'table_id'])
			for l in lists:
				p = aggregation_data(l[0])
				adic = { 'files': l }
				adic.update(p)
				aggregations.append(adic)

			params = {	'aggregations': aggregations,
						'fxs': list(fxs),
						'size': size
			}

			with open(os.path.join(path, filename), 'w+') as fh:
				fh.write(template(args.template, **params))

if __name__ == '__main__':
	main()
