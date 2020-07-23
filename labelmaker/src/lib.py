#TODO switch to structs

#####
points_to_mm = 0.3528
mm_to_points = 1/points_to_mm
#####

from pprint import pprint, pformat
import pudb
import logging
#https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python
logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger()

#####
import inspect, os
def subst(s):
  # https://stackoverflow.com/questions/50499/how-do-i-get-the-path-and-name-of-the-file-that-is-currently-executing
  selfd = (os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))) # script directory
  proot = os.path.abspath(selfd + "/..")
  res = s.format(selfd=selfd, proot=proot)
  logging.debug((s, res))
  return res

class Constants:
  sql_sheetUsage = subst("{selfd}/sql/sheet-usage.sql")
  sql_sheetSpecs = subst("{selfd}/sql/labelsheet-specs.sql")
  _dbPath = subst("{proot}/tmp/db.sqlite")
  histfile = subst("{proot}/tmp/console.hist")

#####

import sqlite3
import contextlib

@contextlib.contextmanager
def connect(*args, **kwargs):
  with sqlite3.connect(*args, **kwargs) as conn:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = 1")
    yield conn

def sqlErrHandler(expr, f, raise_exc=True): #TODO just use sqlalchemy?
  try:
    return f()
  except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
    print("error in: %s" % expr)
    if raise_exc:
      raise e
    else:
      print("sql error: %s" % e)

def init(dbPath=Constants._dbPath):
  with connect(dbPath) as conn:
    for path in [ Constants.sql_sheetUsage, Constants.sql_sheetSpecs ]:
      expr = open(path, "rb").read().decode("utf-8")
      sqlErrHandler(expr, lambda: conn.executescript(expr))
  return dbPath

def parse_row(dbPath, table, cols, str, field_override={}):
  from collections import OrderedDict

  with connect(dbPath) as conn:
    integer = p.regex("[0-9]+")
    float = p.regex("[0-9]+(\\.[0-9]+){0,1}")
    text = None #TODO

    expr = "select name, type from pragma_table_info(:table)" #select * from pragma_table_info('pragma_table_info')
    parser_lut = {"FLOAT" : float, "INTEGER" : integer, "TEXT" : text }

    type_lut = dict(sqlErrHandler(str, lambda: conn.execute(expr, {"table":table}).fetchall()))
    logging.debug(type_lut)
    parsedict = OrderedDict()
    for i,k in enumerate(cols):
      if k in field_override:
        parsedict[k] = field_override[k]
      else:
        parsedict[k] = (p.whitespace if i != 0 else p.success(None)) >> parser_lut[type_lut[k]]
    #logging.debug(pformat(parsedict)) #TODO parser objects dont name themselves legibly
    parser = p.seq(**parsedict) << p.eof
    return parse_err2Obj(parser, str)

#####
def get_last_sheetid(dbPath_or_conn): #TODO halfassed
  try:#TODO
    with connect(dbPath_or_conn) as conn:
      val = (conn.execute("select last_sheetid from promptstate").fetchone()) # TODO assert / single
  except: #TODO
      val = (dbPath_or_conn.execute("select last_sheetid from promptstate").fetchone()) # TODO assert / single
  return val["last_sheetid"] if val else None

def get_spec_from_id(dbPath, id):
  from collections import namedtuple
  objectify = lambda d: namedtuple('Struct', d.keys())(*d.values()) # https://stackoverflow.com/questions/1305532/convert-nested-python-dict-to-object/9413295#9413295

  expr = "select * from sheetspecs join sheettype on sheetspecs.name = sheettype.type where sheettype.id = :sid" 
#  logging.debug(expr)
  with connect(dbPath) as conn:
    res = sqlErrHandler(expr, lambda: conn.execute(expr, {"sid" : id}))
  res2 = objectify(dict(res.fetchone())) #TODO does this work
  return objectify({ # convert to object that takes row from this table as argument (ORM? >_>)
    "sheet": objectify({"w": res2.sheet_width, "h":res2.sheet_height}),
    "grid": objectify({"w": res2.columns, "h": res2.rows}),
    "label": objectify({"w": res2.label_width, "h": res2.label_height}),
    "margin": objectify({"l": res2.left_margin, "t": res2.top_margin})
    })

def get_sheet_used_indexes(dbPath, sheet_id):
  with connect(dbPath) as conn:
    expr = "select used_idx from sheetusage where id = :id"
    res = sqlErrHandler(expr, lambda: conn.execute(expr, {"id" : sheet_id}))
  return [ x["used_idx"] for x in res.fetchall()]

#####
import parsy as p
import cmd
import readline
import re

