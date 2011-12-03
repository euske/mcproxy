#!/usr/bin/env python
# map chunk merger (for pigmap)

import sys, zlib, array, os.path
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


##  RegionFile
##
class RegionFile(object):

    class Chunk(object):
        
        def __init__(self):
            n = 16*128*16
            self._blockids = array.array('c', '\x00'*n)
            self._blockdata = array.array('b', [0]*n)
            self._skylight = array.array('b', [0]*n)
            self._blocklight = array.array('b', [0]*n)
            return

        def put(self, x0, y0, z0, sx, sy, sz, data):
            n = sx*sy*sz
            assert len(data) == int(n*2.5), (len(data), sx,sy,sz)
            blockids = data[:n]
            nibs = unpack4(data[n:])
            blockdata = nibs[:n]
            skylight = nibs[n:n*2]
            blocklight = nibs[n*2:]
            assert len(blockids) == len(blockdata) == len(skylight) == len(blocklight)
            assert 0 <= x0 and x0+sx <= 16
            assert 0 <= y0 and y0+sy <= 128
            assert 0 <= z0 and z0+sz <= 16
            if x0 == y0 == z0 == 0 and sx == sz == 16 and sy == 128:
                self._blockids = array.array('c', blockids)
                self._blockdata = array.array('b', blockdata)
                self._skylight = array.array('b', skylight)
                self._blocklight= array.array('b', blocklight)
            else:
                j = 0
                for x in xrange(x0, x0+sx):
                    i0 = x*16*128
                    for z in xrange(z0, z0+sz):
                        i1 = i0+z*128
                        for y in xrange(y0, y0+sy):
                            self._blockids[i1+y] = blockids[j]
                            self._blockdata[i1+y] = blockdata[j]
                            self._skylight[i1+y] = skylight[j]
                            self._blocklight[i1+y] = blocklight[j]
                            j += 1
            return

        def write(self, fp):
            buf = StringIO()
            buf.write(pack('>bh', 10, 5)+'Level') # compound 'Level'
            blockids = self._blockids.tostring()
            buf.write(pack('>bh', 7, 6)+'Blocks'+pack('>i', len(blockids)))
            buf.write(blockids)
            blockdata = pack4(self._blockdata)
            buf.write(pack('>bh', 7, 4)+'Data'+pack('>i', len(blockdata)))
            buf.write(blockdata)
            skylight = pack4(self._skylight)
            buf.write(pack('>bh', 7, 8)+'SkyLight'+pack('>i', len(skylight)))
            buf.write(skylight)
            blocklight = pack4(self._blocklight)
            buf.write(pack('>bh', 7, 10)+'BlockLight'+pack('>i', len(blocklight)))
            buf.write(blocklight)
            buf.write('\x00') # compound end
            data = zlib.compress(buf.getvalue())
            fp.write(pack('>ib', len(data)+1, 2))
            fp.write(data)
            return len(data)+5
    
    def __init__(self):
        self._chunks = {}
        return
    
    def loadext(self, fp):
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
                chunk = self.Chunk()
                self._chunks[(cx,cy,cz)] = chunk
            chunk.put(x&15,y&127,z&15, sx,sy,sz, data)
            sys.stderr.write('.'); sys.stderr.flush()
        return

    def write(self, fp):
        headerpos = fp.tell()
        fp.seek(8192, 1)
        offsets = [ (0,0) for _ in xrange(1024) ]
        sector = 2
        for ((cx,cy,cz),chunk) in self._chunks.iteritems():
            i = ((cx % 32) + 32*(cz % 32))
            size = chunk.write(fp)
            xsize = (size+4095)/4096*4096
            fp.write('\x00' * (xsize-size)) # padding
            offsets[i] = (sector, xsize/4096)
            sector += xsize/4096
        fp.seek(headerpos)
        for (sector, size) in offsets:
            fp.write(pack('>ib', sector, size)[1:])
        return
    
def main(argv):
    import getopt
    def usage():
        print 'usage: %s [-o outdir] [file ...]' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'o:')
    except getopt.GetoptError:
        return usage()
    outdir = './region'
    for (k, v) in opts:
        if k == '-o': outdir = v
    for extpath in args:
        print >>sys.stderr, 'reading: %r' % extpath,
        rgn = RegionFile()
        fp = open(extpath, 'rb')
        rgn.loadext(fp)
        fp.close()
        name = os.path.basename(extpath).replace('.ext', '')
        outpath = os.path.join(outdir, name+'.mcr')
        print >>sys.stderr, 'writing: %r' % outpath
        outfp = open(outpath, 'wb')
        rgn.write(outfp)
        outfp.close()
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
