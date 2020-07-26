#! /usr/bin/env python
#TODO sigint is getting passed to xephyr for some reason, otherwise normal exiting works
#TODO exit on exit of konsole
import os
import sys
import time

import subprocess as s

import inspect
from os.path import join, dirname, abspath, realpath
currentdir = dirname(abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(join(currentdir, "../")) #TODO meh
from common.supervisor import run
import common.multiprocess_main as multiprocess_main

class App(multiprocess_main.App):
  def send_kill_signals(self): #TODO partial failure on dict keys #TODO race condition somewhere? can still kill xephyr first
    self.l.debug("trying to close qtile")
    while self.procs["qtile"].dead.empty():
      s.run("qtile-cmd -o cmd -f shutdown".split())
      time.sleep(0.1)
    self.l.debug("waiting arbitrary time for qtile to finish closing")
    time.sleep(2)
    self.l.debug("trying to close xeph")
    while self.procs["xeph"].dead.empty():
      self.procs["xeph"].kill.put(0)
      time.sleep(0.1)

  def main(self):
    innerdisplay = ":1"

    self.procs["xeph"] = run("Xephyr %s -screen 1600x900" % innerdisplay)
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

    #TODO separate repo and home?
    if "repo" not in os.listdir(): #todo what if file
      try:
        os.mkdir("repo")
      except:
        self.l.debug("could not create repo root")
        kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph)
      s.run("cp gitignore ./repo/.gitignore", shell=True)
      s.run("cp qtile.py ./repo", shell=True)

    home = realpath(join(os.getcwd(), "./repo"))
    os.chdir(home)
    os.environ["HOME"] = home
    os.environ["DISPLAY"] = innerdisplay
    self.procs["qtile"] = run("qtile -c %s" % realpath(join(os.getcwd(), "./qtile.py")))
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

    #TODO GC issue? if i dont assign the retval things break
    self.procs["konsole"] = run(["bash", "-c", """konsole -e bash --init-file <(echo "python3 ../src/lib.py")"""], nosplit=True) #TODO is launcher that closes immediately
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

App(__name__ == "__main__", prevent_falling_off=True).run()
