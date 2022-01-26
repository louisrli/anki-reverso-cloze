#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from reverso_api import context
from itertools import islice
import csv

MAX_EXAMPLES = 2

def make_cloze(text, highlighted):
  """Takes the a string and a pair of numbers and clozes
  the parts of the string between the numbers."""
  start = highlighted[0][0]
  end = highlighted[0][1]
  prefix = text[:start]
  highlighted = text[start:end]
  suffix = text[end:]
  return "%s{{c1::%s}}%s" % (prefix, highlighted, suffix)

with open('words.txt', 'r') as f:
  words = f.read().strip().split('\n')

results = []
for w in words:
  api = context.ReversoContextAPI(
    w,
    "",
    "ru",
    "en")
  clozes = []
  for source, target in islice(api.get_examples(), 0, MAX_EXAMPLES):
    cloze = make_cloze(source.text, source.highlighted)
    clozes.append(cloze)
  # Term, cloze
  if len(clozes) != 0:
    results.append([w, '\n'.join(clozes)])
  else:
    print("Reverso miss: " + w)

with open('reverso.csv', 'w', newline='') as csvfile:
    reversowriter = csv.writer(csvfile)
    for row in results:
      reversowriter.writerow(row)

