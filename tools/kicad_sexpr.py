"""Small lossless-token KiCad S-expression reader used by the CAD generators."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path


class Atom(str):
    pass


def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack, result = [], None
    for token in tokens:
        if token == '(':
            node = []
            if stack:
                stack[-1].append(node)
            else:
                result = node
            stack.append(node)
        elif token == ')':
            stack.pop()
        elif token.startswith('"'):
            stack[-1].append(json.loads(token))
        else:
            stack[-1].append(Atom(token))
    assert not stack
    return result


def read(path):
    return parse(Path(path).read_text(encoding='utf-8-sig'))


def children(node, key):
    return [n for n in node if isinstance(n, list) and n and n[0] == key]


def child(node, key, default=None):
    return next(iter(children(node, key)), default)


def prop(node, name, default=''):
    return next((n[2] for n in children(node, 'property') if n[1] == name), default)


def dumps(node, level=0):
    if isinstance(node, Atom):
        return str(node)
    if not isinstance(node, list):
        if isinstance(node, str):
            return json.dumps(node, ensure_ascii=False)
        return str(node)
    if not any(isinstance(v, list) for v in node):
        return '(' + ' '.join(dumps(v) for v in node) + ')'
    out = '(' + dumps(node[0])
    for item in node[1:]:
        if isinstance(item, list):
            out += '\n' + '\t' * (level + 1) + dumps(item, level + 1)
        else:
            out += ' ' + dumps(item)
    return out + '\n' + '\t' * level + ')'


def symbol_from_library(library, name):
    syms = {n[1]: n for n in children(library, 'symbol')}

    def resolve(key):
        sym = copy.deepcopy(syms[key])
        ext = child(sym, 'extends')
        if ext:
            base = resolve(ext[1])
            replacements = {p[1] for p in children(sym, 'property')}
            sym.remove(ext)
            for item in base[2:]:
                if item[0] == 'property' and item[1] in replacements:
                    continue
                if item[0] == 'symbol':
                    item[1] = name + item[1][item[1].rfind('_', 0, item[1].rfind('_')):]
                sym.append(item)
        return sym

    return resolve(name)


if __name__ == '__main__':
    import sys
    doc = read(sys.argv[1])
    libs = child(doc, 'lib_symbols')
    if libs:
        for sym in children(libs, 'symbol'):
            print(sym[1], [(child(p,'number')[1], child(p,'name')[1], child(p,'at')[1:])
                  for unit in children(sym,'symbol') for p in children(unit,'pin')])
        print('INSTANCES')
        for sym in children(doc, 'symbol'):
            if not prop(sym, 'Reference').startswith('#'):
                print(prop(sym, 'Reference'), child(sym, 'lib_id')[1], child(sym, 'at')[1:])
