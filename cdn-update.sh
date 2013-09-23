#! /bin/bash

cd "$(dirname "$0")";

oIFS="$IFS";
IFS='
';

mkdir -p "/var/www/minetest-remote/";

for file in $(find worlds/K-World/game/ -name '*.png' -o -name '*.x' -o -name '*.ogg'); do
	cp "$file" "/var/www/minetest-remote/";
done

chown -R www-data:www-data "/var/www/minetest-remote/";

