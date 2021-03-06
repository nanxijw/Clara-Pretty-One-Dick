#Embedded file name: carbon/common/lib/cherrypy/process\servers.py
r"""
Starting in CherryPy 3.1, cherrypy.server is implemented as an
:ref:`Engine Plugin<plugins>`. It's an instance of
:class:`cherrypy._cpserver.Server`, which is a subclass of
:class:`cherrypy.process.servers.ServerAdapter`. The ``ServerAdapter`` class
is designed to control other servers, as well.

Multiple servers/ports
======================

If you need to start more than one HTTP server (to serve on multiple ports, or
protocols, etc.), you can manually register each one and then start them all
with engine.start::

    s1 = ServerAdapter(cherrypy.engine, MyWSGIServer(host='0.0.0.0', port=80))
    s2 = ServerAdapter(cherrypy.engine, another.HTTPServer(host='127.0.0.1', SSL=True))
    s1.subscribe()
    s2.subscribe()
    cherrypy.engine.start()

.. index:: SCGI

FastCGI/SCGI
============

There are also Flup\ **F**\ CGIServer and Flup\ **S**\ CGIServer classes in
:mod:`cherrypy.process.servers`. To start an fcgi server, for example,
wrap an instance of it in a ServerAdapter::

    addr = ('0.0.0.0', 4000)
    f = servers.FlupFCGIServer(application=cherrypy.tree, bindAddress=addr)
    s = servers.ServerAdapter(cherrypy.engine, httpserver=f, bind_addr=addr)
    s.subscribe()

The :doc:`cherryd</deployguide/cherryd>` startup script will do the above for
you via its `-f` flag.
Note that you need to download and install `flup <http://trac.saddi.com/flup>`_
yourself, whether you use ``cherryd`` or not.

.. _fastcgi:
.. index:: FastCGI

FastCGI
-------

A very simple setup lets your cherry run with FastCGI.
You just need the flup library,
plus a running Apache server (with ``mod_fastcgi``) or lighttpd server.

CherryPy code
^^^^^^^^^^^^^

hello.py::

    #!/usr/bin/python
    import cherrypy
    
    class HelloWorld:
        """Sample request handler class."""
        def index(self):
            return "Hello world!"
        index.exposed = True
    
    cherrypy.tree.mount(HelloWorld())
    # CherryPy autoreload must be disabled for the flup server to work
    cherrypy.config.update({'engine.autoreload_on':False})

Then run :doc:`/deployguide/cherryd` with the '-f' arg::

    cherryd -c <myconfig> -d -f -i hello.py

Apache
^^^^^^

At the top level in httpd.conf::

    FastCgiIpcDir /tmp
    FastCgiServer /path/to/cherry.fcgi -idle-timeout 120 -processes 4

And inside the relevant VirtualHost section::

    # FastCGI config
    AddHandler fastcgi-script .fcgi
    ScriptAliasMatch (.*$) /path/to/cherry.fcgi$1

Lighttpd
^^^^^^^^

For `Lighttpd <http://www.lighttpd.net/>`_ you can follow these
instructions. Within ``lighttpd.conf`` make sure ``mod_fastcgi`` is
active within ``server.modules``. Then, within your ``$HTTP["host"]``
directive, configure your fastcgi script like the following::

    $HTTP["url"] =~ "" {
      fastcgi.server = (
        "/" => (
          "script.fcgi" => (
            "bin-path" => "/path/to/your/script.fcgi",
            "socket"          => "/tmp/script.sock",
            "check-local"     => "disable",
            "disable-time"    => 1,
            "min-procs"       => 1,
            "max-procs"       => 1, # adjust as needed
          ),
        ),
      )
    } # end of $HTTP["url"] =~ "^/"

Please see `Lighttpd FastCGI Docs
<http://redmine.lighttpd.net/wiki/lighttpd/Docs:ModFastCGI>`_ for an explanation 
of the possible configuration options.
"""
import sys
import time

