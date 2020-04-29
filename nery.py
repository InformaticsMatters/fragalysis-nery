#!/usr/bin/env python3

"""nery - a simple REST receiver designed to process fragalysis neo4j queries.
"""

import logging
import os
import random

from flask import Flask, abort, request
from neo4j.v1 import GraphDatabase

APP = Flask(__name__)
# Disable distracting logging...
LOG = logging.getLogger('werkzeug')
LOG.disabled = True
APP.logger.disabled = True

_LOGGER = logging.getLogger('nery')

_DUMP_MESSAGES = os.environ.get('DUMP_MESSAGES', 'no')
_NEO4J_QUERY = os.environ.get('NEO4J_QUERY', 'neo4j')
_NEO4J_AUTH = os.environ.get('NEO4J_AUTH', 'neo4j/neo4j')


class ReturnObject(object):

    def __init__(self,
                 start_smi,
                 end_smi,
                 label,
                 edge_count,
                 change_frag,
                 iso_label):
        self.start_smi = start_smi
        self.end_smi = end_smi
        self.label = label
        self.iso_label = iso_label
        self.frag_type = None
        self.edge_count = edge_count
        self.change_frag = change_frag

    def __str__(self):
        out_list = [self.label, str(self.edge_count), self.frag_type]
        return "_".join(out_list)


@APP.route('/get-full-graph', methods=['GET'])
def get_full_graph():
    """Expects 'canon_smiles' (string) value in the JSON block.
    """

    if not request.json:
        # Bad request
        abort(400)
    elif _DUMP_MESSAGES.lower() in ['yes']:
        _dump_message(request)

    data = request.get_json()
    smiles = data.get('canon_smiles', '')
    _LOGGER.info("smiles=%s", smiles)

    if not smiles:
        _LOGGER.error('Empty SMILES')
        abort(400)

    driver = _get_driver()
    records = []
    with driver.session() as session:
        for record in session.read_transaction(_find_proximal, smiles):
            ans = _define_proximal_type(record)
            records.append(ans)
        for record in session.read_transaction(_find_double_edge, smiles):
            ans = _define_double_edge_type(record)
            records.append(ans)
        for label in list(set([x.label for x in records])):
            # Linkers are meaningless
            if "." in label:
                continue

    if records:
        _LOGGER.info("len(records)=%s", len(records))
        return _organise(records, None)
    else:
        _LOGGER.warning("Nothing found for input: %s", smiles)


def _find_proximal(tx, input_str):

    return tx.run(
        "match p = (n:F2{smiles:$smiles})-[nm]-(m:Mol) "
        "where abs(n.hac-m.hac) <= 3 and abs(n.chac-m.chac) <= 1 "
        "return n, nm, m "
        "order by split(nm.label, '|')[4];",
        smiles=input_str)


def _find_double_edge(tx, input_str):

    return tx.run(
        "match (sta:F2 {smiles:$smiles})-[nm:FRAG]-(mid:F2)-[ne:FRAG]-(end:Mol) "
        "where abs(sta.hac-end.hac) <= 3 and abs(sta.chac-end.chac) <= 1 "
        "and sta.smiles <> end.smiles "
        "return sta, nm, mid, ne, end "
        "order by split(nm.label, '|')[4], split(ne.label, '|')[2];",
        smiles=input_str)


def _define_proximal_type(record):

    mol_one = record["n"]
    label = str(record["nm"]["label"].split("|")[4])
    iso_label = str(record["nm"]["label"].split("|")[5])
    change_frag = str(record["nm"]["label"].split("|")[2])
    mol_two = record["m"]
    ret_obj = ReturnObject(
        mol_one["smiles"], mol_two["smiles"], label, 1, change_frag, iso_label
    )
    if "." in label:
        ret_obj.frag_type = "LINKER"
    elif mol_one["hac"] - mol_two["hac"] > 0:
        ret_obj.frag_type = "DELETION"
    elif mol_one["hac"] - mol_two["hac"] < 0:
        ret_obj.frag_type = "ADDITION"
    else:
        ret_obj.frag_type = "REPLACE"
    return ret_obj


def _define_double_edge_type(record):

    mol_one = record["sta"]
    label = str(record["ne"]["label"].split("|")[4])
    iso_label = str(record["ne"]["label"].split("|")[5])
    change_frag = str(record["ne"]["label"].split("|")[2])
    mol_two = record["mid"]
    mol_three = record["end"]
    diff_one = mol_one["hac"] - mol_two["hac"]
    diff_two = mol_two["hac"] - mol_three["hac"]
    ret_obj = ReturnObject(
        mol_one["smiles"], mol_three["smiles"], label, 2, change_frag, iso_label
    )
    if "." in label:
        ret_obj.frag_type = "LINKER"
    elif diff_one >= 0 and diff_two >= 0:
        ret_obj.frag_type = "DELETION"
    elif diff_one <= 0 and diff_two <= 0:
        ret_obj.frag_type = "ADDITION"
    else:
        ret_obj.frag_type = "REPLACE"
    return ret_obj


def _organise(records, num_picks):

    out_d = {}
    smi_set = set()
    for rec in records:
        rec_key = str(rec)
        addition = {"change": rec.change_frag, "end": rec.end_smi}
        if rec_key in out_d:
            out_d[rec_key]["addition"].append(addition)
        else:
            out_d[rec_key] = {"vector": rec.iso_label, "addition": [addition]}
        smi_set.add(rec.end_smi)
    if num_picks:
        max_per_hypothesis = num_picks / len(out_d)
    out_smi = []
    for rec in out_d:
        # TODO here is the logic as to ordering replacements
        if num_picks:
            random.shuffle(out_d[rec]["addition"])
            out_d[rec]["addition"] = out_d[rec]["addition"][:max_per_hypothesis]
        else:
            out_d[rec]["addition"] = out_d[rec]["addition"]
        out_smi.extend(out_d[rec])
    return out_d


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


def _get_driver():
    """Get the driver to the network connection using the bolt service
    at the URI provided. If an authentication string is provided
    (i.e. a typical NEO4J_AUTH value of <username>/<password>) then
    authentication is assumed.
    :return: the driver for the graph database
    """
    _LOGGER.info('Getting driver for %s (%s)...', _NEO4J_QUERY, _NEO4J_AUTH)
    auth_parts = _NEO4J_AUTH.split('/')
    if len(auth_parts) == 2:
        driver = GraphDatabase.driver('bolt://' + _NEO4J_QUERY + ':7687',
                                      auth=(auth_parts[0], auth_parts[1]))
    else:
        driver = GraphDatabase.driver('bolt://' + _NEO4J_QUERY + ':7687')

    return driver
