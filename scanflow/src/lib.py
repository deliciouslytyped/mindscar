#TODO quit signal from repl
#TODO make ^C work

import sys, os, inspect
import subprocess

from os.path import join, dirname, abspath
currentdir = dirname(abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(join(currentdir, "../../")) #TODO meh
from common.repl import REPLBase
from common.pushd import pushd


from dmserver import EvtServer, ScannedMessage
from feh import feh, FehState

#import multiprocessing_logging as ml
#ml.install_mp_handler() # TODO wait this probably doesnt help me with anything


from collections import namedtuple

import readline

import logging
#https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python
logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger()

#####
import ctypes
rl_lib = ctypes.cdll.LoadLibrary(inspect.getfile(readline))
#####

class REPLMessageHandler:
  def __init__(self, queue):
    pass

  def handle_message(self):
    pass

class REPL(REPLBase, ReplMessageHandler):
  def __init__(self, queue):
    self.state = { "docid": None, "workdir": None, "thumbs": None, "preview": None }
    super().__init__()
    self.do_init_repo(None) #TODO

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
    if self.state["docid"]:
      thisdir = "D%s" % self.state["docid"] #TODO zero pad
      with pushd("./" + thisdir): #TODO wtf
        self.commit()

    #if not exists create
    #chdir
    self.state["docid"] = docid
    thisdir = "D%s" % self.state["docid"] #TODO zero pad
    subprocess.run(["mkdir", thisdir])
    self.update_next_prompt() #TODO kind of crppy way do do this
    self.update_current_prompt()

  def reload_feh(self, thisdir, stateid, target=None): #if target is set load an image otherwise thumbnail view current dir
    import time
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

  def onecmd(self, arg):
    if arg == "EOF": #TODO meh
      queue.put("exit")
      return True #yes stop interpreting
    super().onecmd(arg)

  def do_show(self, arg):
    thisdir = "D%s" % self.state["docid"] #TODO zero pad
    with pushd("./" + thisdir): #TODO wtf
      self.reload_feh(thisdir, "preview", "%s.jpg" % arg) #TODO have feh show did/id.jpg in the bar

  def do_show_thumbs(self, arg):
    thisdir = "D%s" % self.state["docid"] #TODO zero pad
    with pushd("./" + thisdir): #TODO wtf
      self.reload_feh(thisdir, "thumbs") #TODO have feh show did/id.jpg in the bar
  def do_layout(self, arg):
    subprocess.run(["qtile-cmd", "-o", "layout", "-f", "eval", "--args", 'self.relative_sizes = [0.1, 0.9]'])

  def do_scan(self, arg): #TODO unfuck
    #TODO pass args
    #TODO thumbnail mode doesnt show path in title?
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

      self.reload_feh(thisdir, "thumbs")
      #subprocess.run("xnview", close_fds=True) #TODO zero pad
      #subprocess.run("scanimage -L")
      targetfile = "%s.jpg" % (getmaxidx()+1)
      scanner = "genesys"
      subprocess.run(("scanimage --resolution 600 -d %s -o %s" % (scanner, targetfile)).split()) #TODO
      self.reload_feh(thisdir, "thumbs")
      self.reload_feh(thisdir, "preview", targetfile) #TODO have feh show did/id.jpg in the bar
      #checkl we are in repo etc
      #prep_env
      # call_scanimage()
      # set_preview_window

  def do_delete(self, arg):
    pass

  def do_reorder(self, arg):
    pass

  def commit(self):
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
    self.set_doc(arg)

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
