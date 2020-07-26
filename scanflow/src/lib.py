#TODO quit signal from repl
#TODO make ^C work

import sys, os, inspect
import subprocess
import readline
import logging
from collections import namedtuple
import time

from threading import Thread

from os.path import join, dirname, abspath
currentdir = dirname(abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(join(currentdir, "../../")) #TODO meh
from common.repl import REPLBase, readline_preprint
from common.pushd import pushd
import common.multiprocess_main as multiprocess_main
from common.context import with_did

from dmserver import DMServer, ScannedMessage
from feh import feh, FehState, startfeh
from repo import Repo
from scanner import Scanner
from document import Document

import ctypes
rl_lib = ctypes.cdll.LoadLibrary(inspect.getfile(readline))

#https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python
logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger()

#####

#TODO
class REPLMessageHandler:
  def __init__(self, mq):
    self.mq = mq

  def start_mq(self):
    #TODO bug why doesnt this exit on exit
    Thread(target=self.message_handler, name="REPLMessageHandler").start() #TODO BUG audit this, using self here is fucky - actually no maybe its not that bad, thius is a thread not a process

  def message_handler(self): #  def message_handler(queue, repl, p):
    import queue
    while self.global_exit_q.empty():
      try:
        msg = self.mq.get(timeout=0.1) #TODO timout??

        if isinstance(msg, ScannedMessage): #TODO
          self.handle_new_dm_event(msg)

        if isinstance(msg, logging.LogRecord): #TODO make this designed, subprocess shouldnt inherit usable std  fds
          readline_preprint(msg.getMessage())

        if msg == "exit":
          self.global_exit_q.put(0) #TODO this seems to hang for some reason
      except queue.Empty:
        pass

  def handle_new_dm_event(self, msg):
    def parse_dm_data(data): #TODO
      return data.replace("(","").replace(")","").split()

    if self.state["docid"]:
      thisdir = "D%s" % self.state["docid"] #TODO zero pad
      with pushd(thisdir):
        Repo.commit(self.state["docid"])
    type, data = parse_dm_data(msg.dm_data)
    if type == "id":
      self.set_doc(data)

  #TODO unfuck
  def reload_feh(self, thisdir, stateid, target=None): #if target is set load an image otherwise thumbnail view current dir
    #if self.state["feh"] and self.state["whichfeh"] != thisdir:
    if self.state[stateid]: #TODO this is force reloading feh because everything is shit
      self.state[stateid].killqueue.put(0)
      self.state[stateid] = None

    if not self.state[stateid]:
      self.state[stateid] = startfeh(thisdir, target)


class REPL(REPLBase, REPLMessageHandler):
  def __init__(self, mq, global_exit_q):
    self.state = { "docid": None, "workdir": None, "thumbs": None, "preview": None }
    self.global_exit_q = global_exit_q
    REPLBase.__init__(self)
    REPLMessageHandler.__init__(self, mq)
    #self.do_init_repo(None) #TODO

  def update_next_prompt(self):
    self.prompt =  "(%s) " % ("document id: %s" % self.state["docid"])

  def set_doc(self, docid): #TODO staging?
    if self.state["docid"]:
      with with_did(self.state["docid"]) as doc:
        Repo.commit(self.state["docid"])

    #if not exists create
    #chdir
    self.state["docid"] = docid
    with with_did(self.state["docid"], create=True) as doc:
      pass
    self.update_next_prompt() #TODO kind of crppy way do do this
    self.update_current_prompt()

  def on_EOF(self):
      self.mq.put("exit") #TODO bug, ???

  def do_show(self, arg):
    with with_did(self.state["docid"]) as doc:
      self.reload_feh(doc.path, "preview", "%s.jpg" % arg) #TODO have feh show did/id.jpg in the bar

  def do_show_thumbs(self, arg):
    with with_did(self.state["docid"]) as doc:
      self.reload_feh(doc.path, "thumbs") #TODO have feh show did/id.jpg in the bar

  def do_layout(self, arg):
    subprocess.run(["qtile-cmd", "-o", "layout", "-f", "eval", "--args", 'self.relative_sizes = [0.1, 0.9]'], **self.outpipes)

  def do_scan(self, arg): #TODO unfuck
    #TODO pass args
    #TODO thumbnail mode doesnt show path in title?
    if not self.state["docid"]: #TODO
      print("error: No document set.") #TODO lib stuff, return doenst seem to work right
      return

    with with_did(self.state["docid"]) as doc:
      self.reload_feh(doc.path, "thumbs")
      result = Scanner.scan() #TODO unfuck
      self.reload_feh(doc.path, "thumbs")
      self.reload_feh(doc.path, "preview", result) #TODO have feh show did/id.jpg in the bar
      #checkl we are in repo etc
      #prep_env
      # call_scanimage()
      # set_preview_window

  def do_delete(self, arg):
    raise NotImplementedError

  def do_reorder(self, arg):
    raise NotImplementedError

  def do_commit(self, arg):
    with with_did(self.state["docid"]) as doc:
      Repo.commit(doc.id)

  def do_recover(self, arg):
    raise NotImplementedError


  def do_open_preview(self, arg):
    raise NotImplementedError

  def do_set_page(self, arg):
    raise NotImplementedError

  def do_set_did(self, arg):
    self.set_doc(arg)

  def do_init_repo(self, arg):
    raise NotImplementedError


class App(multiprocess_main.App):
  def send_kill_signals(self): #TODO move to lib? what about procs that dont support the procs interface?
    for p in self.procs:
      p.kill.put(0)
    while [p for p in self.procs if p.dead.empty()]:
      sleep(0.1)

  def main(self):
    from multiprocessing import Queue, Process
    import multiprocessing as mp
    from threading import Thread

    #TODO using fork fixes the code reinit logging problem but spawn is cleaner
    #mp.set_start_method("spawn") #TODO does this actually help make anything more reliable?
    mq = Queue()
    repl = REPL(mq, self.global_exit_q)
    repl.start_mq()

    Process(target=DMServer.run, args=(repl.mq, self.global_exit_q), name="dm_server", daemon=True).start()
    #TODO problem here is you cant terminate the process from another event source without killing cmdloop somehow and i havent found how to get the main process to kill itself
    repl.cmdloop()

App(__name__ == "__main__").run()
