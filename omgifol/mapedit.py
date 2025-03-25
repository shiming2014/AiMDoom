from omg import util, lump
from omg.wad import NameGroup

Vertex = util.make_struct(
  "Vertex", """Represents a map vertex""",
  [["x", "h", 0],
   ["y", "h", 0]]
)

GLVertex = util.make_struct(
  "GLVertex", """Represents a map GL vertex""",
  [["x", "l", 0],
   ["y", "l", 0]]
)

Sidedef = util.make_struct(
  "Sidedef", """Represents a map sidedef""",
  [["off_x",  'h',  0  ],
   ["off_y",  'h',  0  ],
   ["tx_up",  '8s', "-"],
   ["tx_low", '8s', "-"],
   ["tx_mid", '8s', "-"],
   ["sector", 'h',  -1 ]]
)

Linedef = util.make_struct(
  "Linedef", """Represents a map linedef""",
  [["vx_a",   'h', -1],
   ["vx_b",   'h', -1],
   ["flags",  'h',  0],
   ["action", 'h',  0],
   ["tag",    'h',  0],
   ["front",  'h', -1],
   ["back",   'h', -1]],
  ["impassable", "block_monsters", "two_sided",
   "upper_unpeg", "lower_unpeg", "secret",
   "block_sound", "invisible", "automap"]
)

Thing = util.make_struct(
  "Thing", """Represents a map thing""",
  [["x",     'h', 0],
   ["y",     'h', 0],
   ["angle", 'h', 0],
   ["type",  'h', 0],
   ["flags", 'h', 0]],
  ["easy", "medium", "hard", "deaf", "multiplayer"]
)

Sector = util.make_struct(
  "Sector", """Represents a map sector""",
  [["z_floor",  'h',  0],
   ["z_ceil",   'h',  128],
   ["tx_floor", '8s', "FLOOR4_8"],
   ["tx_ceil",  '8s', "CEIL3_5"],
   ["light",    'h',  160],
   ["type",     'h',  0],
   ["tag",      'h',  0]]
)

Seg = util.make_struct(
  "Seg", """Represents a map seg""",
  [["vx_a",   'h', 0],
   ["vx_b",   'h', 0],
   ["angle",  'h', 0],
   ["line",   'h', 0],
   ["side",   'h', 0],
   ["offset", 'h', 0]]
)

SubSector = util.make_struct(
  "SubSector", """Represents a map subsector""",
  [["numsegs", 'h', 0],
   ["seg_a",   'H', 0]]
)

GLSeg = util.make_struct(
  "GLSeg", """Represents a map GL seg""",
  [["vx_a",    'h', 0],
   ["vx_b",    'h', 0],
   ["line",    'h', 0],
   ["side",    'h', 0],
   ["partner", 'h', 0]]
)

