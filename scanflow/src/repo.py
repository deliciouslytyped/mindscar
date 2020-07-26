import subprocess
import os

class Repo:
  def init():
    subprocess.run("git init".split());
    subprocess.run("git config --local user.name usr".split());
    subprocess.run("git config --local user.email eml".split());
    subprocess.run("git annex init".split())
    #TODO add gitignore, initial commit
    #TODO nondestructive
    # maybe just call a shell script or something
    # git init, config commit info
    # git annex init

  def commit(docid):
    if not os.listdir(): #TODO check
      open("placeholder", "w").close()
    subprocess.run("git annex add *",shell=True)
    subprocess.run(["git", "commit", "-m", "committed %s" % docid])
    #move temporary directory to store

