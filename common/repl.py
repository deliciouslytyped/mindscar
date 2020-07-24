import cmd
import readline

from .subst import Constants #TODO some kind of config class?

import inspect
import os

import ctypes
rl_lib = ctypes.cdll.LoadLibrary(inspect.getfile(readline))


#TODO way to handle interrupting prints (set my own stdout file descriptor to inherit

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

