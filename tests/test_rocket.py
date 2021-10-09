import requests
import threading
import unittest

import rocket3

def demo_app(environ, start_response):
    start_response(200, "Hello World")

class SimpleTest(unittest.TestCase):

    def start_server(self):
        rocket = rocket3.Rocket3(("127.0.0.1", 8007),
                                 "wsgi",
                                 {"wsgi_app": demo_app})
        rocket.start()

    def start_client(self):
        res = requests.get("http://127.0.0.1:8007")
        self.assertTrue(res.content, "Hello World")
    
    def test_server(self):
        server = threading.Thread(target=self.start_server)
        server.daemon = True
        server.start()
        self.start_client()