class MapEditor:
    """Doom map editor

    Data members:
        vertexes      List containing Vertex objects
        sidedefs      List containing Sidedef objects
        linedefs      List containing Linedef objects
        sectors       List containing Sector objects
        things        List containing Thing objects"""

    def __init__(self, from_lumps=None):
        """Create new, optionally from a lump.lump group"""
        if from_lumps is not None:
            self.from_lumps(from_lumps)
        else:
            self.vertexes = []
            self.sidedefs = []
            self.linedefs = []
            self.sectors  = []
            self.things   = []
            self.segs     = []
            self.ssectors = []

    def _unpack_lump(self, class_, data):
        s = class_._fmtsize
        return [class_(bytes=data[i:i+s]) for i in xrange(0,len(data),s)]

    def from_lumps(self, lumpgroup):
        """Load entries from a lump.lump group."""
        m = lumpgroup
        self.vertexes = self._unpack_lump(Vertex,    m["VERTEXES"].data)
        self.sidedefs = self._unpack_lump(Sidedef,   m["SIDEDEFS"].data)
        self.sectors  = self._unpack_lump(Sector,    m["SECTORS"].data)
        self.things   = self._unpack_lump(Thing,     m["THINGS"].data)
        self.linedefs = self._unpack_lump(Linedef,   m["LINEDEFS"].data)
        self.ssectors = self._unpack_lump(SubSector, m["SSECTORS"].data)
        self.segs     = self._unpack_lump(Seg,       m["SEGS"].data)
        self.blockmap = m["BLOCKMAP"]
        self.reject   = m["REJECT"]      # To be implemented
        self.nodes    = m["NODES"]

    def load_gl(self, mapobj):
        """Load GL nodes entries from a map"""
        vxdata = mapobj["GL_VERT"].data[4:]  # s[:4] == "gNd3" ?
        self.gl_vert  = self._unpack_lump(GLVertex,  vxdata)
        self.gl_segs  = self._unpack_lump(GLSeg,     mapobj["GL_SEGS"].data)
        self.gl_ssect = self._unpack_lump(SubSector, mapobj["GL_SSECT"].data)

    def to_lumps(self):
        m = NameGroup()
        m["_HEADER_"] = lump.Lump("")
        m["VERTEXES"] = lump.Lump("".join([x.pack() for x in self.vertexes]))
        m["THINGS"  ] = lump.Lump("".join([x.pack() for x in self.things  ]))
        m["LINEDEFS"] = lump.Lump("".join([x.pack() for x in self.linedefs]))
        m["SIDEDEFS"] = lump.Lump("".join([x.pack() for x in self.sidedefs]))
        m["SECTORS" ] = lump.Lump("".join([x.pack() for x in self.sectors ]))
        m["NODES"]    = self.nodes
        m["SEGS"]     = lump.Lump("".join([x.pack() for x in self.segs    ]))
        m["SSECTORS"] = lump.Lump("".join([x.pack() for x in self.ssectors]))
        m["BLOCKMAP"] = self.blockmap
        m["REJECT"]   = self.reject
        return m

    def draw_sector(self, vertexes, sector=None, sidedef=None):
        """Draw a polygon from a list of vertexes. The vertexes may be
        either Vertex objects or simple (x, y) tuples. A sector object
        and prototype sidedef may be provided."""
        assert len(vertexes) > 2
        firstv = len(self.vertexes)
        firsts = len(self.sidedefs)
        if sector  is None: sector  = Sector()
        if sidedef is None: sidedef = Sidedef()
        self.sectors.append(util.copy(sector))
        for i, v in enumerate(vertexes):
            if isinstance(v, tuple):
                x, y = v
            else:
                x, y = v.x, v.y
            self.vertexes.append(Vertex(x, y))
        for i in range(len(vertexes)):
            side = util.copy(sidedef)
            side.sector = len(self.sectors)-1
            self.sidedefs.append(side)
            self.linedefs.append(
              Linedef(vx_a=firstv+((i+1)%len(vertexes)),
              vx_b=firstv+i, front=firsts+i, flags=1))

    def paste(self, other, offset=(0,0)):
        """Insert content of another map."""
        vlen = len(self.vertexes)
        ilen = len(self.sidedefs)
        slen = len(self.sectors)
        for vx in other.vertexes:
            x, y = vx.x, vx.y
            self.vertexes.append(Vertex(x+offset[0], y+offset[1]))
        for line in other.linedefs:
            z = util.copy(line)
            z.vx_a += vlen
            z.vx_b += vlen
            if z.front != -1: z.front += ilen
            if z.back != -1: z.back += ilen
            self.linedefs.append(z)
        for side in other.sidedefs:
            z = util.copy(side)
            z.sector += slen
            self.sidedefs.append(z)
        for sector in other.sectors:
            z = util.copy(sector)
            self.sectors.append(z)
        for thing in other.things:
            z = util.copy(thing)
            z.x += offset[0]
            z.y += offset[1]
            self.things.append(z)

