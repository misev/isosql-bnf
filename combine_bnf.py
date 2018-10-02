#!/usr/bin/env python
#
# Convert multiple BNF XML files extracted from sql-*.xml into a single grammar.
#
# Copyright (c) 2016 Dimitar Misev.
#

import sys
import argparse
import string
from lxml import etree
from lxml import objectify
from abc import ABCMeta, abstractmethod

OPT_SEMICOLON = False
OPT_BNFC_STYLE = False
OPT_EBNF_STYLE = False
OPT_ANTLR_STYLE = False
OPT_EMPTY_LINE = True
OPT_SERIALIZE = True
OPT_TREE_ROOTS = False
OPT_FILTER = None
OPT_CONVERT_TO_BNF = False

nonterminals = set()

alpha = 'abcdefghijklmnopqrstuvwxyz'.upper()

class GrammarObject(object):
    __metaclass__ = ABCMeta
    @abstractmethod
    def serialize(self):
        pass

    def simplify(self, grammar, nonterminal):
        pass

    def filter(self, cls):
        pass

    def collect(self, cls):
        if isinstance(self, cls):
            return [self]
        else:
            return []

    def collect_leafs(self, cls):
        return self.collect(cls)

class Symbol(GrammarObject):
    def __init__(self, name = ''):
        self.name = name

    def serialize(self):
        return self.name

    def __str__(self):
        return self.serialize()

class Terminal(Symbol):
    def serialize(self):
        res = self.name
        if OPT_ANTLR_STYLE or OPT_BNFC_STYLE:
            res = self.name
            if res == '\\':
                res = '\\\\'
            elif res == '\'':
                res = '\\\''
            elif res == '"':
                res = '\\"'
        if OPT_ANTLR_STYLE:
            res = "'" + res + "'"
        else:
            res = '"' + res + '"'
        return res

class Keyword(Terminal):
    pass

class Noop(Terminal):
    def serialize(self):
        return ''

class Nonterminal(Symbol):
    def __init__(self, name, production_rule = None):
        self.name = name
        self.production_rule = production_rule

    def serialize(self):
        if OPT_EBNF_STYLE:
            return self.name
        elif OPT_ANTLR_STYLE:
            return self.name.replace(' ', '_').replace('-', '_').replace('/', '').replace(':', '').lower()
        elif OPT_BNFC_STYLE:
            ret = self.name.replace('-', ' ').replace('/', '').replace(':', '').title().replace(' ', '')
            for i in range(len(ret)):
                c = ret[i]
                if c.isdigit():
                    ret = ret.replace(c, alpha[int(c)])
            return ret
        else:
            return '<' + self.name + '>'

    def __str__(self):
        return self.serialize()

    def simplify(self, grammar, nonterminal):
        if self.name in grammar.ast:
            self.production_rule = grammar.ast[self.name]
        else:
            print("Warning: non-terminal '" + self.name + "' has no production rule.")

