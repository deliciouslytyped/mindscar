from os.path import dirname, abspath
import inspect

import logging
logger = logging.getLogger()

def subst(s):
  # https://stackoverflow.com/questions/50499/how-do-i-get-the-path-and-name-of-the-file-that-is-currently-executing
  selfd = dirname(abspath(inspect.getfile(inspect.currentframe()))) # script directory
  proot = abspath(selfd + "/..")
  res = s.format(selfd=selfd, proot=proot)
  logger.debug((s, res)) #TODO figure out how to deal with the logger
  return res

class Constants:
  histfile = subst("console.hist") #TODO #TODO something for periodically committing this?
