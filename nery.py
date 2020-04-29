#!/usr/bin/env python3

"""nery, a simple REST receiver designed to process fragalysis-neo queries.
"""

import logging
import os

from flask import Flask, abort, request

APP = Flask(__name__)
# Disable distracting logging...
LOG = logging.getLogger('werkzeug')
LOG.disabled = True
APP.logger.disabled = True

_LOGGER = logging.getLogger('nery')

_DUMP_MESSAGES = os.environ.get('DUMP_MESSAGES', 'no')


@APP.route('/find-double-edge', methods=['GET'])
def find_double_edge():
    if not request.json:
        # Bad request
        abort(400)
    elif _DUMP_MESSAGES.lower() in ['yes']:
        _dump_message(request)


@APP.route('/find-triple-edge-growth', methods=['GET'])
def find_triple_edge_growth():
    if not request.json:
        # Bad request
        abort(400)
    elif _DUMP_MESSAGES.lower() in ['yes']:
        _dump_message(request)


@APP.route('/add-follow-ups', methods=['GET'])
def add_follow_ups():
    if not request.json:
        # Bad request
        abort(400)
    elif _DUMP_MESSAGES.lower() in ['yes']:
        _dump_message(request)


def _dump_message(request):
    """Prints the message request header and json body
    """

    # Beautify the message.
    #
    # Print a clear banner...
    print('- header -')
    _dump(request.headers)
    # Do we have a list of json structures or just one?
    if isinstance(request.json, list):
        print('- json (list) -')
        for json_block in request.json:
            _dump(json_block)
    else:
        print('- json -')
        _dump(request.json)


def _dump(key_val_block):
    """Prints what is expected to be a dictionary.
    """
    # ...and then format the payload
    # with neatly aligned keys and values.
    # Find the length of the longest key...
    max_key_length = 0
    for key in key_val_block:
        this_key_length = len(key)
        if this_key_length > max_key_length:
            max_key_length = this_key_length
    # Print...
    if max_key_length:
        for item in sorted(key_val_block.items()):
            padding = max_key_length - len(item[0])
            print(' {}{}: {}'.format(padding * ' ', item[0], item[1]))
