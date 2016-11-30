
from __future__ import print_function

__module_name__ = "mt_irc"
__module_version__ = "0.1.0"
__module_description__ = "Minetest IRC Mod Support plugin for HexChat/XChat"

import xchat

try:
	from ConfigParser import ConfigParser
except ImportError:
	from configparser import ConfigParser

import re
import os

HOME = os.getenv("HOME") or "."

CFGFILES = (
	os.path.join(HOME, "mt_irc.conf"),
	os.path.join(HOME, ".mt_irc_rc"),
)

cfg = ConfigParser()
cfg.read(CFGFILES)

known_servers_map = { }
known_servers_map_reverse = { }

if cfg.has_section("servers"):
	for key in cfg.options("servers"):
		name = cfg.get("servers", key)
		known_servers_map[key.lower()] = name
		known_servers_map_reverse[name.lower()] = key
		print('Added server "%s" as "%s".' % (key, name))

main_re = re.compile(r"^:([^!]+)!.*")

mt_message_re = re.compile(r"^<(?P<player>[^>]+)> (?P<message>.*)")
mt_action_re = re.compile(r"^\* (?P<player>[^ ]+) (?P<action>.*)")
mt_join_re = re.compile(r"^\*\*\* (?P<player>[^ ]+) joined the game")
mt_part_re = re.compile(r"^\*\*\* (?P<player>[^ ]+) left the game"
		+ r"(?P<timedout> [(]Timed out[)])?")

C1 = '\x01'

cmd = xchat.command

# channels[chan]: dict of channels
# channels[chan][server]: list of idents
# channels[chan][server][ident]: string
channels = { }

class Server:

	def __init__(self, channame, name):
		self.name = name
		self.channame = channame
		self.users = [ ]

	def add(self, ident):
		ident_l = ident.lower()
		if not ident_l in self.users:
			self.users.append(ident_l)
			cmd("recv :%s JOIN %s" % (ident, self.channame))

	def rem(self, ident, reason=None, force=False):
		reason = (" :"+reason) if reason else ""
		ident_l = ident.lower()
		if force or (ident_l in self.users):
			i = self.users.index(ident_l)
			del self.users[i]
			cmd("recv :%s PART %s%s" % (ident, self.channame, reason))

	def __del__(self):
		for ident in self.users[:]:
			self.rem(ident, "mt_irc: server deleted", True)

class Channel:

	def __init__(self, name):
		self.name = name
		self.servers = { }

	def get(self, name):
		name_l = name.lower()
		if not name_l in self.servers:
			self.servers[name_l] = Server(self.name, name)
		return self.servers[name_l]

	def rem(self, name):
		name_l = name.lower()
		if name_l in self.servers:
			del self.servers[name_l]

class ChannelList:

	def __init__(self):
		self.channels = { }

	def get(self, name):
		name_l = name.lower()
		if not name_l in self.channels:
			self.channels[name_l] = Channel(name)
		return self.channels[name_l]

	def rem(self, name, force=False):
		name_l = name.lower()
		if force or (name_l in self.channels):
			del self.channels[name_l]

chanlist = ChannelList()

def add_user(chan, server, ident):
	global chanlist
	chanlist.get(chan).get(server).add(ident)

def del_user(chan, server, ident, reason=None):
	global chanlist
	chanlist.get(chan).get(server).rem(ident, reason)

def handle_message(chan, server, ident, match):
	add_user(chan, server, ident)
	message = match.group("message")
	cmd("recv :%s PRIVMSG %s :%s" % (ident, chan, message))

def handle_action(chan, server, ident, match):
	add_user(chan, server, ident)
	action = match.group("action")
	cmd("recv :%s PRIVMSG %s :%sACTION %s%s" % (ident, chan, C1, action, C1))

def handle_join(chan, server, ident, match):
	add_user(chan, server, ident)

def handle_part(chan, server, ident, match):
	del_user(chan, server, ident, "timed out" if match.group(2) else None)

handlers = (
	( mt_message_re, handle_message ),
	( mt_action_re,  handle_action  ),
	( mt_join_re,    handle_join    ),
	( mt_part_re,    handle_part    ),
)

def quit_cb(word, word_eol, userdata):
	m = main_re.match(word[0])
	server = m.group(1)
	server_l = server.lower()
	if server_l in known_servers_map:
		global chanlist
		for chan in chanlist.channels:
			if server_l in chanlist.channels[chan].servers:
				chanlist.get(chan).rem(server)
				return

def message_cb(word, word_eol, userdata):
	m = main_re.match(word[0])
	server = m.group(1)
	server_l = server.lower()
	if not server_l in known_servers_map:
		return

	server_short = known_servers_map[server_l]

	chan = word[2].lower()
	message = word_eol[3][1:]

	for handler in handlers:
		regex, func = handler
		mm = regex.match(message)
		if mm:
			player = mm.group("player")
			ident = "%s@%s!%s@%s" % (player, server_short, player, server)
			func(chan, server, ident, mm)
			return xchat.EAT_XCHAT

