
__module_name__ = "mt_irc"
__module_version__ = "0.1.0"
__module_description__ = "Minetest IRC Mod Support plugin for HexChat/XChat"

import xchat

import re

# Part message for players.
# If None, a plain "PART" is sent.
PART_MESSAGE = None

# Add your name mappings here.
# This list (actually, a dictionary) serves two purposes:
# First, it lists which IRC users are bots from the IRC mod, and second,
# maps bot nicks to server names. This can be used to e.g. shorten the
# suffix (or host, or whatever) displayed in [he]xchat.
known_servers_map = {
	"ShadowServer": "Sn-S",
	"VE-Creative":  "VE-C",
	"VE-Survival":  "VE-S",
	"K-Server":     "K-Sv",
	"MT-Nostalgia": "MT-N",
}

main_re = re.compile(r"^:([^!]+)!.*")

mt_message_re = re.compile(r"^<(?P<player>[^>]+)> (?P<message>.*)")
mt_action_re = re.compile(r"^\* (?P<player>[^ ]+) (?P<action>.*)")
mt_join_re = re.compile(r"^\*\*\* (?P<player>[^ ]+) joined the game")
mt_part_re = re.compile(r"^\*\*\* (?P<player>[^ ]+) left the game")

C1 = '\x01'

cmd = xchat.command

def handle_message(chan, ident, match):
	message = match.group("message")
	cmd("recv :%s PRIVMSG %s :%s" % (ident, chan, message))

def handle_action(chan, ident, match):
	action = match.group("action")
	cmd("recv :%s PRIVMSG %s :%sACTION %s%s" % (ident, chan, C1, action, C1))

def handle_join(chan, ident, match):
	cmd("recv :%s JOIN %s" % (ident, chan))

def handle_part(chan, ident, match):
	if PART_MESSAGE:
		cmd("recv :%s PART %s :%s" % (ident, chan, PART_MESSAGE))
	else:
		cmd("recv :%s PART %s" % (ident, chan))

handlers = (
	( mt_message_re, handle_message ),
	( mt_action_re,  handle_action  ),
	( mt_join_re,    handle_join    ),
	( mt_part_re,    handle_part    ),
)

def message_cb(word, word_eol, userdata):

	m = main_re.match(word[0])
	server = m.group(1)
	if not server in known_servers_map:
		return

	server_short = known_servers_map[server]

	chan = word[2]
	message = word_eol[3][1:]

	for handler in handlers:
		regex, func = handler
		mm = regex.match(message)
		if mm:
			player = mm.group("player")
			ident = "%s@%s!%s@%s" % (player, server_short, player, server)
			func(chan, ident, mm)
			return xchat.EAT_XCHAT

def unload_cb(userdata):
	print __module_description__, 'version', __module_version__, ' unloaded.'

xchat.hook_unload(unload_cb)

xchat.hook_server("PRIVMSG", message_cb)

print __module_description__, 'version', __module_version__, ' loaded.'
