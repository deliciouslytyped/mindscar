#TODO make ^C work

import sys, os
import subprocess

#import multiprocessing_logging as ml
#ml.install_mp_handler() # TODO wait this probably doesnt help me with anything


from collections import namedtuple

import cmd
import readline

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
  logger.debug((s, res))
  return res

class Constants:
  histfile = subst("{proot}/tmp/console.hist") #TODO

#####
import ctypes
rl_lib = ctypes.cdll.LoadLibrary(inspect.getfile(readline))
#####


import http.server as h
import urllib.parse as up
ScannedMessage = namedtuple("ScannedMessage", ["dm_data"]) #TODO scoping https://stackoverflow.com/questions/16377215/how-to-pickle-a-namedtuple-instance-correctly
class EvtServer:
  def run(queue):
    import logging.handlers
    logger = logging.Logger("EvtServer")
    qh = logging.handlers.QueueHandler(queue)
    qh.setLevel(logging.DEBUG)
    f = logging.Formatter(logging._STYLES["%"][1]) #from logging.basicconfig #TODO still looks dfferent from the other stuff
    qh.setFormatter(f)
    logger.addHandler(qh)

    class HRH(h.BaseHTTPRequestHandler):
      def log_message(self, format, *args):
        logger.debug("%s - - [%s] %s\n" %
          (self.address_string(),
          self.log_date_time_string(),
          format%args))

      def do_GET(self):
        self.send_response(200)
        self.end_headers()

        request = self.requestline.split()[1] #TODO crap parser
        parsed = up.urlparse(request)
        if parsed.path == "/dat":
          dm_data = up.parse_qs(parsed.query)["dm"][0] #TODO no idea why this is an array
          queue.put(ScannedMessage(dm_data))

    try:
      httpd = h.HTTPServer(("", 9999), HRH)
    except OSError: #TODO
      logger.error("port in use")
      queue.put("exit")

    httpd.serve_forever()

#TODO "EOF" is nterpreted as a special string?? https://github.com/python/cpython/blob/3.8/Lib/cmd.py
#TODO factor into lib
class REPLBase(cmd.Cmd):
  def __init__(self):
    self.histfile = Constants.histfile
    super().__init__()
    self.update_next_prompt()

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

  #TODO: kind of crappy, currently you ovrride update_next, (crappy part) and if you want to use update_current you call update_next first, to change self.prompt

  def update_next_prompt(self):
    pass

  def update_current_prompt(self):
    #update_by_newline = False #TODO
    #if update_by_newline:
    #  rl_lib.rl_reset_line_state()
    #  rl_lib.rl_crlf()
    rl_lib.rl_set_prompt(ctypes.c_char_p(self.prompt.encode("ascii"))) #TODO encoding??
    readline.redisplay()

  ##
FehState = namedtuple("FehState", ["pyproc", "killqueue", "thisdir"])

