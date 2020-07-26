#TODO logging

import logging
import multiprocessing as mp
from .supervisor import ProcStruct

import sys

class App:
  def __init__(self, runnable, prevent_falling_off=False):
    self.runnable = runnable #TODO error?
    self.prevent_falling_off = prevent_falling_off
    if runnable:
      mp.set_start_method("spawn") #TODO #WARN #NOTE needs to be run before any other mp code?
      self.global_exit_q = mp.Queue()

      self.procs = dict() #TODO attrdict
      logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        level=logging.DEBUG)
      self.logger = logging.getLogger() # todo fd pipe stuff
      self.l = self.logger
      self.l.setLevel(logging.DEBUG)

  def kill_self(self):
    self.global_exit_q.put(0)
    self.send_kill_signals() # send items to kill queues #TODO should block till done
    sys.exit(0)

  def _main(self):
    if self.runnable:
      try:
        self.main()

        if self.prevent_falling_off:
          input("press enter to exit")
        self.kill_self() #maybe i should use globals or a mutable reg or something so partial failure means still killable?
      except KeyboardInterrupt: #TODO good solution? , dunno  why it causes a trailing newline in scanflow
        self.kill_self()

  def run(self):
    self._main()
