import logging
from collections import namedtuple
from threading import Thread

import time

import http.server as h
import urllib.parse as up

ScannedMessage = namedtuple("ScannedMessage", ["dm_data"]) #TODO scoping https://stackoverflow.com/questions/16377215/how-to-pickle-a-namedtuple-instance-correctly
class DMServer: #TODO rename
  def run(mq, global_exit_q):
    import logging.handlers
    logger = logging.Logger("DMServer")
    qh = logging.handlers.QueueHandler(mq) #TODO
    qh.setLevel(logging.DEBUG) 
    f = logging.Formatter(logging._STYLES["%"][1]) #from logging.basicconfig #TODO still looks dfferent from the other stuff
    qh.setFormatter(f)
    logger.addHandler(qh) 

    class HRH(h.BaseHTTPRequestHandler):   
      def log_message(self, format, *args):
        logger.debug("%s - - [%s] %s\n" %
          (self.address_string(),
          self.log_date_time_string(),
          format%args))

      def do_GET(self):
        self.send_response(200)
        self.end_headers()

        request = self.requestline.split()[1] #TODO crap parser
        parsed = up.urlparse(request)
        if parsed.path == "/dat":
          dm_data = up.parse_qs(parsed.query)["dm"][0] #TODO no idea why this is an array
          mq.put(ScannedMessage(dm_data))

    try:
      httpd = h.HTTPServer(("", 9999), HRH)
    except OSError: #TODO
      logger.error("port in use")
      mq.put("exit")

    def supervisor():
      while global_exit_q.empty():
        time.sleep(0.1)
      httpd.shutdown()

    Thread(target=supervisor,daemon=True).start()

    httpd.serve_forever()


