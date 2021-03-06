#Embedded file name: cherrypy/tutorial\tut01_helloworld.py
"""
Tutorial - Hello World

The most basic (working) CherryPy application possible.
"""
import cherrypy

class HelloWorld:
    """ Sample request handler class. """

    def index(self):
        return 'Hello world!'

    index.exposed = True


import os.path
tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')
if __name__ == '__main__':
    cherrypy.quickstart(HelloWorld(), config=tutconf)
else:
    cherrypy.tree.mount(HelloWorld(), config=tutconf)