pm_re = re.compile(r'^(?P<player>[^@]+)\@(?P<server>.+)$')
def out_message_cb(word, word_eol, userdata):
	chan = xchat.get_info("channel")
	m = pm_re.match(chan)
	if m:
		user = m.group("player")
		serv = m.group("server")
		serv_l = serv.lower()
		if serv_l in known_servers_map_reverse:
			message = word_eol[1]
			serv = known_servers_map_reverse[serv_l]
			xchat.command("msg %s @%s %s" % (serv, user, message))
			return xchat.EAT_XCHAT

def unload_cb(userdata):
	global chanlist
	print(__module_description__, "unloading...")
	del chanlist
	print(__module_description__, 'version', __module_version__, ' unloaded!')

subcommands = { }

def doprint(subcmd, message):
	print("[mt_irc %s] %s" % (subcmd, message))

def subcmd_server(word, word_eol):
	"""Manage servers.

	/mt_irc server add BOTNICK ALIAS
	  Add a new server.

	/mt_irc server remove BOTNICK
	  Remove an existing server. This also causes all fake users
	  for that server to part the channel.
	"""
	if len(word) > 1:
		subcmd = word[1]
		chan = xchat.get_info("channel")
		if subcmd == "add":
			if len(word) == 4:
				known_servers_map[word[2].lower()] = word[3].lower()
				known_servers_map_reverse[word[3].lower()] = word[2].lower()
				doprint('server', 'Server "%s" added as "%s".' % (word[2], word[3]))
			else:
				doprint('server', 'Usage: /mt_irc server add BOTNICK ALIAS')
		elif subcmd == "remove":
			if len(word) == 3:
				if word[2] in known_servers_map:
					channels[chan].del_server(word[2])
					del known_servers_map_reverse[known_servers_map[word[2].lower()]]
					del known_servers_map[word[2].lower()]
					doprint('server', 'Server "%s" removed.' % word[2])
				else:
					doprint('server', 'Unknown server "%s".' % word[2])
			else:
				doprint('server', 'Usage: /mt_irc server remove BOTNICK')
		else:
			doprint('server', 'Unknown subcommand "%s". Try "/mt_irc help server".' % subcmd)
	else:
		doprint('server', 'Invalid usage. Try "/mt_irc help server"')

def subcmd_info(word, word_eol):
	"""Show debug information.

	/mt_irc info
	  Show resume.

	/mt_irc info v[erbose]
	  Show resume.
	"""
	if len(word) == 1:
		chancount = len(chanlist.channels)
		servcount = 0
		usercount = 0
		for chan in chanlist.channels:
			servcount += len(chanlist.channels[chan].servers)
			for serv in chanlist.channels[chan].servers:
				usercount += len(chanlist.channels[chan].servers[serv].users)
		doprint('info', 'Totals: %d Channels, %d Servers, %d Users' % (chancount, servcount, usercount))
	elif (len(word) == 2) and ((word[1] == "v") or (word[1] == "verbose")):
		chancount = len(chanlist.channels)
		servcount = 0
		usercount = 0
		for chan in chanlist.channels:
			doprint('info', 'Channel %s:' % chanlist.channels[chan].name)
			servcount += len(chanlist.channels[chan].servers)
			for serv in chanlist.channels[chan].servers:
				doprint('info', '  Server %s:' % chanlist.channels[chan].servers[serv].name)
				usercount += len(chanlist.channels[chan].servers[serv].users)
				for user in chanlist.channels[chan].servers[serv].users:
					doprint('info', '    %s' % user)
		doprint('info', 'Totals: %d Channels, %d Servers, %d Users' % (chancount, servcount, usercount))
	else:
		doprint('info', 'Invalid usage. Try "/mt_irc help info"')

def subcmd_help(word, word_eol):
	"""Get help.

	/mt_irc help [SUBCOMMAND]
	  Get help for a sub-command. If no subcommand is specified,
	  it list all supported subcommands.
	"""
	if len(word) > 1:
		topic = word[1]
		if topic in subcommands:
			doprint('help', subcommands[topic].__doc__)
		else:
			doprint('help', 'Unknown subcommand "%s". Try "/mt_irc help".' % topic)
	else:
		for subcmd in subcommands:
			doprint('help', subcommands[subcmd].__doc__)

subcommands["server"] = subcmd_server
subcommands["info"] = subcmd_info
subcommands["help"] = subcmd_help

def cmd_mt_irc(word, word_eol, userdata):
	"""Manage mt_irc plugin configuration.

	Use "/mt_irc help" for subcommands.
	"""
	if len(word) > 1:
		subcmd = word[1]
		if subcmd in subcommands:
			subcmd = subcommands[subcmd]
			subcmd(word[1:], word_eol[1:])
		else:
			print('[mt_irc] Unknown subcommand "%s". Try "/mt_irc help".')
	else:
		print('Usage: /mt_irc SUBCOMMAND')
		print('Try "/mt_irc help".')
	return xchat.EAT_XCHAT

xchat.hook_unload(unload_cb)

xchat.hook_server("PRIVMSG", message_cb)
xchat.hook_server("QUIT", quit_cb)

xchat.hook_command("mt_irc", cmd_mt_irc)

xchat.hook_print("Your Message", out_message_cb)

print(__module_description__, 'version', __module_version__, ' loaded.')
