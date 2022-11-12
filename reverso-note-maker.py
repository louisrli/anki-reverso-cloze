"""
A script that pulls from the file `queries.txt` (by default) in the same
directory, which should be a file with one query per line. It then generates a
CSV file that can be imported into Anki.

At the moment, it's not written as an anki add-on that can add to existing cards
and should be used to generate notes from scratch.

Example usage:

    python3 reverso-note-maker.py -s ru
"""
from optparse import OptionParser
from reverso_api import context
from itertools import islice
import time
import progress.bar
from collections import namedtuple
import csv
import logging

logger = logging.getLogger(__name__)

# Maximum number of examples to pull from Reverso.
MAX_EXAMPLES = 3
MAX_FREQUENCIES = 5

# Wait this long between each request to prevent getting blocked by reverso.
SLEEP_THROTTLE_SEC = 1

parser = OptionParser()
parser.add_option("-s", "--sourcelang", dest="source_lang",
                  help="Source language code of words to read.")
parser.add_option("-t", "--target_lang", dest="target_lang",
                  help="Target language code.",
                  default="en")
parser.add_option("-q", "--queries", dest="query_file",
                  help="Path to queries file", default="queries.txt")
parser.add_option("-o", "--output", dest="output_file",
                  help="Path to output file", default="reverso.csv")


def get_highlighted(text, highlighted):
    """
    Given `highlighted`, which is a list of pair of indexes, return the first
    highlighted string in the Reverso sentence
    """
    start = highlighted[0][0]
    end = highlighted[0][1]
    return text[start:end]


def make_cloze(text, highlighted):
    """
    Takes the a string and a pair of numbers and clozes the parts of the string
    between the given indices.
    """
    start = highlighted[0][0]
    end = highlighted[0][1]
    prefix = text[:start]
    highlighted = text[start:end]
    suffix = text[end:]
    return "%s{{c1::%s}}%s" % (prefix, highlighted, suffix)


# frequencies is a (definition, count) pair that shows up at the top of the
# Reverso UI, indicating what the most frequent translation is
AnkiReversoNote = namedtuple(
    "AnkiReversoNote",
    ("query",
     "hints",
     "cloze_texts",
     "frequencies"))


def reverso_note_to_csv(notes):
    """
    Processes AnkiReversoNotes into an array of array of strings that can easily
    be written to CSV.
    """
    results = []
    for note in notes:
        # Format: foo (123)
        freq_strs = ["%s (%d)" % (f[0], f[1]) for f in note.frequencies]
        results.append([note.query, '\n\n'.join(note.cloze_texts),
                        ' | '.join(note.hints),
                        ', '.join(freq_strs)
                        ])
    return results


(options, args) = parser.parse_args()

with open(options.query_file, 'r') as f:
    queries = f.read().strip().split('\n')

results = []
bar = progress.bar.Bar('Processing', max=len(queries))
for q in queries:
    bar.next()
    # We need to normalize because of this article:
    # https://www.ojisanseiuchi.com/2021/05/08/encoding-of-the-cyrillic-letter-%D0%B9-a-utf-8-gotcha/
    # It doesn't handle the character й well, treating it as и + diacritic in a
    # lot of cases.
    # TODO: Move this into some other function.
    normalized = q.strip().lower().replace(u"\u0438\u0306", u"\u0439")

    api = context.ReversoContextAPI(
        normalized,
        "",
        options.source_lang,
        options.target_lang)
    # Rate limit to prevent getting blocked by Reverso.
    time.sleep(SLEEP_THROTTLE_SEC)

    note = AnkiReversoNote(query=q, hints=[], cloze_texts=[], frequencies=[])

    # Handle frequencies.
    for translation in islice(api.get_translations(), 0, MAX_FREQUENCIES):
        note.frequencies.append((translation.translation,
            translation.frequency))

    # Handle examples.
    for source, target in islice(api.get_examples(), 0, MAX_EXAMPLES):
        # Create the cloze part
        cloze = make_cloze(source.text, source.highlighted)
        note.cloze_texts.append(cloze)

        # Use the english translation in a list of hints. The hint won't be
        # colocated with the sentence but doesn't really matter.
        try:
            note.hints.append(get_highlighted(target.text, target.highlighted))
        except BaseException:
            logger.warning('Hint failed on ' + q)

    # Columns: Term, cloze, hint
    if len(note.cloze_texts) != 0:
        results.append(note)
    else:
        # Simply skip the word for now, oh well.
        logger.warning("Nothing found on Reverso: " + q)

bar.finish()


as_columns = reverso_note_to_csv(results)
with open(options.output_file, 'w', newline='') as csvfile:
    reversowriter = csv.writer(csvfile)
    for row in as_columns:
        reversowriter.writerow(row)
