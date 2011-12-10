#!/usr/bin/env python
##
##  map chunk merger (for pigmap)
##
##  mcproxy.py can optionally generate *.maplog files,
##  which can augment existing region files to produce pigmap outputs.
##
##  caution: data other than map chunks (ie. signs, mob stats, etc.) are not changed!
##
##  usage: python mergemap.py -o world/region world/region/r.*.mcr maplog/r.*.maplog
##

import sys, zlib, array, os, os.path, glob
from cStringIO import StringIO
from struct import pack, unpack


def pack4(data):
    r = ''
    for i in xrange(0, len(data), 2):
        b = (data[i] << 4) | data[i+1]
        r += chr(b)
    return r

def unpack4(data):
    r = []
    for c in data:
        b = ord(c)
        r.append(b >> 4)
        r.append(b & 15)
    return r


##  NBTObject
##
class NBTObject(object):
    def __init__(self, value):
        self.value = value
        return
    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.value)
    def pp(self, fp, indent=0):
        fp.write(' '*indent)
        fp.write('%s: %r\n' % (self.__class__.__name__, self.value))
        return 

class NBTByte(NBTObject):
    TAG = 1
    def tostring(self):
        return pack('>b', self.value)
    
class NBTShort(NBTObject):
    TAG = 2
    def tostring(self):
        return pack('>h', self.value)

class NBTInt(NBTObject):
    TAG = 3
    def tostring(self):
        return pack('>i', self.value)

class NBTLong(NBTObject):
    TAG = 4
    def tostring(self):
        return pack('>q', self.value)

class NBTFloat(NBTObject):
    TAG = 5
    def tostring(self):
        return pack('>f', self.value)

class NBTDouble(NBTObject):
    TAG = 6
    def tostring(self):
        return pack('>d', self.value)

class NBTByteArray(NBTObject):
    TAG = 7
    def tostring(self):
        return pack('>i', len(self.value))+self.value
    LIMIT = 20
    def pp(self, fp, indent=0):
        fp.write(' '*indent)
        if len(self.value) < self.LIMIT:
            fp.write('%s: %r\n' % (self.__class__.__name__, self.value))
        else:
            fp.write('%s: %r...\n' % (self.__class__.__name__, self.value[:self.LIMIT]))
        return 

class NBTString(NBTObject):
    TAG = 8
    def tostring(self):
        data = self.value.encode('utf-8')
        return pack('>h', len(data))+data

class NBTList(NBTObject):
    TAG = 9
    def __init__(self, value, tag):
        NBTObject.__init__(self, value)
        self.tag = tag
        return
    def tostring(self):
        data = ''.join( obj.tostring() for obj in self.value )
        return pack('>bi', self.tag, len(self.value))+data
    def pp(self, fp, indent=0):
        fp.write(' '*indent+'[\n')
        for obj in self.value:
            obj.pp(fp, indent=indent+1)
        fp.write(' '*indent+']\n')
        return 

class NBTCompound(NBTObject):
    TAG = 10
    def __init__(self, value):
        NBTObject.__init__(self, value)
        self.dict = dict(value)
        return
    def get(self, name):
        return self.dict.get(name)
    def tostring(self, root=False):
        data = ''
        for (name,obj) in self.value:
            name = name.encode('utf-8')
            data += pack('>bh', obj.TAG, len(name))+name+obj.tostring()
        if not root:
            data += '\x00'
        return data
    def pp(self, fp, indent=0):
        fp.write(' '*indent+'{\n')
        for (name,obj) in self.value:
            fp.write(' '*indent+' %r:\n' % name)
            obj.pp(fp, indent=indent+2)
        fp.write(' '*indent+'}\n')
        return 


