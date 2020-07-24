from threading import Thread
import subprocess
import time

from collections import namedtuple

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
  p.communicate()

  #attempt to relayout qtile
  time.sleep(0.1)
  subprocess.run([" qtile-cmd", "-o", "layout", "-f", "eval", "--args", 'self.relative_sizes = [0.1, 0.9]'])


