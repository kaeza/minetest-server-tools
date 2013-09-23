#! /bin/bash
me=$(basename "$0");
cd "$(dirname "$0")";
exec=exec;
conf='';
check_dupe_ips='';
while [ $# -gt 0 ]; do
	case "$1" in
		-c|--conf)
			conf=y;
			;;
		-n|--dry-run)
			exec=echo;
			;;
		-d|--check-dupe-ips)
			check_dupe_ips=y;
			;;
		-*)
			echo "$me: unknown option \`$1'" >&2;
			exit 1;
			;;
		*)
			if [ "$w" ]; then
				echo "$me: error: multiple worlds specified: world is \`$w'" >&2;
				exit 1;
			fi
			w="$2";
			shift;
			;;
	esac
	shift;
done
base=".";
w="$1";
[ "$w" ] || w="K-World";
wp="$base/worlds/$w"
if [ "$conf" ]; then
	exec vim "$wp/server.conf";
fi

if [ "$check_dupe_ips" ]; then

	cat "$wp/players.iplist" | {
		while read line; do
			ip=$(echo "$line" | cut -d '|' -f 2);
			echo "=== IP: $ip ===";
			grep "$ip" "$wp/players.iplist" | cut -d '|' -f 1;
			echo;
		done
	}
	exit 0;

fi

$exec bin/minetestserver \
	--config "$wp/server.conf" \
	--world "$(pwd)/worlds/$w";