##  NBTParser
##
class NBTParser(object):

    def __init__(self, data):
        self.data = data
        self.pos = 0
        return

    def get(self, n):
        v = self.data[self.pos:self.pos+n]
        self.pos += n
        return v
        
    def get_byte(self):
        return NBTByte(ord(self.get(1)))

    def get_short(self):
        (v,) = unpack('>h', self.get(2))
        return NBTShort(v)
        
    def get_int(self):
        (v,) = unpack('>i', self.get(4))
        return NBTInt(v)
        
    def get_long(self):
        (v,) = unpack('>q', self.get(8))
        return NBTLong(v)
        
    def get_float(self):
        (v,) = unpack('>f', self.get(4))
        return NBTFloat(v)
        
    def get_double(self):
        (v,) = unpack('>d', self.get(8))
        return NBTDouble(v)
        
    def get_byte_array(self):
        n = self.get_int()
        return NBTByteArray(self.get(n.value))
        
    def get_string(self):
        n = self.get_short()
        return NBTString(self.get(n.value).decode('utf-8'))

    def get_list(self):
        tag = self.get_byte().value
        n = self.get_int().value
        r = []
        for _ in xrange(n):
            r.append(self.get_value(tag))
        return NBTList(r, tag)

    def get_item(self):
        tag = self.get_byte().value
        if tag == 0: return (None, None)
        name = self.get_string().value
        value = self.get_value(tag)
        return (name, value)

    def get_compound(self):
        r = []
        while 1:
            (name, value) = self.get_item()
            if name is None: break
            r.append((name, value))
        return NBTCompound(r)

    def get_value(self, tag):
        if tag == NBTByte.TAG:  # TAG_Byte
            return self.get_byte()
        elif tag == NBTShort.TAG: # TAG_Short
            return self.get_short()
        elif tag == NBTInt.TAG: # TAG_Int
            return self.get_int()
        elif tag == NBTLong.TAG: # TAG_Long
            return self.get_long()
        elif tag == NBTFloat.TAG: # TAG_Float
            return self.get_float()
        elif tag == NBTDouble.TAG: # TAG_Double
            return self.get_double()
        elif tag == NBTByteArray.TAG: # TAG_Byte_Array
            return self.get_byte_array()
        elif tag == NBTString.TAG: # TAG_String
            return self.get_string()
        elif tag == NBTList.TAG: # TAG_List
            return self.get_list()
        elif tag == NBTCompound.TAG: # TAG_Compound
            return self.get_compound()
        else:                   # Other
            raise ValueError(tag)
        return

    def get_root(self):
        return NBTCompound([self.get_item()])
    

##  RegionFile
##
class RegionFile(object):

    class Chunk(object):
        
        def __init__(self, (cx,cy,cz), timestamp=0):
            n = 16*128*16
            self.key = (cx,cy,cz)
            self.timestamp = timestamp
            self._blockids = array.array('c', '\x00'*n)
            self._blockdata = array.array('b', [0]*n)
            self._skylight = array.array('b', [0]*n)
            self._blocklight = array.array('b', [0]*n)
            level = NBTCompound([
                    (u'Blocks', NBTByteArray('')),
                    (u'Data', NBTByteArray('')),
                    (u'SkyLight', NBTByteArray('')),
                    (u'BlockLight', NBTByteArray('')),
                    (u'xPos', NBTInt(cx)),
                    (u'zPos', NBTInt(cz)),
                    ])
            root = NBTCompound([(u'Level', level)])
            self._compound = NBTCompound([(u'', root)])
            return

        def __repr__(self):
            return '<Chunk %r>' % self.key

        def put(self, x0, y0, z0, sx, sy, sz, data):
            n = sx*sy*sz
            assert len(data) == int(n*2.5), (len(data), sx,sy,sz)
            blockids = data[:n]
            nibs = unpack4(data[n:])
            blockdata = nibs[:n]
            skylight = nibs[n:n*2]
            blocklight = nibs[n*2:]
            assert len(blockids) == len(blockdata) == len(skylight) == len(blocklight)
            if x0 == y0 == z0 == 0 and sx == sz == 16 and sy == 128:
                self._blockids[:] = array.array('c', blockids)
                self._blockdata[:] = array.array('b', blockdata)
                self._skylight[:] = array.array('b', skylight)
                self._blocklight[:] = array.array('b', blocklight)
            else:
                j = 0
                for x in xrange(x0, x0+sx):
                    if x < 0 or 16 <= x: continue
                    i0 = x*16*128
                    for z in xrange(z0, z0+sz):
                        if z < 0 or 16 <= z: continue
                        i1 = i0+z*128
                        for y in xrange(y0, y0+sy):
                            if y < 0 or 128 <= y: continue
                            self._blockids[i1+y] = blockids[j]
                            self._blockdata[i1+y] = blockdata[j]
                            self._skylight[i1+y] = skylight[j]
                            self._blocklight[i1+y] = blocklight[j]
                            j += 1
            return

        def load(self, fp):
            (nbytes,method) = unpack('>ib', fp.read(5))
            data = fp.read(nbytes)
            data = zlib.decompress(data)
            self._compound = NBTParser(data).get_root()
            root = self._compound.get(u'')
            level = root.get(u'Level')
            blockids = level.get(u'Blocks').value
            blockdata = unpack4(level.get(u'Data').value)
            skylight = unpack4(level.get(u'SkyLight').value)
            blocklight = unpack4(level.get(u'BlockLight').value)
            self._blockids[:] = array.array('c', blockids)
            self._blockdata[:] = array.array('b', blockdata)
            self._skylight[:] = array.array('b', skylight)
            self._blocklight[:] = array.array('b', blocklight)
            return

        def write(self, fp):
            root = self._compound.get(u'')
            level = root.get(u'Level')
            level.get(u'Blocks').value = self._blockids.tostring()
            level.get(u'Data').value = pack4(self._blockdata)
            level.get(u'SkyLight').value = pack4(self._skylight)
            level.get(u'BlockLight').value = pack4(self._blocklight)
            data = zlib.compress(self._compound.tostring(root=True))
            fp.write(pack('>ib', len(data)+1, 2))
            fp.write(data)
            return len(data)+5
    
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self._chunks = {}
        return

    def __repr__(self):
        return '<RegionFile %r,%r>' % (self.x, self.y)

    def load_mcr_header(self, fp):
        offsets = []
        for _ in xrange(1024):
            (sector,size) = unpack('>ib', '\x00'+fp.read(4))
            offsets.append((sector,size))
        timestamps = []
        for _ in xrange(1024):
            (timestamp,) = unpack('>i', fp.read(4))
            timestamps.append(timestamp)
        return zip(offsets, timestamps)

    def load_mcr(self, fp):
        for (i,((sector,size),timestamp)) in enumerate(self.load_mcr_header(fp)):
            if size == 0: continue
            (cz,cx) = divmod(i, 32)
            chunk = self.Chunk((cx,0,cz), timestamp)
            pos = sector * 4096
            fp.seek(pos)
            chunk.load(fp)
            sys.stderr.write('.'); sys.stderr.flush()
            self._chunks[chunk.key] = chunk
        sys.stderr.write('\n'); sys.stderr.flush()
        return
    
    def load_log(self, fp):
        while 1:
            buf = fp.read(28)
            if not buf: break
            (x,y,z,sx,sy,sz,nbytes) = unpack('>iiiiiii', buf)
            (sx,sy,sz) = (sx+1,sy+1,sz+1)
            data = fp.read(nbytes)
            data = zlib.decompress(data)
            (cx,cy,cz) = (x>>4,y>>7,z>>4)
            if (cx,cy,cz) in self._chunks:
                chunk = self._chunks[(cx,cy,cz)]
            else:
                chunk = self.Chunk((cx,cy,cz))
                self._chunks[chunk.key] = chunk
            chunk.put(x&15,y&127,z&15, sx,sy,sz, data)
            sys.stderr.write('.'); sys.stderr.flush()
        sys.stderr.write('\n'); sys.stderr.flush()
        return

    def write(self, fp):
        headerpos = fp.tell()
        fp.seek(8192, 1)
        offsets = [ (0,0) for _ in xrange(1024) ]
        timestamps = [0]*1024
        sector = 2
        for ((cx,cy,cz),chunk) in self._chunks.iteritems():
            i = 32*(cz % 32) + (cx % 32)
            size = chunk.write(fp)
            xsize = (size+4095)/4096*4096
            fp.write('\x00' * (xsize-size)) # padding
            offsets[i] = (sector, xsize/4096)
            timestamps[i] = chunk.timestamp
            sector += xsize/4096
            sys.stderr.write('.'); sys.stderr.flush()
        fp.seek(headerpos)
        for (sector, size) in offsets:
            fp.write(pack('>ib', sector, size)[1:])
        for timestamp in timestamps:
            fp.write(pack('>i', timestamp))
        sys.stderr.write('\n'); sys.stderr.flush()
        return
    
