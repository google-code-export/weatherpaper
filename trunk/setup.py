from distutils.core import setup
import py2exe

setup(
	name="Weather Wallpaper",
	options = {'py2exe': {'bundle_files': 1}},
	windows = [{
		'script': "weatherpaper.pyw",
		"icon_resources": [(1, "out.ico")]
	}],
	zipfile = None,
)