class NonSymbol(GrammarObject):
    __metaclass__ = ABCMeta
    def __init__(self, children, separator, open_bracket = '', close_bracket = ''):
        if type(children) is not list:
            self.children = [children]
        else:
            self.children = children
        self.separator = separator
        self.open_bracket = open_bracket
        self.close_bracket = close_bracket

    def serialize(self):
        ret = self.open_bracket
        first = True
        for c in self.children:
            if not first:
                ret += self.separator
            first = False
            ret += c.serialize()
        ret += self.close_bracket
        return ret

    def __str__(self):
        ret = self.open_bracket
        first = True
        for c in self.children:
            if not first:
                ret += self.separator
            first = False
            ret += str(c)
        ret += self.close_bracket
        return ret

    def collect(self, cls):
        ret = super(NonSymbol, self).collect(cls)
        for c in self.children:
            ret.extend(c.collect(cls))
        return ret

    def collect_leafs(self, cls):
        ret = []
        for c in self.children:
            ret.extend(c.collect_leafs(cls))
        if len(ret) == 0:
            ret.extend(super(NonSymbol, self).collect_leafs(cls))
        return ret

    def simplify(self, grammar, nonterminal):
        delete = []
        for i, c in enumerate(self.children):
            if isinstance(c, ProductionRule):
                nonterminal = c.head.name

            if isinstance(c, Repetition):
                if OPT_BNF_STYLE:
                    new_rule = grammar.add_rule(nonterminal, 'seq', c.children)
                    self.children[i] = new_rule.head
                    if OPT_ANTLR_STYLE:
                        new_rule.children.append(new_rule.head)
                    else:
                        new_rule.children.insert(0, new_rule.head)
                    new_rule.children = [Sequence(new_rule.children)]
            elif isinstance(c, Group) and OPT_BNF_STYLE:
                new_rule = grammar.add_rule(nonterminal, 'group', c.children)
                self.children[i] = new_rule.head
            elif isinstance(c, Optional) and OPT_BNF_STYLE:
                new_rule = grammar.add_rule(nonterminal, 'opt', c.children)
                self.children[i] = new_rule.head
                new_rule.children.append(Terminal(''))
                new_rule.children = [Alternatives(new_rule.children)]
            elif isinstance(c, Terminal) and c.name == 'seeTheRules':
                if nonterminal == 'escaped character':
                    c.name = '\\'
                elif nonterminal == 'space':
                    c.name = ' '
                elif nonterminal == 'newline':
                    c.name = '\\n'
                elif nonterminal == 'white space':
                    self.children = [Terminal(' '), Terminal('\\n'), Terminal('\\t')] #, Terminal('\\r'), Terminal('\\v'), Terminal('\\f')]
                elif nonterminal == 'Unicode escape character':
                    c.name = 'U+'
                elif nonterminal == 'identifier start':
                    # todo revise
                    self.children = [Symbol('Ident')]
                elif nonterminal == 'identifier extend':
                    # todo fix
                    self.children = [Symbol('Ident')]
                elif nonterminal == 'nondoublequote character':
                    # any character except "
                    self.children = [Symbol('Char')]
                elif nonterminal == 'nonquote character':
                    # any character except ' or "
                    self.children = [Symbol('Char')]
                elif nonterminal == 'non-escaped character':
                    # any character except ' or "
                    self.children = [Symbol('Char')]
            else:
                c.simplify(grammar, nonterminal)

    def filter(self, ast):
        for i, c in enumerate(self.children):
            if isinstance(c, Nonterminal):
                if c.name not in ast:
                    if c.production_rule is None:
                        print("Warning: non-terminal '" + c.name + "' has no production rule.")
                    else:
                        ast[c.name] = c.production_rule
                        c.production_rule.filter(ast)
            elif isinstance(c, NonSymbol):
                c.filter(ast)


class Optional(NonSymbol):
    def __init__(self, children):
        if OPT_ANTLR_STYLE:
            super(Optional, self).__init__(children, ' ', '( ', ' )?')
        else:
            super(Optional, self).__init__(children, ' ', '[ ', ' ]')

class Group(NonSymbol):
    def __init__(self, children):
        if OPT_EBNF_STYLE or OPT_ANTLR_STYLE:
            super(Group, self).__init__(children, ' ', '( ', ' )')
        else:
            super(Group, self).__init__(children, ' ', '{ ', ' }')

class Alternatives(NonSymbol):
    def __init__(self, children):
        super(Alternatives, self).__init__(children, ' | ', '', '')

class Sequence(NonSymbol):
    def __init__(self, children):
        if OPT_EBNF_STYLE:
            super(Sequence, self).__init__(children, ', ', '', '')
        else:
            super(Sequence, self).__init__(children, ' ', '', '')

class Repetition(NonSymbol):
    def __init__(self, children):
        if OPT_EBNF_STYLE:
            super(Repetition, self).__init__(children, ' ', '{ ', ' }')
        elif OPT_ANTLR_STYLE:
            super(Repetition, self).__init__(children, ' ', '', '+')
        else:
            super(Repetition, self).__init__(children, ' ', '', ' ...')

class ProductionRule(NonSymbol):
    def __init__(self, head, children):
        super(ProductionRule, self).__init__(children, ' ', '', '')
        self.head = head
        self.rule_sep = ' ::= '
        if OPT_EBNF_STYLE:
            self.rule_sep = ' = '
        elif OPT_ANTLR_STYLE:
            self.rule_sep = ': '
        self.semicolon = ' ;'
        if not OPT_SEMICOLON:
            self.semicolon = ''

    def serialize(self):
        ret = ''
        first = True
        i = 0
        for c in self.children:
            if not first:
                ret += '\n'
            first = False
            label = ''
            if OPT_BNFC_STYLE:
                name = self.head.name
                while name in nonterminals:
                    name += ' A'
                tmp = i
                while tmp >= len(alpha):
                    name += ' A'
                    tmp -= len(alpha)
                name += alpha[tmp]
                name = Nonterminal(name).serialize()
                label = name + ' . '
            ret += label + self.head.serialize() + self.rule_sep + c.serialize() + self.semicolon
            i += 1
        return ret

