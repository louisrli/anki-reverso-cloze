#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from reverso_api import context
from itertools import islice
import time
import csv

# Change these constants if needed.

# Maximum number of examples to pull from Reverso.
MAX_EXAMPLES = 3

# Path to output file.
OUTPUT_PATH = 'reverso.csv'

INPUT_LANG = 'ru'
OUTPUT_LANG = 'en'

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
  # Rate limit to prevent getting blocked by Reverso.
  time.sleep(1)
  clozes = []
  hints = []
  for source, target in islice(api.get_examples(), 0, MAX_EXAMPLES):
    # Create the cloze part
    cloze = make_cloze(source.text, source.highlighted)
    clozes.append(cloze)

    # Use the english translation in a list of hints. The hint won't be
    # colocated with the sentence but doesn't really matter.
    try:
      hints.append(get_highlighted(target.text, target.highlighted))
    except:
      print('Hint failed on ' + w)

  # Columns: Term, cloze, hint
  if len(clozes) != 0:
    results.append([w, '\n\n'.join(clozes), ' | '.join(hints)])
  else:
    # Simply skip the word for now, oh well.
    print("Nothing found on Reverso: " + w)

with open(OUTPUT_PATH, 'w', newline='') as csvfile:
    reversowriter = csv.writer(csvfile)
    for row in results:
      reversowriter.writerow(row)

