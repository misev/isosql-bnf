# isosql-bnf

Scripts to work with the BNF grammar of ISO SQL.

## extract_bnf.sh

Extracts the bnf rules from the specified XML sources (DOCS variable in the script).
The results go to `bnf-<input_file>.xml`.

## combine_bnf.py

Combines the results from `extract_bnf.sh`, and allows to export the result in
several formats.

```bash
$ python combine_bnf.py -h`
usage: combine_bnf.py [-h] [-b] [-n] [-x] [-a] [-r] [-s] [-e] [-g] [-f FILTER]
                      FILE [FILE ...]

Convert multiple BNF XML files extracted from sql-*.xml into a single grammar.

positional arguments:
  FILE                  Input BNF XML file(s).

optional arguments:
  -h, --help            show this help message and exit
  -b, --bnfc-style      Generate LBNF grammar understood by BNFC
                        (http://bnfc.digitalgrammars.com/).
  -n, --bnf-style       Generate BNF grammar.
  -x, --ebnf-style      Generate EBNF grammar.
  -a, --antlr-style     Generate ANTLR4-compliant grammar.
  -r, --print-roots     Print grammar tree roots.
  -s, --no-semicolon    Do not end each production rule with a semicolon.
  -e, --no-empty-line   Do not separate BNF rules by an empty line.
  -g, --no-serialize    Do not serialize the grammar to std out.
  -f FILTER, --filter FILTER
                        Serialize only the tree starting with the given root
                        (expects rule name without enclosing '<' and '>').
```