class Grammar(NonSymbol):
    def __init__(self, ast):
        children = ast.values()
        separator = '\n'
        if OPT_EMPTY_LINE:
            separator = '\n\n'
        super(Grammar, self).__init__(children, separator, '', '')
        self.ast = ast

    def add_rule(self, rule_name, suffix, children):
        new_rule_name = rule_name + ' ' + suffix + ' '
        i = 0
        while (new_rule_name + alpha[i]) in self.ast:
            i += 1
        new_rule_name += alpha[i]
        new_rule = ProductionRule(Nonterminal(new_rule_name), children)
        new_rule.head.production_rule = new_rule
        self.ast[new_rule_name] = new_rule
        self.children.append(new_rule)
        return new_rule

    def print_tree_roots(self):
        for c in self.children:
            if c.head.name not in nonterminals:
                print("Grammar tree root: " + c.head.serialize())

    def serialize(self):
        ret = super(Grammar, self).serialize()
        if OPT_ANTLR_STYLE:
            ret = 'grammar SQLGrammar;\n\n' + ret
        if OPT_BNFC_STYLE:
            ret = 'entrypoints DirectSqlStatement ;\n\n' + ret
        return ret

    def filter(self, name):
        ret = None
        if name in self.ast:
            root_node = self.ast[name]
            new_ast = {}
            new_ast[name] = root_node
            root_node.filter(new_ast)
            ret = Grammar(new_ast)
        return ret

    def simplify(self):
        super(Grammar, self).simplify(self, None)

        if OPT_BNF_STYLE:
            for production_rule in self.children:
                alternatives = production_rule.collect_leafs(Alternatives)
                if len(alternatives) > 0:
                    #print("eliminating alternatives in production rule: " + production_rule.head.name)
                    new_children = []
                    for c in alternatives:
                        new_children.extend(c.children)
                    production_rule.children = new_children

def build_bnf_dict(files):
    """
    Parse the input XML files and build a dictionary of BNFdef -> BNF production rules.
    @param files a list of files. BNFdef elements are directly under the root element.
    @return a dictionary of BNFdef -> BNF production rules.
    """
    bnfdef_dict = {}
    for f in args.files:
        fileobj = open(f)
        tree = objectify.parse(f)
        root_el = tree.getroot()
        for bnfdef_el in root_el.BNFdef:
            bnfdef_name = bnfdef_el.get("name")

            prod_rules = [ el for el in bnfdef_el.rhs.iterchildren() ]
            if bnfdef_name in bnfdef_dict:
                bnfdef_dict[bnfdef_name].extend(prod_rules)
            else:
                bnfdef_dict[bnfdef_name] = prod_rules
    return bnfdef_dict

def convert_xml_to_ast(bnfdef_dict, xml_el):
    ret = None
    if isinstance(xml_el, str):
        if len(xml_el.strip()) > 0:
            ret = Terminal(xml_el.strip())
        else:
            ret = Noop()
    elif xml_el.tag == "BNF":
        rule_name = xml_el.get("name")
        nonterminals.add(rule_name)
        ret = Nonterminal(rule_name, None)
    elif xml_el.tag == "kw" or xml_el.tag == "sjkw" or xml_el.tag == "mono" or xml_el.tag == "sym":
        text = xml_el.text.strip()
        if len(text) > 0:
            ret = Keyword(text)
        else:
            ret = Noop()
    elif xml_el.tag == "terminalsymbol":
        ret = Terminal(xml_el.text.strip())
    elif xml_el.tag == "seeTheRules":
        ret = Terminal("seeTheRules")
    elif xml_el.tag == "ellipsis":
        ret = Repetition([])
    elif xml_el.tag == "opt":
        ret = Optional(convert_children_to_ast(bnfdef_dict, xml_el))
    elif xml_el.tag == "group":
        ret = Group(convert_children_to_ast(bnfdef_dict, xml_el))
    elif xml_el.tag == "alt" or xml_el.tag == "minialt":
        ret = Alternatives(Sequence(convert_children_to_ast(bnfdef_dict, xml_el)))
    else:
        ret = Terminal('')
    return ret

def remove_directly_contained_alt(ast_symbols):
    ret = []
    if isinstance(ast_symbols[0], Alternatives):
        for cit in ast_symbols:
            ret.extend(cit.children)
    return ret

