#! /bin/bash
[ "$1" ] || exit;
grep "$1" ~/.minetest/debug.txt | tail -n 50;

