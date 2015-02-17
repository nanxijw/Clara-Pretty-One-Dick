#Embedded file name: carbon/common/lib/werkzeug\serving.py
"""
    werkzeug.serving
    ~~~~~~~~~~~~~~~~

    There are many ways to serve a WSGI application.  While you're developing
    it you usually don't want a full blown webserver like Apache but a simple
    standalone one.  From Python 2.5 onwards there is the `wsgiref`_ server in
    the standard library.  If you're using older versions of Python you can
    download the package from the cheeseshop.

    However there are some caveats. Sourcecode won't reload itself when
    changed and each time you kill the server using ``^C`` you get an
    `KeyboardInterrupt` error.  While the latter is easy to solve the first
    one can be a pain in the ass in some situations.

    The easiest way is creating a small ``start-myproject.py`` that runs the
    application::

        #!/usr/bin/env python
        # -*- coding: utf-8 -*-
        from myproject import make_app
        from werkzeug import run_simple

        app = make_app(...)
        run_simple('localhost', 8080, app, use_reloader=True)

    You can also pass it a `extra_files` keyword argument with a list of
    additional files (like configuration files) you want to observe.

    For bigger applications you should consider using `werkzeug.script`
    instead of a simple start file.


    :copyright: (c) 2010 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
import socket
import sys
import time
import thread
import subprocess
from urllib import unquote
from itertools import chain
from SocketServer import ThreadingMixIn, ForkingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import werkzeug
from werkzeug._internal import _log
from werkzeug.exceptions import InternalServerError

class WSGIRequestHandler(BaseHTTPRequestHandler, object):
    """A request handler that implements WSGI dispatching."""

    @property
    def server_version(self):
        return 'Werkzeug/' + werkzeug.__version__

    def make_environ(self):
        if '?' in self.path:
            path_info, query = self.path.split('?', 1)
        else:
            path_info = self.path
            query = ''
        url_scheme = self.server.ssl_context is None and 'http' or 'https'
        environ = {'wsgi.version': (1, 0),
         'wsgi.url_scheme': url_scheme,
         'wsgi.input': self.rfile,
         'wsgi.errors': sys.stderr,
         'wsgi.multithread': self.server.multithread,
         'wsgi.multiprocess': self.server.multiprocess,
         'wsgi.run_once': False,
         'SERVER_SOFTWARE': self.server_version,
         'REQUEST_METHOD': self.command,
         'SCRIPT_NAME': '',
         'PATH_INFO': unquote(path_info),
         'QUERY_STRING': query,
         'CONTENT_TYPE': self.headers.get('Content-Type', ''),
         'CONTENT_LENGTH': self.headers.get('Content-Length', ''),
         'REMOTE_ADDR': self.client_address[0],
         'REMOTE_PORT': self.client_address[1],
         'SERVER_NAME': self.server.server_address[0],
         'SERVER_PORT': str(self.server.server_address[1]),
         'SERVER_PROTOCOL': self.request_version}
        for key, value in self.headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value

        return environ

    def run_wsgi(self):
        app = self.server.app
        environ = self.make_environ()
        headers_set = []
        headers_sent = []

        def write(data):
            if not headers_sent:
                status, response_headers = headers_sent[:] = headers_set
                code, msg = status.split(None, 1)
                self.send_response(int(code), msg)
                header_keys = set()
                for key, value in response_headers:
                    self.send_header(key, value)
                    key = key.lower()
                    header_keys.add(key)

                if 'content-length' not in header_keys:
                    self.close_connection = True
                    self.send_header('Connection', 'close')
                if 'server' not in header_keys:
                    self.send_header('Server', self.version_string())
                if 'date' not in header_keys:
                    self.send_header('Date', self.date_time_string())
                self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()

        def start_response(status, response_headers, exc_info = None):
            if exc_info:
                try:
                    if headers_sent:
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None

            elif headers_set:
                raise AssertionError('Headers already set')
            headers_set[:] = [status, response_headers]
            return write

        def execute(app):
            application_iter = app(environ, start_response)
            try:
                for data in application_iter:
                    write(data)

                if not headers_sent:
                    write('')
            finally:
                if hasattr(application_iter, 'close'):
                    application_iter.close()
                application_iter = None

        try:
            execute(app)
        except (socket.error, socket.timeout) as e:
            self.connection_dropped(e, environ)
        except:
            if self.server.passthrough_errors:
                raise
            from werkzeug.debug.tbtools import get_current_traceback
            traceback = get_current_traceback(ignore_system_exceptions=True)
            try:
                if not headers_sent:
                    del headers_set[:]
                execute(InternalServerError())
            except:
                pass

            self.server.log('error', 'Error on request:\n%s', traceback.plaintext)

    def handle(self):
        """Handles a request ignoring dropped connections."""
        try:
            return BaseHTTPRequestHandler.handle(self)
        except (socket.error, socket.timeout) as e:
            self.connection_dropped(e)
        except:
            if self.server.ssl_context is None or not is_ssl_error():
                raise

    def connection_dropped(self, error, environ = None):
        """Called if the connection was closed by the client.  By default
        nothing happens.
        """
        pass

    def handle_one_request(self):
        """Handle a single HTTP request."""
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
        elif self.parse_request():
            return self.run_wsgi()

    def send_response(self, code, message = None):
        """Send the response header and log the response code."""
        self.log_request(code)
        if message is None:
            message = code in self.responses and self.responses[code][0] or ''
        if self.request_version != 'HTTP/0.9':
            self.wfile.write('%s %d %s\r\n' % (self.protocol_version, code, message))

    def version_string(self):
        return BaseHTTPRequestHandler.version_string(self).strip()

    def address_string(self):
        return self.client_address[0]

    def log_request(self, code = '-', size = '-'):
        self.log('info', '"%s" %s %s', self.requestline, code, size)

    def log_error(self, *args):
        self.log('error', *args)

    def log_message(self, format, *args):
        self.log('info', format, *args)

    def log(self, type, message, *args):
        _log(type, '%s - - [%s] %s\n' % (self.address_string(), self.log_date_time_string(), message % args))


BaseRequestHandler = WSGIRequestHandler

def generate_adhoc_ssl_context():
    """Generates an adhoc SSL context for the development server."""
    from random import random
    from OpenSSL import crypto, SSL
    cert = crypto.X509()
    cert.set_serial_number(int(random() * sys.maxint))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000)
    subject = cert.get_subject()
    subject.CN = '*'
    subject.O = 'Dummy Certificate'
    issuer = cert.get_issuer()
    issuer.CN = 'Untrusted Authority'
    issuer.O = 'Self-Signed'
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 768)
    cert.set_pubkey(pkey)
    cert.sign(pkey, 'md5')
    ctx = SSL.Context(SSL.SSLv23_METHOD)
    ctx.use_privatekey(pkey)
    ctx.use_certificate(cert)
    return ctx


def is_ssl_error(error = None):
    """Checks if the given error (or the current one) is an SSL error."""
    if error is None:
        error = sys.exc_info()[1]
    from OpenSSL import SSL
    return isinstance(error, SSL.Error)


class _SSLConnectionFix(object):
    """Wrapper around SSL connection to provide a working makefile()."""

    def __init__(self, con):
        self._con = con

    def makefile(self, mode, bufsize):
        return socket._fileobject(self._con, mode, bufsize)

    def __getattr__(self, attrib):
        return getattr(self._con, attrib)


def select_ip_version(host, port):
    """Returns AF_INET4 or AF_INET6 depending on where to connect to."""
    try:
        info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        if info:
            return info[0][0]
    except socket.gaierror:
        pass

    if ':' in host and hasattr(socket, 'AF_INET6'):
        return socket.AF_INET6
    return socket.AF_INET


class BaseWSGIServer(HTTPServer, object):
    """Simple single-threaded, single-process WSGI server."""
    multithread = False
    multiprocess = False

    def __init__(self, host, port, app, handler = None, passthrough_errors = False, ssl_context = None):
        if handler is None:
            handler = WSGIRequestHandler
        self.address_family = select_ip_version(host, port)
        HTTPServer.__init__(self, (host, int(port)), handler)
        self.app = app
        self.passthrough_errors = passthrough_errors
        if ssl_context is not None:
            try:
                from OpenSSL import tsafe
            except ImportError:
                raise TypeError('SSL is not available if the OpenSSL library is not installed.')

            if ssl_context == 'adhoc':
                ssl_context = generate_adhoc_ssl_context()
            self.socket = tsafe.Connection(ssl_context, self.socket)
            self.ssl_context = ssl_context
        else:
            self.ssl_context = None

    def log(self, type, message, *args):
        _log(type, message, *args)

    def serve_forever(self):
        try:
            HTTPServer.serve_forever(self)
        except KeyboardInterrupt:
            pass

    def handle_error(self, request, client_address):
        if self.passthrough_errors:
            raise
        else:
            return HTTPServer.handle_error(self, request, client_address)

    def get_request(self):
        con, info = self.socket.accept()
        if self.ssl_context is not None:
            con = _SSLConnectionFix(con)
        return (con, info)


class ThreadedWSGIServer(ThreadingMixIn, BaseWSGIServer):
    """A WSGI server that does threading."""
    multithread = True


class ForkingWSGIServer(ForkingMixIn, BaseWSGIServer):
    """A WSGI server that does forking."""
    multiprocess = True

    def __init__(self, host, port, app, processes = 40, handler = None, passthrough_errors = False, ssl_context = None):
        BaseWSGIServer.__init__(self, host, port, app, handler, passthrough_errors, ssl_context)
        self.max_children = processes


def make_server(host, port, app = None, threaded = False, processes = 1, request_handler = None, passthrough_errors = False, ssl_context = None):
    """Create a new server instance that is either threaded, or forks
    or just processes one request after another.
    """
    if threaded and processes > 1:
        raise ValueError('cannot have a multithreaded and multi process server.')
    else:
        if threaded:
            return ThreadedWSGIServer(host, port, app, request_handler, passthrough_errors, ssl_context)
        if processes > 1:
            return ForkingWSGIServer(host, port, app, processes, request_handler, passthrough_errors, ssl_context)
        return BaseWSGIServer(host, port, app, request_handler, passthrough_errors, ssl_context)


def reloader_loop(extra_files = None, interval = 1):
    """When this function is run from the main thread, it will force other
    threads to exit when any modules currently loaded change.
    
    Copyright notice.  This function is based on the autoreload.py from
    the CherryPy trac which originated from WSGIKit which is now dead.
    
    :param extra_files: a list of additional files it should watch.
    """

    def iter_module_files():
        for module in sys.modules.values():
            filename = getattr(module, '__file__', None)
            if filename:
                old = None
                while not os.path.isfile(filename):
                    old = filename
                    filename = os.path.dirname(filename)
                    if filename == old:
                        break
                else:
                    if filename[-4:] in ('.pyc', '.pyo'):
                        filename = filename[:-1]
                    yield filename

    mtimes = {}
    while 1:
        for filename in chain(iter_module_files(), extra_files or ()):
            try:
                mtime = os.stat(filename).st_mtime
            except OSError:
                continue

            old_time = mtimes.get(filename)
            if old_time is None:
                mtimes[filename] = mtime
                continue
            elif mtime > old_time:
                _log('info', ' * Detected change in %r, reloading' % filename)
                sys.exit(3)

        time.sleep(interval)


def restart_with_reloader():
    """Spawn a new Python interpreter with the same arguments as this one,
    but running the reloader thread.
    """
    while 1:
        _log('info', ' * Restarting with reloader...')
        args = [sys.executable] + sys.argv
        new_environ = os.environ.copy()
        new_environ['WERKZEUG_RUN_MAIN'] = 'true'
        if os.name == 'nt':
            for key, value in new_environ.iteritems():
                if isinstance(value, unicode):
                    new_environ[key] = value.encode('iso-8859-1')

        exit_code = subprocess.call(args, env=new_environ)
        if exit_code != 3:
            return exit_code


def run_with_reloader(main_func, extra_files = None, interval = 1):
    """Run the given function in an independent python interpreter."""
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        thread.start_new_thread(main_func, ())
        try:
            reloader_loop(extra_files, interval)
        except KeyboardInterrupt:
            return

    try:
        sys.exit(restart_with_reloader())
    except KeyboardInterrupt:
        pass


def run_simple(hostname, port, application, use_reloader = False, use_debugger = False, use_evalex = True, extra_files = None, reloader_interval = 1, threaded = False, processes = 1, request_handler = None, static_files = None, passthrough_errors = False, ssl_context = None):
    """Start an application using wsgiref and with an optional reloader.  This
    wraps `wsgiref` to fix the wrong default reporting of the multithreaded
    WSGI variable and adds optional multithreading and fork support.
    
    .. versionadded:: 0.5
       `static_files` was added to simplify serving of static files as well
       as `passthrough_errors`.
    
    .. versionadded:: 0.6
       support for SSL was added.
    
    :param hostname: The host for the application.  eg: ``'localhost'``
    :param port: The port for the server.  eg: ``8080``
    :param application: the WSGI application to execute
    :param use_reloader: should the server automatically restart the python
                         process if modules were changed?
    :param use_debugger: should the werkzeug debugging system be used?
    :param use_evalex: should the exception evaluation feature be enabled?
    :param extra_files: a list of files the reloader should watch
                        additionally to the modules.  For example configuration
                        files.
    :param reloader_interval: the interval for the reloader in seconds.
    :param threaded: should the process handle each request in a separate
                     thread?
    :param processes: number of processes to spawn.
    :param request_handler: optional parameter that can be used to replace
                            the default one.  You can use this to replace it
                            with a different
                            :class:`~BaseHTTPServer.BaseHTTPRequestHandler`
                            subclass.
    :param static_files: a dict of paths for static files.  This works exactly
                         like :class:`SharedDataMiddleware`, it's actually
                         just wrapping the application in that middleware before
                         serving.
    :param passthrough_errors: set this to `True` to disable the error catching.
                               This means that the server will die on errors but
                               it can be useful to hook debuggers in (pdb etc.)
    :param ssl_context: an SSL context for the connection. Either an OpenSSL
                        context, the string ``'adhoc'`` if the server should
                        automatically create one, or `None` to disable SSL
                        (which is the default).
    """
    if use_debugger:
        from werkzeug.debug import DebuggedApplication
        application = DebuggedApplication(application, use_evalex)
    if static_files:
        from werkzeug.wsgi import SharedDataMiddleware
        application = SharedDataMiddleware(application, static_files)

    def inner():
        make_server(hostname, port, application, threaded, processes, request_handler, passthrough_errors, ssl_context).serve_forever()

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        display_hostname = hostname != '*' and hostname or 'localhost'
        if ':' in display_hostname:
            display_hostname = '[%s]' % display_hostname
        _log('info', ' * Running on %s://%s:%d/', ssl_context is None and 'http' or 'https', display_hostname, port)
    if use_reloader:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_socket.bind((hostname, port))
        test_socket.close()
        run_with_reloader(inner, extra_files, reloader_interval)
    else:
        inner()
