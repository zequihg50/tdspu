from setuptools import setup, find_packages

setup(
    name="tdspu", # THREDDS Data Server Publication Utils
    version="0.16",
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3',
    install_requires=['netCDF4', 'Jinja2', 'pandas', 'cftime', 'argparse'],

    scripts=['tdspu/ncmlify', 'tdspu/csvify'],
    entry_points = {
        "console_scripts": [
            "ncml = tdspu.ncml:main",
            "catalog = tdspu.catalog:main",
        ],
    },

    author="zequihg50",
    author_email="ezequiel.cimadevilla@unican.es",
    description="Utils for NcML and TDS catalog generation",
)
