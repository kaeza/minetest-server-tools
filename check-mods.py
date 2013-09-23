#! /usr/bin/env python

import os

def fexists(path):
	return (path[0] != '.') and os.path.isfile(path)

def dexists(path):
	return (path[0] != '.') and os.path.isdir(path)

JP = os.path.join

def do_check_mods(path, mods_ok, mods_err):
	for mod in os.listdir(path):
		if mod[0] == '.': continue
		fullpath = JP(path, mod)
		if dexists(fullpath):
			if fexists(JP(fullpath, "init.lua")):
				mods_ok.append((mod, fullpath))
			elif fexists(JP(fullpath, "modpack.txt")):
				do_check_mods(fullpath, mods_ok, mods_err)
			else:
				mods_err.append((mod, fullpath))

def check_mods(mod_paths):
	mods_ok = [ ]
	mods_err = [ ]
	for mod_path in mod_paths:
		if dexists(mod_path):
			do_check_mods(mod_path, mods_ok, mods_err)
	return mods_ok, mods_err

if __name__ == "__main__":
	mod_paths = (
		JP(os.getenv("HOME"), "minetest", "worlds", "K-World", "game", "mods"),
	)
	ok, err = check_mods(mod_paths)
	if len(err):
		print "Erroneous mods:"
		for mod in err:
			print "%s (from %s)" % mod
		import sys
		sys.exit(1)
	else:
		print "Everything OK!"

