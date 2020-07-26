#TODO how to deal with kill queues and daemonization?
import textwrap #TODO these are useless rn because of inherited descriptors

import subprocess as s
import multiprocessing as mp
import threading as th

import signal
import os

from collections import namedtuple

ProcStruct = namedtuple("ProcStruct", ["kill", "dead"])

def printret(command, stdout, stderr):
  print("command: %s" % command)
  if stdout:
    print(textwrap.indent(stdout, "  "))
  if stderr:
    print(textwrap.indent(stderr, "  "), file=sys.stderr)

#This should be below run() but spawn mode can only pickle top level objects
def supervisor(command, kill_q, dead_q, args, kwargs, environ, nosplit=False):
  #TODO handle stdout forwarding
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

  return ProcStruct(kill_q, dead_q)