def convert_children_to_ast(bnfdef_dict, xml_el):
    ret = []
    alternatives = False

    if not isinstance(xml_el, list) and xml_el.text is not None:
        ret.append(convert_xml_to_ast(bnfdef_dict, xml_el.text))

    xml_el_children = xml_el
    if not isinstance(xml_el, list):
        xml_el_children = xml_el.iterchildren()

    for c in xml_el_children:

        ast_symbol = convert_xml_to_ast(bnfdef_dict, c)

        if isinstance(ast_symbol, Alternatives):
            alternatives = True
            children = remove_directly_contained_alt(ast_symbol.children)
            if len(children) == 0:
                children = ast_symbol.children
            if len(children) > 1:
                children = [Sequence(children)]
            ret.extend(children)
        elif isinstance(ast_symbol, Repetition):
            ast_symbol.children = [ret.pop()]
            ret.append(ast_symbol)
        else:
            if alternatives:
                print("Warning: production rule for <" + bnfdef_name + "> contains mixed alt and non-alt symbols.")
            ret.append(ast_symbol)

        if c.tail is not None:
            ret.append(convert_xml_to_ast(bnfdef_dict, c.tail))

    if alternatives:
        ret = [Alternatives(ret)]
    elif len(ret) > 1:
        ret = [Sequence(ret)]

    return ret

def convert_rule_to_ast(bnfdef_dict, ast, bnfdef_name):
    if bnfdef_name in ast:
        return ast[bnfdef_name]
    ast_symbol = convert_children_to_ast(bnfdef_dict, bnfdef_dict[bnfdef_name])
    ast[bnfdef_name] = ProductionRule(Nonterminal(bnfdef_name), ast_symbol)

def convert_grammar_to_ast(bnfdef_dict):
    """
    Convert the BNFdef -> BNF production rules dictionary to a dictionary
    of GrammarObject.
    """
    ast = {}
    for bnfdef_name in bnfdef_dict.keys():
        if bnfdef_name not in ast:
            convert_rule_to_ast(bnfdef_dict, ast, bnfdef_name)
    grammar = Grammar(ast)
    grammar.simplify()
    return grammar

#
# main
#
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description =
        'Convert multiple BNF XML files extracted from sql-*.xml into a single grammar.')
    parser.add_argument("-b", "--bnfc-style", help="Generate LBNF grammar understood by BNFC "
        "(http://bnfc.digitalgrammars.com/).", action='store_true')
    parser.add_argument("-n", "--bnf-style", help="Generate BNF grammar.", action='store_true')
    parser.add_argument("-x", "--ebnf-style", help="Generate EBNF grammar.", action='store_true')
    parser.add_argument("-a", "--antlr-style", help="Generate ANTLR4-compliant grammar.", action='store_true')
    parser.add_argument("-r", "--print-roots", help="Print grammar tree roots.", action='store_true')
    parser.add_argument("-s", "--no-semicolon", help="Do not end each production rule with a semicolon.", action='store_false')
    parser.add_argument("-e", "--no-empty-line", help="Do not separate BNF rules by an empty line.", action='store_false')
    parser.add_argument("-g", "--no-serialize", help="Do not serialize the grammar to std out.", action='store_false')
    parser.add_argument("-f", "--filter", help="Serialize only the tree starting with the given root "
        "(expects rule name without enclosing '<' and '>').", default=None)
    parser.add_argument("files", metavar="FILE", nargs='+', help="Input BNF XML file(s).")

    args = parser.parse_args()
    OPT_BNFC_STYLE = args.bnfc_style
    OPT_BNF_STYLE = args.bnf_style
    OPT_SEMICOLON = args.no_semicolon
    OPT_EMPTY_LINE = args.no_empty_line
    OPT_SERIALIZE = args.no_serialize
    OPT_EBNF_STYLE = args.ebnf_style
    OPT_ANTLR_STYLE = args.antlr_style
    OPT_TREE_ROOTS = args.print_roots
    OPT_FILTER = args.filter

    if OPT_EBNF_STYLE or OPT_ANTLR_STYLE or OPT_BNFC_STYLE:
        OPT_SEMICOLON = True
        OPT_EMPTY_LINE = True

    if OPT_BNFC_STYLE:
        OPT_BNF_STYLE = True

    bnfdef_dict = build_bnf_dict(args.files)
    grammar = convert_grammar_to_ast(bnfdef_dict)

    if OPT_TREE_ROOTS:
        grammar.print_tree_roots()

    if OPT_SERIALIZE:
        if OPT_FILTER is not None:
            root_node = grammar.filter(OPT_FILTER)
            if root_node is not None:
                print(root_node.serialize())
            else:
                print("Error: symbol '" + OPT_FILTER + "' not found.")
        else:
            print(grammar.serialize())
