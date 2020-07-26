#import multiprocessing_logging as ml
#ml.install_mp_handler() # TODO wait this probably doesnt help me with anything

from collections import deque
from threading import Thread

import cmd
import readline

from .subst import Constants #TODO some kind of config class?

import inspect
import os, sys
import time

import ctypes
rl_lib = ctypes.cdll.LoadLibrary(inspect.getfile(readline))

from io import StringIO

#class QueueWriter(mp.Queue)
#  def __init__(self):
#    super().__init__()
#    
#
#class TrackedIO:
#  def __init__():
#    def init_stream(streamname):
#      buffer = ??
#      real = getattr(sys, streamname)
#      setattr(self, streamname, real)
#      setattr(sys, streamname, buffer)
#
#    init_stream("stdout")
#    init_stream("stderr")
#    while res := wait(buf):
#      self.stdout.write(res) # a full line
#      self.readline_update
#
#    self.outpipes = { #TODO not thread safe, need to use queues internally?
#      "stdout": TextIO(line_buffer=True),
#      "stderr": TextIO()
#      }
#    self.real_outpipes = {
#      "stdout": stdout,
#      "stderr": stderr
#      }
#
#    def move_pipes():
#      has_data = 
#      while global_exit_q.empty() or has_data:
#        self.real_outpipes["stdout"].write(self.outpipes["stdout"].read()
#        self.real_outpipes["stderr"].write(self.outpipes["stderr"].read()
#        time.sleep(0.1)#TODO        #wake.get()
#
#    Thread(target=move_data, name="repl_move_pipes").start() #TODO maybe not the best solution to daemon because you could end up with data lost at the end
#
#  Line = namedtuple("Line", ["source_channel", "data"])
#
#  def set_thread_source_name(): #TODO?? #TODO return new stream object instead where you set the name in the constructor
#    pass
#  
#  def write(data):
#    self.write_q.put(Line(source_channel=self.name, data=data))

class LineBuffer:
  def __init__(self, global_exit_q, ostream):
    self.buf = deque()
    self.linebuf = ""
    self.ostream = ostream

    def bg_print(exit_q):
      while exit_q.empty():
        self.print_available()
        time.sleep(0.1)

    Thread(target=bg_print, args=(global_exit_q,)).start()

  def write(self, s):
    self.linebuf += s
    lines = self.linebuf.split("\n")
    lines, self.linebuf = lines[:-1], lines[-1]
    self.buf.extend(lines)
    #self.printavail() #also make one that does it on a timer

  def flush(self):
    self.ostream.flush()

  def print_available(self):
    try:
      while True:
        #self.ostream.write(self.buf.popleft() + "\n") 
        readline_preprint("|| %s" % self.buf.popleft(), stream=self.ostream) #TODO make this line thread safe
    except IndexError:
      pass

class TrackedIO:
  def __init__(self):
    self.realstderr = sys.stderr
    self.realstdout = sys.stdout
    self.stderr = LineBuffer(self.global_exit_q, sys.stderr)
    self.stdout = LineBuffer(self.global_exit_q, sys.stdout) #TODO BUG exit q comes from REPLMessageHandler #NOTE overwrites base class valeu
    sys.stdout = self.stdout
    sys.stderr = self.stderr

#TODO way to handle interrupting prints (set my own stdout file descriptor to inherit

#TODO "EOF" is nterpreted as a special string?? https://github.com/python/cpython/blob/3.8/Lib/cmd.py
#TODO factor into lib
class REPLBase(cmd.Cmd, TrackedIO):
  def __init__(self): # take stdout and stderr params?
    self.histfile = Constants.histfile
    cmd.Cmd.__init__(self)
#    TrackedIO.__init__(self) #TODO
    #super().__init__() #Does this cuase it to get called multiple times?
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

  def onecmd(self, arg):
    if arg == "EOF": #TODO meh
      self.on_EOF()
      return True #yes stop interpreting
    super().onecmd(arg)
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


def readline_preprint(s, stream=None):
  if stream:
    print("\r" + s, end="", file=stream) #TODO hack, #TODO proper formatting
  else:
    print("\r" + s, end="") #TODO hack, #TODO proper formatting
  rl_lib.rl_on_new_line() #how does this fit into this stream stuff
  readline.redisplay()