def print_parse_err(err, arg, doc):
  print("Error: %s\nin %s\nhere%s\nExpected format is %s" % (str(err), repr(arg), " "*int(err.line_info().split(":")[1]) + "^", doc)) #TODO

def parse_err2Obj(parser, arg):
  res, err = None, None
  try:
    res = parser.parse(arg)
  except p.ParseError as e:
    err = e
  return (res, err)

class REPL(cmd.Cmd):
  def __init__(self, dbPath):
    self.dbPath = dbPath
    self.histfile = Constants.histfile

    self.state = { "last_sheetid" : None, "last_docid" : None } #TODO add printer

    with connect(self.dbPath) as conn:
      self.update_prompt_data(conn) #TODO
    self.update_next_prompt()
    super().__init__()

  def preloop(self):
    if readline and os.path.exists(self.histfile):
      readline.set_history_length(-1)
      readline.read_history_file(self.histfile)

  def precmd(self, arg):
    if readline:
      try:
        open(self.histfile, "x")
      except FileExistsError:
        pass
      readline.append_history_file(1, self.histfile)
    return arg

  def postcmd(self, stop, line):
    self.update_next_prompt()

    #TODO if stop is not bool, pprint and return appropriate stop flag
    if stop == None:
      return False
    elif stop != True:
      pprint(stop)
    else:
      return True

  def update_prompt_data(self, conn):
    #TODO wrap, make nice , etc, like the do_ functions
    #sid = (conn.execute("SELECT last_insert_rowid()").fetchall())
    sid = get_last_sheetid(conn)
    self.state["last_sheetid"] = sid if sid else None

  def update_next_prompt(self):
    self.prompt =  "(%s) " % ("sheet %s" % self.state["last_sheetid"])

  #TODO unit tests
  def do_add_type(self, arg): #TODO generated docstring?
    # first w then h
    cols = """
      name,
      label_width, label_height,
      columns, rows,
      sheet_width, sheet_height,
      left_margin, top_margin,
      column_gap, row_gap
      """
    doc = """
      insert into sheetspecs (%s)
      """ % cols

    ident_re = "[a-zA-Z_][a-zA-Z_0-9]*"
    ident = p.regex(ident_re)
    col_idents = re.findall(ident_re, cols)

    validated, err = parse_row(self.dbPath, "sheetspecs", col_idents, arg, field_override={"name" : ident})
    if validated:
      with connect(self.dbPath) as conn:
        param_substitution_names = re.sub("(^| )([a-zA-Z])", " :\\2", cols) #todo use named fields
        expr = " insert into %s (%s) values (%s)" % ("sheetspecs", cols, param_substitution_names) #TODO insecure?
        logging.debug(pformat((expr, validated)))
        sqlErrHandler(expr, lambda: conn.execute(expr, validated), raise_exc=False)
    else:
      print_parse_err(err, arg, doc)

  def do_add_sheet(self, arg):
    cols = "type"
    doc = """
      insert into sheettype (%s)
      """ % cols

    ident_re = "[a-zA-Z_][a-zA-Z_0-9]*"
    ident = p.regex(ident_re)
    col_idents = re.findall(ident_re, cols)

    validated, err = parse_row(self.dbPath, "sheettype", col_idents, arg, field_override={"type" : ident})
    if validated:
      with connect(self.dbPath) as conn:
        param_substitution_names = re.sub("(^| )([a-zA-Z])", " :\\2", cols)
        expr = " insert into %s (%s) values (%s)" % ("sheettype", cols, param_substitution_names) #TODO insecure?
        logging.debug(pformat((expr, validated)))
        sqlErrHandler(expr, lambda: conn.execute(expr, validated), raise_exc=False)

        #TODO
        sid = conn.execute("SELECT last_insert_rowid()").fetchall()[0][0]
        conn.execute("insert into promptstate (prompt_session, last_sheetid) values (1, :sid) on conflict(prompt_session) do update set last_sheetid=(select last_insert_rowid())", {"sid" : sid})
        self.update_prompt_data(conn) #TODO

      if(True): #TODO what if no space?
        print("printing sheet %s bar code..." % sid)
        self.print_sheet_metadata(sid)
    else:
      print_parse_err(err, arg, doc) #todo doc



  # add the sheet idk code
  # TODO add multiple possible id placements
  def print_sheet_metadata(self, sheet_id, printer=None, disabled=None, force_mode=None, dry_run=False):
    #TODO: what if no margin? -> use first label #TODO add to spec
    #force_mode: margin | first
    def add_this_side_up(): #TODO figure out a good way to do this. this is printer dependent and needs user checking? or is my printer just misconfigured
      # multiple possible protocols for thiss
      # - print test dot, ask user, print direction label
      pass

    def add_page_id(sheet, spec, id):
      #TODO note this is in millimeters and needs to be converted to points, and the dmtx needs a dpm (dots per millimeter or something) set / size conversion
      #TODO get margin from db too
      #TODO everything is all messed up here, might be related to the group operation order later
      def calc_code_placement(spec, dmtx_w, dmtx_h): #TODO #dmtx must be prerotated  #TODO figure out how tf to do this sanely
        #TODO need print margin
        margin_w_padding_outer = 3.0/4 * 5 # print margin #TODO
        margin_w_padding_inner = 0
        margin_w = ( (spec.sheet.w - (spec.grid.w * spec.label.w)) / 2 ) - margin_w_padding_outer

        y = (spec.sheet.h / 2) 
        #x = margin_w_padding_outer + dmtx_w / 2 #TODO wtf is this not in the right place??
        #x = dmtx_h / 2 #TODO wtf is this not in the right place??

        w = dmtx_h
        h = margin_w - margin_w_padding_inner #TODO, this is awkward because of the way x is calced right now  #will distort the widget, but this seems to work fine with dmtx #TODO make a max value / error for small value
        h = min(h, 15) # dont make a really big one unnecessarily, TODO the max should be a function of dots in the dmtx

        x = h / 2 + margin_w_padding_outer #TODO meh
        return (w, h), (x, y)

      dmtx_path, dmtx_size = call_dmtx("(sheet %s)" % id)
      size, coords = calc_code_placement(spec, *dmtx_size)
      logging.debug((size, coords))

      dtmx_img = Image(0, 0, *map(lambda x: x * mm_to_points, size), dmtx_path)
      gr = Group(dtmx_img)
      gr.translate(*map(lambda x: -x/2 * mm_to_points, size)) #center coord sys
      gr2 = Group(gr)
      gr2.rotate(90)
      gr3 = Group(gr2)
      gr3.translate(*map(lambda x: x * mm_to_points, coords))

      sheet._current_page.add(gr3)

    import labels
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Image, Group #cannibalized from sheet.py because I couldnt find docs

    def draw_label(label, width, height, obj):
      pass

    spec = get_spec_from_id(self.dbPath, sheet_id) #TODO structify
    spec2 = labels.Specification(*spec.sheet, *spec.grid, *spec.label, column_gap=0, row_gap=0) # TODO
    sheet = labels.Sheet(spec2, draw_label)
    sheet.add_labels([0]) #TODO noop
    add_page_id(sheet, spec, sheet_id)

    #TODO save file and print
    sheet.save(subst('{proot}/tmp/qr.pdf'))

    if not dry_run:
      print("{0:d} label(s) output on {1:d} page(s).".format(sheet.label_count, sheet.page_count))
      call_print(subst('{proot}/tmp/qr.pdf'))

  def do_print_labels(self, arg): #TODO assert count less than remaining while we dont have pagination #TODO factor into function and add dry run
    count = int(arg) #TODO

    sheet_id = get_last_sheetid(self.dbPath)
    mask = get_sheet_used_indexes(self.dbPath, sheet_id)
    spec = get_spec_from_id(self.dbPath, sheet_id) #TODO structify
    page_max = spec.grid.w * spec.grid.h
    free_count = page_max - len(mask) 
    free_idxs = set(range(0,page_max)).difference(set(mask))
    if free_count < count:
      print("pagination not implemented, not enough space on page. at most %s left on this page." % free)
      return

    import labels
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import String, Image, Group #cannibalized from sheet.py because I couldnt find docs

    idx_to_coord = lambda idx: (idx // spec.grid.w + 1, idx % spec.grid.w + 1)
    #coord_to_idx = lambda x, y: y*spec.grid.w+x

    def draw_label(label, width, height, obj):
      def calc_code_placement(spec, dmtx_w, dmtx_h): #TODO #dmtx must be prerotated  #TODO figure out how tf to do this sanely
        x = 0
        y = 0

        w = None # auto?
        h = None # auto?

        #*map(lambda x: x * mm_to_points, coords),
        #*map(lambda x: x * mm_to_points, size)

        return (w, h), (x, y)

      dmtx_path, dmtx_size = call_dmtx("(id %s)" % obj)
      size, coords = calc_code_placement(spec, *dmtx_size)

      dtmx_img = Image(*coords, width / 2, height * 3/4 * 0.95, dmtx_path)
      label.add(dtmx_img)
      label.add(String(width * 0.99, height * 0.99, ".", fontName="Helvetica", fontSize=5))
      label.add(String(0.5, height * 0.99, ".", fontName="Helvetica", fontSize=5))
      label.add(String(width * 0.99, 0.5, ".", fontName="Helvetica", fontSize=5))
      label.add(String(0.5,height - height * 1/4, ".%s-" % obj, fontName="Helvetica", fontSize=16))

    #spec2 = labels.Specification(*spec.sheet, *spec.grid, *spec.label, column_gap=0, row_gap=0, left_margin=spec.margin.l, top_margin=spec.margin.t) # TODO
    spec2 = labels.Specification(*spec.sheet, *spec.grid, *spec.label, column_gap=0, row_gap=0) # TODO
    sheet = labels.Sheet(spec2, draw_label)
    used_labels = map(idx_to_coord, mask)
    sheet.partial_page(1, used_labels)

    with connect(self.dbPath) as conn:
      expr = "insert into labels default values;"
      for i in range(0, count):
        sqlErrHandler(expr, lambda: conn.execute(expr))

      res = reversed([list(x) for x in conn.execute("select id from labels order by id desc limit %s" % count).fetchall()]) # TODO
      label_ids = sum(res, [])
      print(label_ids)
      sheet.add_labels(label_ids) #TODO

      # Save the file and we are done.
      sheet.save(subst('{proot}/tmp/qr.pdf'))
      print("{0:d} label(s) output on {1:d} page(s).".format(sheet.label_count, sheet.page_count))

      dry_run = False    #TODO 
      #dry_run = True    #TODO 
      if not dry_run:
        expr = "insert into sheetusage (id, used_idx) values (?, ?)" #TODO
        vals = [(sheet_id, x) for x in sorted(free_idxs)[:count]]
        try:
          sqlErrHandler(expr, lambda: conn.executemany(expr, vals))
        except Exception as e: #TODO
          print(vals)
          print(mask)
          print("error adding used indexes, aborting.")
          print(e)
          return

        print("{0:d} label(s) output on {1:d} page(s).".format(sheet.label_count, sheet.page_count))
        call_print(subst('{proot}/tmp/qr.pdf'))

  #TODO composite key based integrity see q chat logs
  #TODO do_add_free - basically when your shit is inconsitent because you printed upside down or something
  def do_add_used(self, arg):
    #raise NotImplementedError
    cols = "id, used_idx"
    doc = """
      insert into sheettype (%s)
      """ % cols

    ident_re = "[a-zA-Z_][a-zA-Z_0-9]*"
    ident = p.regex(ident_re)
    col_idents = re.findall(ident_re, cols)

    validated, err = parse_row(self.dbPath, "sheetusage", col_idents, arg)
    if validated:
      with connect(self.dbPath) as conn:
        param_substitution_names = re.sub("(^| )([a-zA-Z])", " :\\2", cols)
        expr = " insert into %s (%s) values (%s)" % ("sheetusage", cols, param_substitution_names) # TODO insecure?
        logging.debug(pformat((expr, validated)))
        sqlErrHandler(expr, lambda: conn.execute(expr, validated), raise_exc=False)
    else:
      print_parse_err(err, arg, doc) #todo doc

  def do_set_sheet(self, arg):
    raise NotImplementedError

  def do_raw(self, arg):
    with connect(self.dbPath) as conn:
      return sqlErrHandler(arg, lambda: conn.execute(arg).fetchall(), raise_exc=False)

#####
def call_dmtx(code): #TODO detect errors
  import tempfile
  import subprocess
  path = tempfile.NamedTemporaryFile(prefix=subst("{proot}/tmp/dmtx")).name
  p = subprocess.Popen(("dmtxwrite -m 1 -d 1 -o %s -s 12x36" % path).split(), stdin=subprocess.PIPE) #TODO tempfile
  p.communicate(code.encode("ascii"))
  #TODO do something about this arbitrary scaling factor, 3pt per square for height
  size = (12 * 3 * points_to_mm, 12 * 12 * points_to_mm) # in points
  return (path, size)

def call_print(pdfpath): #TODO detect errors
  #TODO make a state variable
  import subprocess
  printer = "EPSON_L3050_Series"
  p = subprocess.Popen(("lpr -o PageSize=A4 -P %s %s" % (printer, pdfpath)).split(), stdin=subprocess.PIPE) #TODO tempfile #TODO settings fuckery

#####

def test():
  #dbPath = init(dbPath=":memory:") #TODO does passing dbpath instead of a file descriptor or something work?
  dbPath = init() #TODO does passing dbpath instead of a file descriptor or something work?
  REPL(dbPath).cmdloop()

test()
#init()