class REPL(REPLBase):
  def __init__(self, queue):
    self.state = { "docid": None, "workdir": None, "thumbs": None, "preview": None }
    super().__init__()

  def update_next_prompt(self):
    self.prompt =  "(%s) " % ("document id: %s" % self.state["docid"])

  def handle_new_dm_event(self, msg):
    def parse_dm_data(data): #TODO
      return data.replace("(","").replace(")","").split()
    if self.state["docid"]:
      thisdir = "D%s" % self.state["docid"] #TODO zero pad
      with pushd(thisdir):
        self.commit(None)
    type, data = parse_dm_data(msg.dm_data)
    if type == "id":
      self.set_doc(data)

  def set_doc(self, docid): #TODO staging?
    #if not exists create
    #chdir
    self.state["docid"] = docid
    thisdir = "D%s" % self.state["docid"] #TODO zero pad
    subprocess.run(["mkdir", thisdir])
    self.update_next_prompt() #TODO kind of crppy way do do this
    self.update_current_prompt()

  def onecmd(self, arg):
    if arg == "EOF": #TODO meh
      queue.put("exit")
      return True #yes stop interpreting
    super().onecmd(arg)

  def do_scan(self, arg): #TODO unfuck
    #TODO pass args
    #TODO thumbnail mode doesnt show path in title?
    def feh(queue, target=None): #if target is set load an image otherwise thumbnail view current dir
      subprocess.run("cp ../placeholder.jpg .", shell=True) #TODO fix all the subpocess handle inheritances
      #TODO figure out how to deal with the zoom viewport issues
      #TODO figure out how to not change zoom on resize (when killloading another feh for example)
      p = subprocess.Popen(["feh"] + ([ "-t", "-R", "2", "--keep-zoom-vp" ] if not target else [target]) + [ "--scale-down", "--auto-zoom"], stdin=subprocess.DEVNULL) #TODO zero pad #need to do this mess so i can kill it
      def killme():
        queue.get()
        logger.debug("feh killing self") #sometimes it doesnt work?? racy??
        p.kill()
      Thread(target=killme, daemon=True).start()
      p.communicate()

    def reload_feh(thisdir, stateid, target=None): #if target is set load an image otherwise thumbnail view current dir
      #if self.state["feh"] and self.state["whichfeh"] != thisdir:
      if self.state[stateid]: #TODO this is force reloading feh because everything is shit
        self.state[stateid].killqueue.put(0)
        self.state[stateid].pyproc.join()
        self.state[stateid] = None

      if not self.state[stateid]:
        queue = Queue()
        p = Process(target=feh, args=(queue,target), daemon=True)
        p.start()
        s = FehState(pyproc=p, killqueue=queue, thisdir=thisdir)
        self.state[stateid] = s

    if not self.state["docid"]: #TODO
      print("error: No document set.") #TODO lib stuff, return doenst seem to work right
      return

    thisdir = "D%s" % self.state["docid"] #TODO zero pad
    with pushd("./" + thisdir): #TODO wtf
      def getmaxidx():
        l = os.listdir(os.getcwd())
        res = list()
        for x in l:
          try:
            res += [ int(x.replace(".jpg", "")) ]
          except:
            pass
        return max(res, default=0)

      reload_feh(thisdir, "thumbs")
      #subprocess.run("xnview", close_fds=True) #TODO zero pad
      #subprocess.run("scanimage -L")
      targetfile = "%s.jpg" % (getmaxidx()+1)
      scanner = "genesys"
      subprocess.run(("scanimage --resolution 600 -d %s -o %s" % (scanner, targetfile)).split()) #TODO
      reload_feh(thisdir, "thumbs")
      reload_feh(thisdir, "preview", targetfile) #TODO have feh show did/id.jpg in the bar
      #checkl we are in repo etc
      #prep_env
      # call_scanimage()
      # set_preview_window

  def do_delete(self, arg):
    pass

  def do_reorder(self, arg):
    pass

  def commit(self, arg):
    if not os.listdir(): #TODO check
      open("placeholder", "w").close()
    subprocess.run("git annex add *",shell=True)
    subprocess.run(["git", "commit", "-m", "committed %s" % self.state["docid"]])
    #move temporary directory to store

  def do_commit(self, arg):
    thisdir = "D%s" % self.state["docid"] #TODO zero pad
    with pushd(thisdir):
      self.commit()

  def do_recover(self, arg):
    pass

  def do_open_preview(self, arg):
    pass

  def do_set_page(self, arg):
    pass

  def do_set_did(self, arg):
    self.state["docid"] = int(arg)

  def do_init_repo(self, arg):
    subprocess.run("git init".split());
    subprocess.run("git config --local user.name usr".split());
    subprocess.run("git config --local user.email eml".split());
    subprocess.run("git annex init".split())
    #TODO add gitignore, initial commit
    #TODO nondestructive
    # maybe just call a shell script or something
    # git init, config commit info
    # git annex init
    pass

import os
from contextlib import contextmanager


@contextmanager
def pushd(new_dir):
  previous_dir = os.getcwd()
  logger.debug("cdwd %s, param %s, newdir: %s" % (previous_dir, new_dir, os.path.realpath(os.path.join(previous_dir, new_dir))))
  os.chdir(new_dir)
  try:
    yield
  except Exception as e:
    logger.debug(e)
  finally: #TODO swallows exception?
    os.chdir(previous_dir)

if __name__ == "__main__":
  from multiprocessing import Queue, Process
  import multiprocessing as mp
  from threading import Thread

  #TODO using fork fixes the code reinit logging problem but spawn is cleaner
  #mp.set_start_method("spawn") #TODO does this actually help make anything more reliable?

  queue = Queue()
  repl = REPL(queue)

  def message_handler(queue, repl, p):
    exit = False
    while not exit:
      msg = queue.get()
      if isinstance(msg, ScannedMessage): #TODO
        repl.handle_new_dm_event(msg)
      if isinstance(msg, logging.LogRecord): #TODO
        print("\r" + msg.getMessage(), end="") #TODO hack, #TODO proper formatting
        rl_lib.rl_on_new_line()
        readline.redisplay()
      if msg == "exit":
        exit = True
        p.terminate()
        p.join() #TODO eh?


  p = Process(target=EvtServer.run, args=(queue,), name="dm_server", daemon=True)
  p.start()
  Thread(target=message_handler, args=(queue, repl, p)).start()
  #TODO problem here is you cant terminate the process from another event source without killing cmdloop somehow and i havent found how to get the main process to kill itself
  try:
    repl.cmdloop()
  except KeyboardInterrupt: #TODO good solution? , dunno  why it causes a trailing newline
    queue.put("exit") 
