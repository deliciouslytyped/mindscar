from contextlib import contextmanager
import os.path
import subprocess

from .pushd import pushd

from scanflow.src.document import Document
#TODO does this really go in common, since its pulling types from scanflow/src, or do i mve the latter here
@contextmanager
def with_did(did, create=False): #TODO validation? - should be done on other side
  assert(did != None)
  path = os.path.join(os.getcwd(), "D%s" % did) #TODO some sort of static root #TODO zero pad
  if create:
    subprocess.run(["mkdir", path]) #TODO
  with pushd(path):
    yield Document(path=path, id=did)
