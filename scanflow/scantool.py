#! /usr/bin/env python
#TODO sigint is getting passed to xephyr for some reason, otherwise normal exiting works
#TODO exit on exit of konsole
import os
import sys
import time

import subprocess as s
import multiprocessing as mp
import threading as th

import inspect
from os.path import join, dirname, abspath
currentdir = dirname(abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(join(currentdir, "../")) #TODO meh
from common.supervisor import run

def kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph):
  global_exit_q.put(0)

  print("trying to close qtile")
  while qtile_dead.empty():
    s.run("qtile-cmd -o cmd -f shutdown".split())
    time.sleep(0.1)
  print("waiting arbitrary time for qtile to finish closing")
  time.sleep(2)
  print("trying to close xeph")
  while xeph_dead.empty():
    kill_xeph.put(0)
    time.sleep(0.1)
  sys.exit(0)

if __name__ == "__main__":
  try:
    mp.set_start_method("spawn")
    global_exit_q = mp.Queue()

    innerdisplay = ":1"

    kill_xeph, xeph_dead = run("Xephyr %s -screen 1600x900" % innerdisplay)
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

    if "repo" not in os.listdir(): #todo what if file
      try:
        os.mkdir("repo")
      except:
        print("could not create repo root")
        kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph)
      s.run("cp gitignore ./repo/.gitignore", shell=True)
      s.run("cp qtile.py ./repo", shell=True)

    home = os.path.realpath(os.path.join(os.getcwd(), "./repo"))
    os.chdir(home)
    os.environ["HOME"] = home
    os.environ["DISPLAY"] = innerdisplay
    _, qtile_dead, = run("qtile -c %s" % os.path.realpath(os.path.join(os.getcwd(), "./qtile.py")))
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?


    #TODO GC issue? if i dont assign the retval things break
    blah1, blah2 = run(["bash", "-c", """konsole -e bash --init-file <(echo "python3 ../src/lib.py")"""], nosplit=True)
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

    input("press enter to exit")
    kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph) #maybe i should use globals or a mutable reg or something so partial failure means still killable?
  except KeyboardInterrupt:
    kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph)

