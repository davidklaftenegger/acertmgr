#!/usr/bin/env python
# -*- coding: utf-8 -*-

# standalone - standalone ACME challenge webserver
# Copyright (c) Markus Hauschild & David Klaftenegger, 2016.
# Copyright (c) Rudolf Mayerhofer, 2019.
# available under the ISC license, see LICENSE

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler

import datetime
import re
import socket
import threading

from acertmgr.modes.abstract import AbstractChallengeHandler

HTTPServer.allow_reuse_address = True


class HTTPServer6(HTTPServer):
    address_family = socket.AF_INET6


class ChallengeHandler(AbstractChallengeHandler):
    def __init__(self, config):
        AbstractChallengeHandler.__init__(self, config)
        bind_address = config.get("bind_address", "")
        port = int(config.get("port", 80))

        self.challenges = {}  # Initialize the challenge data dict
        _self = self

        # Custom HTTP request handler
        class _HTTPRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                print("Request from '%s': %s" % (self.address_string(), fmt % args))

            def do_GET(self):
                # Match token on http://<domain>/.well-known/acme-challenge/<token>
                match = re.match(r'.*/(?P<token>[^/]*)$', self.path)
                if match and match.group('token') in _self.challenges:
                    value = _self.challenges[match.group('token')].encode('utf-8')
                    rcode = 200
                else:
                    value = "404 - NOT FOUND".encode('utf-8')
                    rcode = 404
                self.send_response(rcode)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Content-length', len(value))
                self.end_headers()
                self.wfile.write(value)

        self.server_thread = None
        try:
            self.server = HTTPServer6((bind_address, port), _HTTPRequestHandler)
        except socket.gaierror:
            self.server = HTTPServer((bind_address, port), _HTTPRequestHandler)

    @staticmethod
    def get_challenge_type():
        return "http-01"

    def create_challenge(self, domain, thumbprint, token):
        self.challenges[token] = "{0}.{1}".format(token, thumbprint)
        return datetime.datetime.now()

    def destroy_challenge(self, domain, thumbprint, token):
        del self.challenges[token]

    def start_challenge(self):
        def _():
            self.server.serve_forever()

        self.server_thread = threading.Thread(target=_)
        self.server_thread.start()

    def stop_challenge(self):
        self.server.shutdown()
        self.server_thread.join()
