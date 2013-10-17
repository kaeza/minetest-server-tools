#! /bin/bash

me=$(basename "$0");

cmdline="$me $@";

base='';

exec='';
conf='';
restart=3;

mailto="$MAILTO";
mailto_lines=20;

editor="$EDITOR";
[ "$editor" ] || editor=vim;

usage()
{

cat << EOF
Usage: $me [OPTIONS] WORLDNAME

Available options:
  -h,--help             Show this help screen and exit.
  -b,--basedir X        Set base directory (*1).
  -c,--conf             Edit world configuration file (*2).
  -l,--mailto-lines X   Send up to \`X' lines of debug output (default 20) (*3)
  -m,--mailto X         Send log to email address \`X' in case of errors (*3).
  -n,--dry-run          Echo command to run server, but do not actually run.
  -r,--restart X        Restart \`X' times in case of errors (default 2).
  -s,--simple-run       Same as \`-r 0'.

Notes:
  (*1) This sets where the script should look for all files. The server should
       be located at \`\$basedir/bin/minetestserver', world should be at
       \`\$basedir/worlds/\$worldname', etc. If this is not specified, the
       script looks in \`./', then in \`../', relative to the directory where
       this script resides.
  (*2) The default editor is \`$editor' (change via \`\$EDITOR').
  (*3) If blank (the default if not overriden by this option or \`\$MAILTO'),
       no mail is sent. This assumes that the \`sendmail' program is installed
       and working. The \`-l' option is used to specify how many lines from
       \`debug.txt' to send (filtered via \`tail').

Exit status is 0 if everything was OK, -1 in case of command line errors, or 1
if server failed to start.
EOF

}

while [ $# -gt 0 ]; do
	case "$1" in
	-h|--help)
		usage;
		exit 0;
		;;
	-c|--conf)
		conf=y;
		;;
	-n|--dry-run)
		exec=echo;
		;;
	-s|--simple-run)
		once=y;
		;;
	-m|--mailto)
		[ $# -gt 1 ] || {
			echo "$me: missing required argument to \`$1'" >&2;
			exit -1;
		}
		mailto="$2";
		shift;
		;;
	-l|--mailto-lines)
		[ $# -gt 1 ] || {
			echo "$me: missing required argument to \`$1'" >&2;
			exit -1;
		}
		mailto_lines="$2";
		shift;
		;;
	-r|--restart)
		[ $# -gt 1 ] || {
			echo "$me: missing required argument to \`$1'" >&2;
			exit -1;
		}
		restart="$2";
		shift;
		;;
	-s|--simple-run)
		restart=0;
		;;
	-b|--basedir)
		[ $# -gt 1 ] || {
			echo "$me: missing required argument to \`$1'" >&2;
			exit -1;
		}
		base="$2";
		shift;
		;;
	-*)
		echo "$me: unknown option \`$1'" >&2;
		exit -1;
		;;
	*)
		[ "$w" ] && {
			echo "$me: error: multiple worlds specified: world is \`$w'" >&2;
			exit -1;
		}
		w="$1";
		;;
	esac
	shift;
done

[ "$w" ] || {
	echo "$me: no world specified. Try \`--help'." >&2;
	exit 1;
}

[ "$base" ] || base="$(dirname "$0")";

# Try to find server.
[    -x "$base/bin/minetestserver" ] || {
	base="$base/..";
	[ -x "$base/../bin/minetestserver" ] || {
		echo "$me: could not find server binary \`minetestserver'";
		exit 1;
	}
}

wp="$base/worlds/$w"
[ "$conf" ] && {
	exec "$editor" "$wp/server.conf";
}

restart=$((restart+1));

status=1;

while [ $restart -gt 0 ]; do
	$exec "$base/bin/minetestserver" \
		--config "$wp/server.conf" \
		--world "$wp";
	status=$?;
	[ $status -eq 0 ] && exit 0;
	[ "$exec" == "echo" ] && exit 0;
	restart=$((restart-1));
done

[ "$mailto" ] || exit $status;

[ "$mailto_lines" ] || mailto_lines=20;

debug_lines=$(tail "$base/debug.txt" -n $mailto_lines);

sendmail "$mailto" << EOF
Subject: Minetest Server Error

Your Minetest server exited with an error.
Below are the last $mailto_lines lines of \`debug.txt':

---- BEGIN LOG ----
$debug_lines
---- END LOG ----

The script was started with the command:
  $cmdline

The final command to run the server was:
  $base/bin/minetestserver \\
    --config "$wp/server.conf" \\
    --world "$wp";
EOF
