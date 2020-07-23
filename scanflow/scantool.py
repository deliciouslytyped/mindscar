#! /usr/bin/env python
#TODO sigint is getting passed to xephyr for some reason, otherwise normal exiting works
#TODO exit on exit of konsole
import os
import sys
import time

import subprocess as s
import multiprocessing as mp
import threading as th

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

def printret(command, stdout, stderr):
  import textwrap #TODO these are useless rn because of inherited descriptors
  print("command: %s" % command)
  if stdout:
    print(textwrap.indent(stdout, "  "))
  if stderr:
    print(textwrap.indent(stderr, "  "), file=sys.stderr)

#This should be below run() but spawn mode can only pickle top level objects
def supervisor(command, kill_q, dead_q, args, kwargs, environ, nosplit=False):
  #TODO handle stdout forwarding
  import signal
  signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore sigint / keyboardinterrupt in child processes  https://stackoverflow.com/questions/44774853/exit-multiprocesses-gracefully-in-python3

  os.environ.update(environ) # spawn doesnt keep environ

  print("starting %s" % command)
  p = s.Popen(command if nosplit else command.split(), stdin=s.PIPE, *args, **kwargs)
  def killme():
    kill_q.get()
    p.kill()
    dead_q.put(0)
  th.Thread(target=killme, daemon=True).start() 
  printret(command, *p.communicate())
  dead_q.put(0)

def run(command, nosplit=False, *args, **kwargs):
  kill_q = mp.Queue()
  dead_q = mp.Queue()
  print("attempting to start %s" % command)
  mp.Process(target=supervisor, args=(command, kill_q, dead_q, args, kwargs, dict(os.environ), nosplit), name="run-%s" % (command[0] if nosplit else command.split()[0]), daemon=True).start()

  return kill_q, dead_q

if __name__ == "__main__":
  try:
    mp.set_start_method("spawn")
    global_exit_q = mp.Queue()

    innerdisplay = ":1"

    kill_xeph, xeph_dead = run("Xephyr %s -screen 1600x900" % innerdisplay)
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

    os.environ["HOME"] = os.path.realpath(os.path.join(os.getcwd(), "./config"))
    os.environ["DISPLAY"] = innerdisplay
    _, qtile_dead, = run("qtile -c %s" % os.path.realpath(os.path.join(os.getcwd(), "./qtile.py")))
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?


    #TODO GC issue? if i dont assign the retval things break
    blah1, blah2 = run(["bash", "-c", """konsole -e bash --init-file <(echo "cd %s/config; python3 ../src/lib.py")""" % os.getcwd()], nosplit=True)
    time.sleep(1) #TODO no actual way to check if a process has started i think - and besides what does that even mean, ready?

    input("press enter to exit")
    kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph) #maybe i should use globals or a mutable reg or something so partial failure means still killable?
  except KeyboardInterrupt:
    kill_self(qtile_dead, xeph_dead, global_exit_q, kill_xeph)

