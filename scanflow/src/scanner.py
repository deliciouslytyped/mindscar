import os
import subprocess

class Scanner:
  def scan():
    def getmaxidx():
      l = os.listdir(os.getcwd())
      res = list()
      for x in l:
        try:
          res += [ int(x.replace(".jpg", "")) ]
        except:
          pass
      return max(res, default=0)
    #subprocess.run("scanimage -L")
    targetfile = "%s.jpg" % (getmaxidx()+1)
    scanner = "genesys"
    subprocess.run(("scanimage --resolution 600 -d %s -o %s" % (scanner, targetfile)).split()) #TODO
    return targetfile
