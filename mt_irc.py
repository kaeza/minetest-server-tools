
__module_name__ = "mt_irc"
__module_version__ = "0.1.0"
__module_description__ = "Minetest IRC Mod Support plugin for HexChat/XChat"

import xchat

from ConfigParser import ConfigParser

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

if cfg.has_section("servers"):
	for key in cfg.options("servers"):
		key = key.lower()
		name = cfg.get("servers", key)
		known_servers_map[key] = name
		print 'Added server "%s" as "%s".' % (key, name)

main_re = re.compile(r"^:([^!]+)!.*")

mt_message_re = re.compile(r"^<(?P<player>[^>]+)> (?P<message>.*)")
mt_action_re = re.compile(r"^\* (?P<player>[^ ]+) (?P<action>.*)")
mt_join_re = re.compile(r"^\*\*\* (?P<player>[^ ]+) joined the game")
mt_part_re = re.compile(r"^\*\*\* (?P<player>[^ ]+) left the game")

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

	def rem(self, ident, force=False):
		ident_l = ident.lower()
		if force or (ident_l in self.users):
			i = self.users.index(ident_l)
			del self.users[i]
			cmd("recv :%s PART %s" % (ident, self.channame))

	def __del__(self):
		for ident in self.users[:]:
			self.rem(ident, True)

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

def del_user(chan, server, ident):
	global chanlist
	chanlist.get(chan).get(server).rem(ident)

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
	del_user(chan, server, ident)

handlers = (
	( mt_message_re, handle_message ),
	( mt_action_re,  handle_action  ),
	( mt_join_re,    handle_join    ),
	( mt_part_re,    handle_part    ),
)

def handle_server_quit(chan, server):
	global chanlist
	chanlist.get(chan).rem(server)

def quit_cb(word, word_eol, userdata):
	m = main_re.match(word[0])
	server = m.group(1)
	if server in known_servers_map:
		handle_server_quit(word[2], server)
		return xchat.EAT_XCHAT

def message_cb(word, word_eol, userdata):

	m = main_re.match(word[0])
	server = m.group(1)
	if not server in known_servers_map:
		return

	server_short = known_servers_map[server]

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

def unload_cb(userdata):
	print __module_description__, "unloading..."
	global chanlist
	del chanlist
	print __module_description__, 'version', __module_version__, ' unloaded!'

subcommands = { }

def doprint(subcmd, message):
	for line in message.split("\n"):
		line = "[mt_irc %s] %s" % (subcmd, line)
		print line

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
				known_servers_map[word[2]] = word[3]
				doprint('server', 'Server "%s" added as "%s".' % (word[2], word[3]))
			else:
				doprint('server', '[mt_irc server] Usage: /mt_irc server add BOTNICK ALIAS')
		elif subcmd == "remove":
			if len(word) == 3:
				if word[2] in known_servers_map:
					channels[chan].del_server(word[2])
					del known_servers_map[word[2]]
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
			doprint(subcommands[topic].__doc__)
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
			print '[mt_irc] Unknown subcommand "%s". Try "/mt_irc help".'
	else:
		print 'Usage: /mt_irc SUBCOMMAND'
		print 'Try "/mt_irc help".'
	return xchat.EAT_XCHAT

xchat.hook_unload(unload_cb)

xchat.hook_server("PRIVMSG", message_cb)
xchat.hook_server("PART", quit_cb)

xchat.hook_command("mt_irc", cmd_mt_irc)

print __module_description__, 'version', __module_version__, ' loaded.'
