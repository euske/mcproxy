Minecraft Logging Proxy
by Yusuke Shinyama <yusuke at cs dot nyu dot edu>


What is it?

This small Python script is a Minecraft proxy server. The primary
purpose of this program is to save the chat log and other various
activities (such as player position, player health and time). A proxy
server sits in between a client and a real server and relays the
communication for both direction. Since a proxy server acts just as a
normal Minecraft server, there's no client or server-side modification
needed.  The client can simply connect to the proxy server as if it
was a real server. The information through the proxy can be captured
and recorded on a disk.


Current supported version:

Minecraft 1.0


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
the localhost (127.0.0.1).  A text file is automatically created in
the current directory and a user's activity is saved.


Credits:

Many thanks to those who investigated the Minecraft protocol at 
Minecraft Coalition Wiki:
http://mc.kev009.com/Protocol


Terms and Conditions:

This program is in public domain.  
There's no need to ask permission of doing anything with this program.
