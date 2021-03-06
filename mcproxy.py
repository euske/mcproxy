#!/usr/bin/env python
##
##  Minecraft Logger Proxy by Yusuke Shinyama
##  * this program is in public domain *
##
##  Supported version: Minecraft 1.2 / Protocol version 29 (2012/4/10)
##
##  usage: $ python mcproxy.py mcserver.example.com
##

import sys, os, os.path
import re
import time
import socket
import asyncore
from struct import pack, unpack


def toshort(x):
    return unpack('>h', x)[0]
def toint(x):
    return unpack('>i', x)[0]
def tolong(x):
    return unpack('>q', x)[0]
def touni(x):
    return x.decode('utf-16be')
def dist((x0,y0,z0),(x1,y1,z1)):
    return abs(x0-x1)+abs(y0-y1)+abs(z0-z1)


##  MCParser
##  (for Protocol. cf. http://mc.kev009.com/wiki/index.php?title=Protocol&oldid=1810)
##
class MCParser(object):

    debugfp = None

    class MCParserError(Exception): pass
    class ProtocolError(MCParserError): pass
    
    def __init__(self, safemode=False):
        self.safemode = safemode
        self._stack = [(self._main,None)]
        self._pos = 0
        self._active = True
        return

    def feed(self, data):
        if self.debugfp is not None:
            print >>self.debugfp, 'feed: %r: %r' % (self._pos, self._stack)
            self.debugfp.flush()
        if not self._active: return
        i = 0
        try:
            while i < len(data):
                (parse,arg) = self._stack[-1]
                if parse(data[i], arg):
                    i += 1
            self._pos += len(data)
        except self.ProtocolError, e:
            print >>self.debugfp, 'protocol error: %r: %r' % (self._pos+i, e)
            if self.safemode:
                self._active = False
            else:
                raise
        return

    def _push(self, func, arg=None):
        if arg is None:
            arg = ['']
        elif isinstance(arg, int):
            arg = [arg]
        self._stack.append((func, arg))
        return
    
    def _pop(self):
        self._stack.pop()
        return

    def _bytes(self, c, arg):
        if 0 < arg[0]:
            arg[0] -= 1
            return True
        elif 0 == arg[0]:
            self._pop()
            return False
        else:
            raise self.ProtocolError('invalid bytes: %r' % arg[0])
    
    def _str8(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._bytes, toshort(arg[0]))
        return True

    def _str16(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._bytes, toshort(arg[0])*2)
        return True

    def _login_info(self, entid, username):
        #print 'login', (entid, username)
        return

    def _server_info(self, wtype, mode, dim, diff, height):
        #print 'server', (wtype, mode, dim, diff, height)
        return

    def _chat_text(self, s):
        #print 'text', repr(s)
        return

    def _time_update(self, t):
        #print 'time', t
        return

    def _player_pos(self, x, y, z):
        #print 'pos', (x,y,z)
        return
    
    def _player_health(self, hp, food, sat):
        #print 'health', (hp,food,sat)
        return
    
    def _mob_spawn(self, eid, t, x, y, z):
        #print 'mob', (eid,t,x,y,z)
        return

    def _map_chunk(self, (x,z,g,b1,b2), nbytes):
        #print 'map', (x,y,g,b1,b2), nbytes
        self._push(self._bytes, nbytes)
        return
        
    def _special_01(self, c, arg): # int
        arg[0] += c
        if len(arg[0]) == 4:
            self._pop()
            self._push(self._special_01_2, ['', toint(arg[0])])
        return True
    def _special_01_2(self, c, arg): # str16
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._special_01_3, ['', arg[1], toshort(arg[0])*2])
        return True
    def _special_01_3(self, c, arg):
        if len(arg[0]) == arg[2]:
            self._pop()
            self._login_info(arg[1], touni(arg[0]))
            self._push(self._special_01_4)
            return False
        arg[0] += c
        return True
    def _special_01_4(self, c, arg): # str16
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._special_01_5, ['', toshort(arg[0])*2])
        return True
    def _special_01_5(self, c, arg):
        if len(arg[0]) == arg[1]:
            self._pop()
            self._push(self._special_01_6, ['', touni(arg[0])])
            return False
        arg[0] += c
        return True
    def _special_01_6(self, c, arg): # (int,int,byte,ubyte,ubyte)
        arg[0] += c
        if len(arg[0]) == 11:
            self._pop()
            (mode,dim,diff,height,nplayers) = unpack('>iibBB', arg[0])
            self._server_info(arg[1], mode, dim, diff, height)
        return True
    
    def _special_03(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._special_03_2, ['', toshort(arg[0])*2])
        return True
    def _special_03_2(self, c, arg):
        if len(arg[0]) == arg[1]:
            self._pop()
            self._chat_text(touni(arg[0]))
            return False
        arg[0] += c
        return True
        
    def _special_04(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 8:
            self._pop()
            self._time_update(tolong(arg[0]))
        return True
        
    def _special_06(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 12:
            self._pop()
            (x,y,z) = unpack('>iii', arg[0])
            self._player_pos(x,y,z)
        return True
        
    def _special_08(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 8:
            self._pop()
            (hp,food,sat) = unpack('>hhf', arg[0])
            self._player_health(hp, food, sat)
        return True
        
    def _special_09(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 8:
            self._pop()
            self._push(self._special_09_2, ['', arg[0]])
        return True
    def _special_09_2(self, c, arg): # str16
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._special_09_3, ['', arg[1], toshort(arg[0])*2])
        return True
    def _special_09_3(self, c, arg):
        if len(arg[0]) == arg[2]:
            self._pop()
            (dim,diff,mode,height) = unpack('>ibbh', arg[1])
            self._server_info(touni(arg[0]), mode, dim, diff, height)
            return False
        arg[0] += c
        return True

    def _special_0b(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 33:
            self._pop()
            (x,y,s,z,ground) = unpack('>ddddB', arg[0])
            self._player_pos(x,y,z)
        return True
        
    def _special_0d(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 41:
            self._pop()
            (x,y,s,z,yaw,pitch,ground) = unpack('>ddddffB', arg[0])
            self._player_pos(x,y,z)
        return True
        
    def _special_17(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 4:
            self._pop()
            if 0 < toint(arg[0]):
                self._push(self._bytes, 6)
        return True
    
    def _special_18(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 20:
            self._pop()
            (eid,t,x,y,z,yaw,pitch,head) = unpack('>ibiiibbb', arg[0])
            self._mob_spawn(eid,t,x/32.0,y/32.0,z/32.0)
        return True
    
    def _special_33(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 21:
            self._pop()
            (x,z,g,b1,b2,nbytes,_) = unpack('>iibHHii', arg[0])
            self._map_chunk((x,z,g,b1,b2), nbytes)
        return True

    def _special_34(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 4:
            self._pop()
            n = toint(arg[0])
            self._push(self._bytes, n)
        return True

    def _special_3c(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 4:
            self._pop()
            n = toint(arg[0])
            self._push(self._bytes, n*3)
        return True

    def _special_68(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._special_68_2, toshort(arg[0]))
        return True
    def _special_68_2(self, c, arg):
        if arg[0]:
            arg[0] -= 1
            self._push(self._slotdata)
        else:
            self._pop()
        return False

    def _special_83(self, c, arg):
        self._pop()
        self._push(self._bytes, ord(c))
        return True

    def _special_fa(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            self._push(self._bytes, toshort(arg[0]))
        return True
    
    ENCHANTABLE_ITEMS = set([
        0x103, #Flint and steel
        0x105, #Bow
        0x15A, #Fishing rod
        0x167, #Shears

        #TOOLS
        #sword, shovel, pickaxe, axe, hoe
        0x10C, 0x10D, 0x10E, 0x10F, 0x122, #WOOD
        0x110, 0x111, 0x112, 0x113, 0x123, #STONE
        0x10B, 0x100, 0x101, 0x102, 0x124, #IRON
        0x114, 0x115, 0x116, 0x117, 0x125, #DIAMOND
        0x11B, 0x11C, 0x11D, 0x11E, 0x126, #GOLD
        
        #ARMOUR
        #helmet, chestplate, leggings, boots
        0x12A, 0x12B, 0x12C, 0x12D, #LEATHER
        0x12E, 0x12F, 0x130, 0x131, #CHAIN
        0x132, 0x133, 0x134, 0x135, #IRON
        0x136, 0x137, 0x138, 0x139, #DIAMOND
        0x13A, 0x13B, 0x13C, 0x13D  #GOLD
        ])
    def _slotdata(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            bid = toshort(arg[0])
            if 0 <= bid:
                if bid in self.ENCHANTABLE_ITEMS:
                    self._push(self._slotdata_extra)
                self._push(self._bytes, 3)
        return True
    def _slotdata_extra(self, c, arg):
        arg[0] += c
        if len(arg[0]) == 2:
            self._pop()
            n = toshort(arg[0])
            if 0 < n:
                self._push(self._bytes, n)
        return True
    
    def _metadata(self, c, arg):
        c = ord(c)
        if c == 0x7f:
            self._pop()
        else:
            x = (c >> 5)
            if x == 0:
                self._push(self._bytes, 1)
            elif x == 1:
                self._push(self._bytes, 2)
            elif x == 2:
                self._push(self._bytes, 4)
            elif x == 3:
                self._push(self._bytes, 4)
            elif x == 4:
                self._push(self._str16)
            elif x == 5:
                self._push(self._bytes, 5)
            elif x == 6:
                self._push(self._bytes, 12)
            else:
                raise self.ProtocolError('invalid metadata: %r' % c)
        return True
        
    def _main(self, c, arg):
        if self.debugfp is not None:
            print >>self.debugfp, 'main: %02x' % ord(c)
        c = ord(c)
        if c == 0x00:
            self._push(self._bytes, 4)
        elif c == 0x01:
            self._push(self._special_01)
        elif c == 0x02:
            self._push(self._str16)
        elif c == 0x03:
            self._push(self._special_03)
        elif c == 0x04:
            self._push(self._special_04)
        elif c == 0x05:
            self._push(self._bytes, 10)
        elif c == 0x06:
            self._push(self._special_06)
        elif c == 0x07:
            self._push(self._bytes, 9)
        elif c == 0x08:
            self._push(self._special_08)
        elif c == 0x09:
            self._push(self._special_09)
        elif c == 0x0a:
            self._push(self._bytes, 1)
        elif c == 0x0b:
            self._push(self._special_0b)
        elif c == 0x0c:
            self._push(self._bytes, 9)
        elif c == 0x0d:
            self._push(self._special_0d)
        elif c == 0x0e:
            self._push(self._bytes, 11)
        elif c == 0x0f:
            self._push(self._slotdata)
            self._push(self._bytes, 10)
        elif c == 0x10:
            self._push(self._bytes, 2)
        elif c == 0x11:
            self._push(self._bytes, 14)
        elif c == 0x12:
            self._push(self._bytes, 5)
        elif c == 0x13:
            self._push(self._bytes, 5)
        elif c == 0x14:
            self._push(self._bytes, 16)
            self._push(self._str16)
            self._push(self._bytes, 4)
        elif c == 0x15:
            self._push(self._bytes, 24)
        elif c == 0x16:
            self._push(self._bytes, 8)
        elif c == 0x17:
            self._push(self._special_17)
            self._push(self._bytes, 17)
        elif c == 0x18:
            self._push(self._metadata)
            self._push(self._special_18)
        elif c == 0x19:
            self._push(self._bytes, 16)
            self._push(self._str16)
            self._push(self._bytes, 4)
        elif c == 0x1a:
            self._push(self._bytes, 18)
        elif c == 0x1b:
            self._push(self._bytes, 18)
        elif c == 0x1c:
            self._push(self._bytes, 10)
        elif c == 0x1d:
            self._push(self._bytes, 4)
        elif c == 0x1e:
            self._push(self._bytes, 4)
        elif c == 0x1f:
            self._push(self._bytes, 7)
        elif c == 0x20:
            self._push(self._bytes, 6)
        elif c == 0x21:
            self._push(self._bytes, 9)
        elif c == 0x22:
            self._push(self._bytes, 18)
        elif c == 0x23:
            self._push(self._bytes, 5)
        elif c == 0x26:
            self._push(self._bytes, 5)
        elif c == 0x27:
            self._push(self._bytes, 8)
        elif c == 0x28:
            self._push(self._metadata)
            self._push(self._bytes, 4)
        elif c == 0x29:
            self._push(self._bytes, 8)
        elif c == 0x2a:
            self._push(self._bytes, 5)
        elif c == 0x2b:
            self._push(self._bytes, 8)
        elif c == 0x32:
            self._push(self._bytes, 9)
        elif c == 0x33:
            self._push(self._special_33)
        elif c == 0x34:
            self._push(self._special_34)
            self._push(self._bytes, 10)
        elif c == 0x35:
            self._push(self._bytes, 11)
        elif c == 0x36:
            self._push(self._bytes, 12)
        elif c == 0x3c:
            self._push(self._special_3c)
            self._push(self._bytes, 28)
        elif c == 0x3d:
            self._push(self._bytes, 17)
        elif c == 0x46:
            self._push(self._bytes, 2)
        elif c == 0x47:
            self._push(self._bytes, 17)
        elif c == 0x64:
            self._push(self._bytes, 1)
            self._push(self._str16)
            self._push(self._bytes, 2)
        elif c == 0x65:
            self._push(self._bytes, 1)
        elif c == 0x66:
            self._push(self._slotdata)
            self._push(self._bytes, 7)
        elif c == 0x67:
            self._push(self._slotdata)
            self._push(self._bytes, 3)
        elif c == 0x68:
            self._push(self._special_68)
            self._push(self._bytes, 1)
        elif c == 0x69:
            self._push(self._bytes, 5)
        elif c == 0x6a:
            self._push(self._bytes, 4)
        elif c == 0x6b:
            self._push(self._slotdata)
            self._push(self._bytes, 2)
        elif c == 0x6c:
            self._push(self._bytes, 2)
        elif c == 0x82:
            self._push(self._str16)
            self._push(self._str16)
            self._push(self._str16)
            self._push(self._str16)
            self._push(self._bytes, 10)
        elif c == 0x83:
            self._push(self._special_83, 4)
            self._push(self._bytes, 4)            
        elif c == 0x84:
            self._push(self._bytes, 23)
        elif c == 0xc8:
            self._push(self._bytes, 5)
        elif c == 0xc9:
            self._push(self._bytes, 3)
            self._push(self._str16)
        elif c == 0xca:
            self._push(self._bytes, 4)
        elif c == 0xfa:
            self._push(self._special_fa)
            self._push(self._str16)
        elif c == 0xfe:
            pass
        elif c == 0xff:
            self._push(self._str16)
        else:
            raise self.ProtocolError('invalid packet: %r' % c)
        return True
    

##  MCLogger
##
class MCLogger(MCParser):
    
    def __init__(self, fp, safemode=False):
        MCParser.__init__(self, safemode=safemode)
        self.fp = fp
        return

    def _write(self, s):
        line = time.strftime('%Y-%m-%d %H:%M:%S')+' '+s.encode('utf-8')
        self.fp.write(line+'\n')
        self.fp.flush()
        print line
        return


##  MCServerLogger
##
class MCServerLogger(MCLogger):

    INTERVAL = 60

    def __init__(self, fp, safemode=False,
                 chat_text=True, time_update=True,
                 player_pos=True, player_health=True,
                 map_chunk_path=None, map_dimension=None):
        MCLogger.__init__(self, fp, safemode=safemode)
        self.rec_chat_text = chat_text
        self.rec_time_update = time_update
        self.rec_player_pos = player_pos
        self.rec_player_health = player_health
        self.map_chunk_path = map_chunk_path
        self.map_dimension = map_dimension
        self._dim = None
        self._h = -1
        return
    
    def _server_info(self, wtype, mode, dim, diff, height):
        self._write(' ### server info: wtype=%r, mode=%d, dim=%d, diff=%d, height=%d' %
                    (wtype, mode, dim, diff, height))
        self._dim = dim
        return

    def _chat_text(self, s):
        if not self.rec_chat_text: return
        s = re.sub(ur'\xa7.', '', s)
        self._write(s)
        return

    def _time_update(self, t):
        if not self.rec_time_update: return
        (d,x) = divmod(t, 24000)
        h = x/1000
        if self._h != h:
            self._h = h
            self._write(' === day %d, %d:00' % (d, (h+8)%24))
        return

    def _player_pos(self, x, y, z):
        if not self.rec_player_pos: return
        p = (int(x), int(y), int(z))
        self._write(' *** (%d, %d, %d)' % p)
        return
    
    def _player_health(self, hp, food, sat):
        if not self.rec_player_health: return
        self._write(' +++ hp=%d, food=%d, sat=%.1f' % (hp, food, sat))
        return

    def _map_chunk(self, (x,z,g,b1,b2), nbytes):
        #self._write(' ... chunk (%d,%d), g=%d, b1=0x%x, b2=0x%x' % (x,z,g,b1,b2))
        self._chunk_key = '%d.%d' % (x>>9, z>>9)
        self._chunk_info = pack('>iibHH', x,z,g,b1,b2)
        self._chunk_data = ''
        if (self.map_chunk_path is not None and
            (self.map_dimension is not None and self.map_dimension == self._dim)):
            self._push(self._map_chunk_2, nbytes)
        else:
            self._push(self._bytes, nbytes)
        return
    
    def _map_chunk_2(self, c, arg):
        arg[0] -= 1
        self._chunk_data += c
        if arg[0] == 0:
            name = 'r.%s.maplog' % self._chunk_key
            path = os.path.join(self.map_chunk_path, name)
            fp = file(path, 'ab')
            fp.write(self._chunk_info)
            fp.write(pack('>i', len(self._chunk_data)))
            fp.write(self._chunk_data)
            fp.close()
            self._pop()
        return True
    

##  MCClientLogger
##
class MCClientLogger(MCLogger):

    INTERVAL = 60

    def __init__(self, fp, safemode=False,
                 chat_text=True, player_pos=True):
        MCLogger.__init__(self, fp, safemode=safemode)
        self.rec_chat_text = chat_text
        self.rec_player_pos = player_pos
        self._t = -1
        self._p = None
        return

    def _chat_text(self, s):
        if not self.rec_chat_text: return
        s = re.sub(ur'\xa7.', '', s)
        self._write('>> '+s)
        return

    def _player_pos(self, x, y, z):
        if not self.rec_player_pos: return
        t = int(time.time())
        p = (int(x), int(y), int(z))
        if t < self._t and (self._p is not None and dist(p, self._p) < 50): return
        self._t = t + self.INTERVAL
        self._p = p
        self._write(' *** (%d, %d, %d)' % p)
        return


##  Client
##
class Client(asyncore.dispatcher):

    BUFSIZE = 4906

    def __init__(self, proxy):
        self.proxy = proxy
        self.sendbuffer = ""
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        return

    def handle_connect(self):
        self.proxy.remote_connected()
        return

    def handle_close(self):
        self.proxy.remote_closed()
        self.close()
        return

    def handle_read(self):
        self.proxy.remote_read(self.recv(self.BUFSIZE))
        return

    def remote_write(self, data):
        self.sendbuffer += data
        return

    def writable(self):
        return 0 < len(self.sendbuffer)

    def handle_write(self):
        n = self.send(self.sendbuffer)
        self.sendbuffer = self.sendbuffer[n:]
        return


##  Proxy
##
class Proxy(asyncore.dispatcher):

    local2remotefp = None
    remote2localfp = None
    BUFSIZE = 4096

    def __init__(self, sock, session,
                 plocal2remote, premote2local, delay=0):
        self.plocal2remote = plocal2remote
        self.premote2local = premote2local
        self.session = session
        self.delay = delay
        self._sendbuffer = ''
        self._sent_local2remote = 0
        self._sent_remote2local = 0
        self._client = None
        self.disp("BEGIN")
        asyncore.dispatcher.__init__(self, sock)
        return

    # overridable methods
    def local2remote(self, s):
        for proc in self.plocal2remote:
            proc.feed(s)
        if self.delay:
            time.sleep(self.delay*.001)
        return s
    def remote2local(self, s):
        for proc in self.premote2local:
            proc.feed(s)
        if self.delay:
            time.sleep(self.delay*.001)
        return s

    def connect_remote(self, addr):
        assert not self._client, "already connected"
        self.addr = addr
        self.disp("(connecting to %s:%d)" % self.addr)
        self._client = Client(self)
        self._client.connect(addr)
        return

    def disconnect_remote(self):
        assert self._client, "not connected"
        self._client.close()
        self._client = None
        return

    def disp(self, s):
        print >>sys.stderr, "SESSION %s:" % self.session, s
        return

    def remote_connected(self):
        self.disp("(connected to remote %s:%d)" % self.addr)
        return

    def remote_closed(self):
        self.disp("(closed by remote %s:%d)" % self.addr)
        self._client = None
        if not self._sendbuffer:
            self.handle_close()
        return

    def remote_read(self, data):
        if data:
            if self.remote2localfp is not None:
                self.remote2localfp.write(data)
            self._sent_remote2local += len(data)
            data = self.remote2local(data)
            if data:
                self._sendbuffer += data
        return

    def handle_read(self):
        data = self.recv(self.BUFSIZE)
        if data:
            data = self.local2remote(data)
            self._sent_local2remote += len(data)
            if self.local2remotefp is not None:
                self.local2remotefp.write(data)
            if data and self._client is not None:
                self._client.remote_write(data)
        return

    def writable(self):
        return 0 < len(self._sendbuffer)

    def handle_write(self):
        n = self.send(self._sendbuffer)
        self._sendbuffer = self._sendbuffer[n:]
        if not self._sendbuffer and self._client is None:
            self.handle_close()
        return

    def handle_close(self):
        if self._client is not None:
            self.disp("(closed by local)")
            self.disconnect_remote()
        self.close()
        self.disp('sent: local2remote: %r, remote2local: %r' %
                  (self._sent_local2remote, self._sent_remote2local))
        self.disp("END")
        return


##  Server
##
class Server(asyncore.dispatcher):

    def __init__(self, port, destaddr, bindaddr="127.0.0.1", delay=0):
        asyncore.dispatcher.__init__(self)
        self.destaddr = destaddr
        self.delay = delay
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((bindaddr, port))
        self.listen(1)
        self.session = 0
        print >>sys.stderr, "Listening: %s:%d" % (bindaddr, port)
        return

    def handle_accept(self):
        (conn, (addr,port)) = self.accept()
        print >>sys.stderr, "Accepted:", addr
        (clientloggers, serverloggers) = self.create_proxy(conn, self.session)
        proxy = Proxy(conn, self.session, clientloggers, serverloggers, delay=self.delay)
        proxy.connect_remote(self.destaddr)
        self.session += 1
        return

    def create_proxy(self, conn, session):
        return ([], [])


##  MCProxyServer
##
class MCProxyServer(Server):
    
    def __init__(self, port, destaddr, output, bindaddr="127.0.0.1", delay=0,
                 safemode=True,
                 chat_text=True, time_update=True,
                 player_pos=True, player_health=True,
                 map_chunk_path=None, map_dimension=None):
        Server.__init__(self, port, destaddr, bindaddr=bindaddr, delay=delay)
        self.output = output
        self.safemode = safemode
        self.chat_text = chat_text
        self.time_update = time_update
        self.player_pos = player_pos
        self.player_health = player_health
        self.map_chunk_path = map_chunk_path
        self.map_dimension = map_dimension
        return

    def create_proxy(self, conn, session):
        path = time.strftime(self.output)
        fp = file(path, 'a')
        print >>sys.stderr, "output:", path
        serverlogger = MCServerLogger(fp, safemode=self.safemode,
                                      chat_text=self.chat_text,
                                      time_update=self.time_update,
                                      player_pos=self.player_pos,
                                      player_health=self.player_health,
                                      map_chunk_path=self.map_chunk_path,
                                      map_dimension=self.map_dimension)
        clientlogger = MCClientLogger(fp, safemode=self.safemode,
                                      chat_text=self.chat_text,
                                      player_pos=self.player_pos)
        return ([clientlogger], [serverlogger])
    
    
# main
def main(argv):
    import getopt
    def usage():
        print 'usage: %s [-d] [-o output] [-p port] [-t testfile] [-U] [-M path] [-L delay] hostname:port' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'do:b:p:t:UM:S:D:L:')
    except getopt.GetoptError:
        return usage()
    debug = 0
    output = 'mclog-%Y%m%d.txt'
    bindaddr = '127.0.0.1'
    listen = 25565
    testfile = None
    safemode = True
    map_chunk_path = None
    map_dimension = None
    delay = 0
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-o': output = v
        elif k == '-b': bindaddr = v
        elif k == '-p': listen = int(v)
        elif k == '-t': testfile = file(v, 'rb')
        elif k == '-U': safemode = False
        elif k == '-M': map_chunk_path = v
        elif k == '-D': map_dimension = int(v)
        elif k == '-L': delay = int(v)
    if testfile is not None:
        MCParser.debugfp = sys.stderr
        parser = MCServerLogger(sys.stdout)
        #parser = MCClientLogger(sys.stdout)
        while 1:
            data = testfile.read(4096)
            if not data: break
            parser.feed(data)
        testfile.close()
        return
    if not args: return usage()
    if map_chunk_path is not None:
        try:
            os.makedirs(map_chunk_path)
        except OSError:
            pass
    x = args.pop(0)
    if ':' in x:
        (hostname,port) = x.split(':')
        port = int(port)
    else:
        hostname = x
        port = 25565
    if debug:
        MCParser.debugfp = file('parser.log', 'w')
        Proxy.local2remotefp = file('client.log', 'wb')
        Proxy.remote2localfp = file('server.log', 'wb')
    MCProxyServer(listen, (hostname, port), output, delay=delay,
                  bindaddr=bindaddr, safemode=safemode,
                  map_chunk_path=map_chunk_path,
                  map_dimension=map_dimension)
    asyncore.loop()
    return

if __name__ == '__main__': sys.exit(main(sys.argv))
