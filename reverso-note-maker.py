#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from reverso_api import context
from itertools import islice
import csv

MAX_EXAMPLES = 3

def get_highlighted(text, highlighted):
  """Given `highlighted`, which is a list of pair of indexes, return the first
  highlighted string in the Reverso sentence"""
  start = highlighted[0][0]
  end = highlighted[0][1]
  return text[start:end]

def make_cloze(text, highlighted):
  """Takes the a string and a pair of numbers and clozes
  the parts of the string between the numbers."""
  start = highlighted[0][0]
  end = highlighted[0][1]
  prefix = text[:start]
  highlighted = text[start:end]
  suffix = text[end:]
  return "%s{{c1::%s}}%s" % (prefix, highlighted, suffix)

def sort_by_length(sentences):
  """Sorts a list of strings by length asc"""
  return sorted(sentences, lambda x: len(x))

with open('words.txt', 'r') as f:
  words = f.read().strip().split('\n')

results = []
for w in words:
  api = context.ReversoContextAPI(
    w.strip(),
    "",
    "ru",
    "en")
  clozes = []
  hints = []
  for source, target in islice(api.get_examples(), 0, MAX_EXAMPLES):
    # Create the cloze part
    cloze = make_cloze(source.text, source.highlighted)
    clozes.append(cloze)

    # Use the english translation in a list of hints. The hint won't be
    # colocated with the sentence but doesn't really matter.
    hints.append(get_highlighted(target.text, target.highlighted))

  # Columns: Term, cloze, hint
  if len(clozes) != 0:
    results.append([w, '\n\n'.join(clozes), ' | '.join(hints)])
  else:
    # Simply skip the word for now, oh well.
    print("Nothing found on Reverso: " + w)

with open('reverso.csv', 'w', newline='') as csvfile:
    reversowriter = csv.writer(csvfile)
    for row in results:
      reversowriter.writerow(row)

