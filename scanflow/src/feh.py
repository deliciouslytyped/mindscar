#TODO make this consistent with the rest of the arch
from threading import Thread
import multiprocessing as mp

import subprocess
import time

from collections import namedtuple

import logging
logger = logging.getLogger()

FehState = namedtuple("FehState", ["pyproc", "killqueue", "thisdir"])

def feh(queue, target=None): #if target is set load an image otherwise thumbnail view current dir
  import time
  subprocess.run("cp ../placeholder.jpg .", shell=True) #TODO fix all the subpocess handle inheritances
  #TODO figure out how to deal with the zoom viewport issues  
  #TODO figure out how to not change zoom on resize (when killloading another feh for example)
  p = subprocess.Popen(["feh"] + ([ "-t", "-R", "2", "--keep-zoom-vp" ] if not target else [target]) + [ "--scale-down", "--auto-zoom"], stdin=subprocess.DEVNULL) #TODO zero pad #need to do this mess so i can kill it
  def killme():
    queue.get()
    logger.debug("feh killing self") #sometimes it doesnt work?? racy??
    p.kill()
  Thread(target=killme, daemon=True).start()
  #TODO use a daemon with detection instead or something, but really shoudl jsut write qtile mod
  def relayout():
    #attempt to relayout qtile
    time.sleep(1.5)
    print("wtSDAFASDFSDFASDFf")
    subprocess.run(["qtile-cmd", "-o", "layout", "-f", "eval", "--args", 'self.relative_sizes = [0.1, 0.9]'])
  Thread(target=relayout, daemon=True).start()
  p.communicate()




def startfeh(thisdir, target):
  queue = mp.Queue()
  p = mp.Process(target=feh, args=(queue,target), daemon=True)
  p.start()
  s = FehState(pyproc=p, killqueue=queue, thisdir=thisdir)
  return s