def main(argv):
    import getopt
    def usage():
        print 'usage: %s [-o outdir] [file ...]' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'fo:')
    except getopt.GetoptError:
        return usage()
    force = False
    outdir = './region'
    for (k, v) in opts:
        if k == '-f': force = True
        elif k == '-o': outdir = v
    names = set()
    mcrs = {}
    maplogs = {}
    for arg in args:
        for path in glob.glob(arg):
            (name,_) = os.path.splitext(os.path.basename(path))
            if path.endswith('.mcr'):
                if name not in mcrs: mcrs[name] = []
                mcrs[name].append(path)
                names.add(name)
            elif path.endswith('.maplog'):
                if name not in maplogs: maplogs[name] = []
                maplogs[name].append(path)
                names.add(name)
            else:
                print >>sys.stderr, 'unknown file format: %r' % path
    try:
        os.makedirs(outdir)
    except OSError:
        pass
    for name in sorted(names):
        outpath = os.path.join(outdir, name+'.mcr')
        if name not in maplogs and len(mcrs[name]) == 1 and os.path.isfile(outpath):
            # skip unchanged files.
            if not force: continue
        (_,x,y) = name.split('.')
        rgn = RegionFile(int(x), int(y))
        for path in mcrs.get(name, []):
            try:
                fp = open(path, 'rb')
                print >>sys.stderr, 'reading mcr: %r' % path
                rgn.load_mcr(fp)
                fp.close()
            except IOError:
                pass
        for path in maplogs.get(name, []):
            try:
                fp = open(path, 'rb')
                print >>sys.stderr, 'reading maplog: %r' % path
                rgn.load_log(fp)
                fp.close()
            except IOError:
                pass
        try:
            os.rename(outpath, outpath+'.old')
            print >>sys.stderr, 'rename old: %r' % outpath
        except OSError:
            pass
        print >>sys.stderr, 'writing: %r' % outpath
        outfp = open(outpath, 'wb')
        rgn.write(outfp)
        outfp.close()
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