class ServerAdapter(object):
    """Adapter for an HTTP server.
    
    If you need to start more than one HTTP server (to serve on multiple
    ports, or protocols, etc.), you can manually register each one and then
    start them all with bus.start:
    
        s1 = ServerAdapter(bus, MyWSGIServer(host='0.0.0.0', port=80))
        s2 = ServerAdapter(bus, another.HTTPServer(host='127.0.0.1', SSL=True))
        s1.subscribe()
        s2.subscribe()
        bus.start()
    """

    def __init__(self, bus, httpserver = None, bind_addr = None):
        self.bus = bus
        self.httpserver = httpserver
        self.bind_addr = bind_addr
        self.interrupt = None
        self.running = False

    def subscribe(self):
        self.bus.subscribe('start', self.start)
        self.bus.subscribe('stop', self.stop)

    def unsubscribe(self):
        self.bus.unsubscribe('start', self.start)
        self.bus.unsubscribe('stop', self.stop)

    def start(self):
        """Start the HTTP server."""
        if self.bind_addr is None:
            on_what = 'unknown interface (dynamic?)'
        elif isinstance(self.bind_addr, tuple):
            host, port = self.bind_addr
            on_what = '%s:%s' % (host, port)
        else:
            on_what = 'socket file: %s' % self.bind_addr
        if self.running:
            self.bus.log('Already serving on %s' % on_what)
            return
        self.interrupt = None
        if not self.httpserver:
            raise ValueError('No HTTP server has been created.')
        if isinstance(self.bind_addr, tuple):
            wait_for_free_port(*self.bind_addr)
        import threading
        t = threading.Thread(target=self._start_http_thread)
        t.setName('HTTPServer ' + t.getName())
        t.start()
        self.wait()
        self.running = True
        self.bus.log('Serving on %s' % on_what)

    start.priority = 75

    def _start_http_thread(self):
        """HTTP servers MUST be running in new threads, so that the
        main thread persists to receive KeyboardInterrupt's. If an
        exception is raised in the httpserver's thread then it's
        trapped here, and the bus (and therefore our httpserver)
        are shut down.
        """
        try:
            self.httpserver.start()
        except KeyboardInterrupt:
            self.bus.log('<Ctrl-C> hit: shutting down HTTP server')
            self.interrupt = sys.exc_info()[1]
            self.bus.exit()
        except SystemExit:
            self.bus.log('SystemExit raised: shutting down HTTP server')
            self.interrupt = sys.exc_info()[1]
            self.bus.exit()
            raise
        except:
            self.interrupt = sys.exc_info()[1]
            self.bus.log('Error in HTTP server: shutting down', traceback=True, level=40)
            self.bus.exit()
            raise

    def wait(self):
        """Wait until the HTTP server is ready to receive requests."""
        while not getattr(self.httpserver, 'ready', False):
            if self.interrupt:
                raise self.interrupt
            time.sleep(0.1)

        if isinstance(self.bind_addr, tuple):
            host, port = self.bind_addr
            wait_for_occupied_port(host, port)

    def stop(self):
        """Stop the HTTP server."""
        if self.running:
            self.httpserver.stop()
            if isinstance(self.bind_addr, tuple):
                wait_for_free_port(*self.bind_addr)
            self.running = False
            self.bus.log('HTTP Server %s shut down' % self.httpserver)
        else:
            self.bus.log('HTTP Server %s already shut down' % self.httpserver)

    stop.priority = 25

    def restart(self):
        """Restart the HTTP server."""
        self.stop()
        self.start()


class FlupCGIServer(object):
    """Adapter for a flup.server.cgi.WSGIServer."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.ready = False

    def start(self):
        """Start the CGI server."""
        from flup.server.cgi import WSGIServer
        self.cgiserver = WSGIServer(*self.args, **self.kwargs)
        self.ready = True
        self.cgiserver.run()

    def stop(self):
        """Stop the HTTP server."""
        self.ready = False


class FlupFCGIServer(object):
    """Adapter for a flup.server.fcgi.WSGIServer."""

    def __init__(self, *args, **kwargs):
        if kwargs.get('bindAddress', None) is None:
            import socket
            if not hasattr(socket, 'fromfd'):
                raise ValueError('Dynamic FCGI server not available on this platform. You must use a static or external one by providing a legal bindAddress.')
        self.args = args
        self.kwargs = kwargs
        self.ready = False

    def start(self):
        """Start the FCGI server."""
        from flup.server.fcgi import WSGIServer
        self.fcgiserver = WSGIServer(*self.args, **self.kwargs)
        self.fcgiserver._installSignalHandlers = lambda : None
        self.fcgiserver._oldSIGs = []
        self.ready = True
        self.fcgiserver.run()

    def stop(self):
        """Stop the HTTP server."""
        self.fcgiserver._keepGoing = False
        self.fcgiserver._threadPool.maxSpare = self.fcgiserver._threadPool._idleCount
        self.ready = False


class FlupSCGIServer(object):
    """Adapter for a flup.server.scgi.WSGIServer."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.ready = False

    def start(self):
        """Start the SCGI server."""
        from flup.server.scgi import WSGIServer
        self.scgiserver = WSGIServer(*self.args, **self.kwargs)
        self.scgiserver._installSignalHandlers = lambda : None
        self.scgiserver._oldSIGs = []
        self.ready = True
        self.scgiserver.run()

    def stop(self):
        """Stop the HTTP server."""
        self.ready = False
        self.scgiserver._keepGoing = False
        self.scgiserver._threadPool.maxSpare = 0


def client_host(server_host):
    """Return the host on which a client can connect to the given listener."""
    if server_host == '0.0.0.0':
        return '127.0.0.1'
    if server_host in ('::', '::0', '::0.0.0.0'):
        return '::1'
    return server_host


def check_port(host, port, timeout = 1.0):
    """Raise an error if the given port is not free on the given host."""
    if not host:
        raise ValueError("Host values of '' or None are not allowed.")
    host = client_host(host)
    port = int(port)
    import socket
    try:
        info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        if ':' in host:
            info = [(socket.AF_INET6,
              socket.SOCK_STREAM,
              0,
              '',
              (host,
               port,
               0,
               0))]
        else:
            info = [(socket.AF_INET,
              socket.SOCK_STREAM,
              0,
              '',
              (host, port))]

    for res in info:
        af, socktype, proto, canonname, sa = res
        s = None
        try:
            s = socket.socket(af, socktype, proto)
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            raise IOError('Port %s is in use on %s; perhaps the previous httpserver did not shut down properly.' % (repr(port), repr(host)))
        except socket.error:
            if s:
                s.close()


def wait_for_free_port(host, port):
    """Wait for the specified port to become free (drop requests)."""
    if not host:
        raise ValueError("Host values of '' or None are not allowed.")
    for trial in range(50):
        try:
            check_port(host, port, timeout=0.1)
        except IOError:
            time.sleep(0.1)
        else:
            return

    raise IOError('Port %r not free on %r' % (port, host))


def wait_for_occupied_port(host, port):
    """Wait for the specified port to become active (receive requests)."""
    if not host:
        raise ValueError("Host values of '' or None are not allowed.")
    for trial in range(50):
        try:
            check_port(host, port)
        except IOError:
            return

        time.sleep(0.1)

    raise IOError('Port %r not bound on %r' % (port, host))
