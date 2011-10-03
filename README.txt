Minecraft Chatlog Proxy
by Yusuke Shinyama <yusuke at cs dot nyu dot edu>


What is it?

This small Python script acts as a "proxy", an intermediate server
which relays communication between a client and a real server. It can also
capture various information about the data which is running through it.
Although the primary purpose of this is to save the chat log on a local disk,
the parser is made in such a way that you can extend it to record other kinds
of information (e.g. player coordinates).

The beauty of this is that since this program itself acts as a server,
no client or server-side modification is needed. The user can simply
connect to localhost as if it was a real server and play it normally.
Every chat text will be automatically saved onto the current directory.


Current supported version:

1.8 beta


How to use:

You need Python 2.6 or later (Python 3.0 is *not* supported!)  and
decent knowledge about using command line interface to run this
program.  Just put this script on any directory and run it from
a command line prompt, as in:

On Linux:
  $ python mcproxy.py minecraftserver.example.com:25565

On Windows:
  > python mcproxy.py minecraftserver.example.com:25565

Note that you need to pass the address and port of the real server
you're connecting to. Then launch a Minecraft client and connect to
localhost.


Credits:

Many thanks to those who investigated the Minecraft protocol at 
Minecraft Coalition Wiki:
http://mc.kev009.com/Protocol


Terms and Conditions:

This program is in public domain.  
There's no need to ask permission of doing anything with this program.


Enjoy!
