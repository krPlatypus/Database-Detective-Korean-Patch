import sys, struct

def read_pe_clr(data):
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    assert data[pe:pe+4] == b'PE\0\0'
    nsec = struct.unpack_from('<H', data, pe+6)[0]
    optsz = struct.unpack_from('<H', data, pe+20)[0]
    opt = pe+24
    magic = struct.unpack_from('<H', data, opt)[0]
    ddoff = opt + (96 if magic==0x10b else 112)
    sects = []
    so = opt+optsz
    for i in range(nsec):
        b = so+i*40
        name = data[b:b+8].rstrip(b'\0').decode()
        vsz, va, rsz, ra = struct.unpack_from('<IIII', data, b+8)
        sects.append((name, va, vsz, ra, rsz))
    def rva2off(rva):
        for name, va, vsz, ra, rsz in sects:
            if va <= rva < va+max(vsz,rsz):
                return ra + (rva-va)
        raise ValueError('bad rva %x' % rva)
    clr_rva = struct.unpack_from('<I', data, ddoff+14*8)[0]
    clr = rva2off(clr_rva)
    meta_rva, meta_sz = struct.unpack_from('<II', data, clr+8)
    return rva2off(meta_rva), meta_sz

def streams(data, mroot):
    assert data[mroot:mroot+4] == b'BSJB'
    vlen = struct.unpack_from('<I', data, mroot+12)[0]
    p = mroot+16+vlen
    p += 2  # flags
    nstreams = struct.unpack_from('<H', data, p)[0]; p += 2
    out = {}
    for _ in range(nstreams):
        off, size = struct.unpack_from('<II', data, p); p += 8
        e = data.index(b'\0', p)
        name = data[p:e].decode()
        p = e+1
        p = (p + 3) & ~3
        out[name] = (mroot+off, size)
    return out

def dump_us(path):
    data = open(path,'rb').read()
    mroot, _ = read_pe_clr(data)
    st = streams(data, mroot)
    if '#US' not in st:
        return []
    off, size = st['#US']
    res = []
    p = off+1
    end = off+size
    while p < end:
        b0 = data[p]
        if b0 == 0: p += 1; continue
        if b0 & 0x80 == 0:
            ln = b0; p += 1
        elif b0 & 0xC0 == 0x80:
            ln = ((b0 & 0x3f)<<8) | data[p+1]; p += 2
        else:
            ln = ((b0 & 0x1f)<<24)|(data[p+1]<<16)|(data[p+2]<<8)|data[p+3]; p += 4
        if ln == 0: continue
        raw = data[p:p+ln-1]
        p += ln
        try: s = raw.decode('utf-16-le')
        except: continue
        res.append(s)
    return res

if __name__ == '__main__':
    for s in dump_us(sys.argv[1]):
        print(repr(s))
