#!/usr/bin/env python
##
##  map html generator (for pigmap)
##
##  coords.txt file format:
##    # for comment
##    Type:Location:Name: (x,y,z)
##

import sys, os, re, time, stat, fileinput

ENTRY = re.compile(r'^([^:]*):([^:]*):([^:]*):(.*)')
COORDS = re.compile(r'[-\d]+')
TITLE = re.compile(r'\s+portal\s*$', flags=re.I)
NAME = re.compile(r'[^-_a-z0-9]', flags=re.I)
def get_entry(line):
    m = ENTRY.match(line)
    if not m: raise ValueError(line)
    (t, loc, title, xyz) = m.groups()
    title = TITLE.sub('', title)
    name = NAME.sub('', title)
    f = [ int(m.group(0)) for m in COORDS.finditer(xyz) ]
    if len(f) == 3:
        (x,y,z) = f
    elif len(f) == 2:
        (x,z) = f
        y = 64
    else:
        raise ValueError(line)
    return (t+'_'+name, loc, title, (x,y,z))

def read_entries(fp):
    for line in fp:
        try:
            line = line[:line.index('#')]
        except ValueError:
            pass
        line = line.strip()
        if not line: continue
        yield get_entry(line)
    return

def read_params(params, fp):
    for line in fp:
        line = line.strip()
        try:
            i = line.index(' ')
        except ValueError:
            continue
        (k,v) = (line[:i], line[i+1:])
        params[k] = v
    return params

ENTRIES = re.compile(r'@@ENTRIES@@')
MARKERS = re.compile(r'@@MARKERS:([^@]+)@@')
PARAM = re.compile(r'@@PARAM:([^@]+)@@')
def main(argv):
    import getopt
    def usage():
        print 'usage: %s [-C] [-i src.html] [-b pigmap.params] [-p key=value] coords.txt ...' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'Ci:b:p:')
    except getopt.GetoptError:
        return usage()
    add_commap = False
    src_html = 'src.html'
    pigmap_params = 'pigmap.params'
    params = {
        'date': time.strftime('%Y-%m-%d GMT'),
        }
    for (k, v) in opts:
        if k == '-C': add_commap = True
        elif k == '-i': src_html = v
        elif k == '-b': pigmap_params = v
        elif k == '-p':
            (k,v) = v.split('=')
            params[k] = v
    #
    entries = sorted(read_entries(fileinput.input(args)))
    #
    fp = file(pigmap_params)
    read_params(params, fp)
    fp.close()
    mtime = os.stat(pigmap_params)[stat.ST_MTIME]
    params['lastUpdated'] = time.strftime('%Y-%m-%d GMT', time.gmtime(mtime))
    #
    out = sys.stdout
    fp = file(src_html)
    for line in fp:
        m = ENTRIES.search(line)
        if m:
            for (name,loc,title,(x,y,z)) in entries:
                out.write(' { name:"%s", loc:"%s", title:"%s", x:%s, y:%s, z:%s },\n' % (name,loc,title,x,y,z))
            continue
        m = MARKERS.search(line)
        if m:
            t0 = m.group(1)
            for (name,loc,title,_) in entries:
                if name[0] != t0: continue
                out.write('<div>')
                out.write('<a href="javascript:void(0);" onclick="gotoLocationByName(%r);">%s</a>' % (name, title))
                if add_commap:
                    out.write(' <small>(<a href="./map/%s/index.html#name=%s" target="%s">map</a>)</small>' % (name, name, name))
                if loc:
                    out.write(' <small>(%s)</small>' % (loc))
                out.write('</div>\n')
            continue
        out.write(PARAM.sub(lambda m: params[m.group(1)], line))
    fp.close()
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
