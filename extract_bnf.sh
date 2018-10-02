#!/bin/bash
#
# Copyright (c) 2016 Dimitar Misev

DOCS="sql-foundation.xml sql-mda.xml"

for f in $DOCS; do
  # remove these entities, otherwise xmlstarlet complains
  sed 's/&doc.*;//g' "$f" | \
  # fix duplicate id in foundation
  sed '0,/fnd_routines_characteristics_para_ir_invoke/s/fnd_routines_characteristics_para_ir_invoke/fnd_routines_characteristics_para_ir_invoke_2/' | \
  # select the BNFdef elements only
  xmlstarlet sel -t -c '//BNFdef' | \
  # wrap in root element
  sed '1i <root>' | sed '$a </root>' | \
  # remove comments and blank lines
  xmlstarlet ed -d '//comment' -d '//blankline' -d '//breakindent' -d '//linebreak' -d '//bar' -d '//endbar' | \
  # remove instructions, e.g.
  #  <alt>
  #      <emph>!! All alternatives from ISO/IEC 9075-2</emph>
  #  </alt>
  xmlstarlet ed -d '//alt/emph[contains(text(),"!! All")]/..' -d '//alt[contains(text(),"!! All")]' | \
  # format with 2 spaces indentation
  xmlstarlet fo -s 2 > "bnf-$f"
done
