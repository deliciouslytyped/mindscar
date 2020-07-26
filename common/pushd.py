from os import chdir, getcwd
from os.path import join, realpath
from contextlib import contextmanager

import logging
logger = logging.getLogger() # TODO

@contextmanager
def pushd(new_dir):
  previous_dir = getcwd()
  logger.debug("cdwd %s, param %s, newdir: %s" % (previous_dir, new_dir, realpath(join(previous_dir, new_dir))))
  chdir(new_dir)
  try:
    yield
  except Exception as e:
    chdir(previous_dir)
    raise e
  else: #TODO swallows exception?
    chdir(previous_dir)

