"""
A script that pulls from the file `queries.txt` (by default) in the same
directory, which should be a file with one query per line. It then generates a
CSV file that can be imported into Anki.

At the moment, it's not written as an anki add-on that can add to existing cards
and should be used to generate notes from scratch.

Example usage:

    python3 reverso_note_maker.py -s ru
"""
from typing import Generator
from optparse import OptionParser
from reverso_api import context
from itertools import islice
import formatting
import os
import time
import progress.bar
import requests.exceptions
from collections import namedtuple
import csv
import logging
from api_helpers import get_highlighted, make_cloze

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Maximum number of examples to pull from Reverso.
MAX_EXAMPLES = 3

# Number of examples to ask for when using prefer_short option. As the API
# provides a generator, we ask for a reasonable amount by eyeballing the UI.
# Unfortunately, there's no easy way to ask for "just one page" using the API
# library, but this should add a ceiling to the request time.
PREFER_SHORT_MAX_EXAMPLES = 15

# Maximum number of frequencies ("translations" in library) to fetch.
MAX_FREQUENCIES = 5
# Reverso can start giving really weird frequencies. This cuts out any
# frequencies relative to n * the highest frequency word. For example, if it's
# 0.1, you can think that this means that any translation appearing < 10%
# relative to the most common translation can be ignored.
FREQUENCY_THRESHOLD = 0.1

MAX_RETRIES = 5

# Wait this long between each request to prevent getting blocked by reverso.
SLEEP_THROTTLE_SEC = 1
RETRY_WAIT_SEC = 60

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
parser.add_option(
    "--prefer-short",
    action="store_true",
    dest="prefer_short",
    help="Sort example sentences by length, preferring shorter sentences",
    default=False)

parser.add_option(
    "--keep-punctuation",
    action="store_true",
    dest="keep_punctuation",
    help="By default, script removes non-apostrophe punctuation because it Reverso matches the punctuation and it usually leads to bad examples. This flag keeps all punctuation",
    default=False)


# frequencies is a (definition, count) pair that shows up at the top of the
# Reverso UI, indicating what the most frequent translation is
AnkiReversoNote = namedtuple(
    "AnkiReversoNote",
    ("query",
     "hints",
     "cloze_texts",
     "frequencies"))


def reverso_note_to_csv(note: AnkiReversoNote) -> list[str]:
    """
    Processes an AnkiReversoNote into a single row of CSV output.

    See the README for an example of what this output would look like.
    """
    # Format: foo (0.5) where the number is the relative frequency to the most
    # common word. However, don't put any number next to the first word.
    freq_strs = []
    for i, f in enumerate(note.frequencies):
        if i == 0:
            freq_strs.append("<b>%s</b></br>" % f[0])
        else:
            highest_freq = note.frequencies[0][1]
            freq_strs.append("%s (%.2f)" % (f[0], f[1] / highest_freq))

    return [note.query, '\n\n'.join(note.cloze_texts),
            ' | '.join(note.hints),
            # First one gets its own line, so no semicolon after it.
            freq_strs[0] + '; '.join(freq_strs[1:]) if freq_strs else ''
            ]


def make_notes(queries, existing_notes, options) -> Generator[AnkiReversoNote,
                                                              None, None]:
    """
    Main function for generating notes
    """
    bar = progress.bar.Bar('Processing', max=len(queries))
    for q in queries:
        bar.next()
        if q in existing_notes:
            continue
        # We need to normalize because of this article:
        # https://www.ojisanseiuchi.com/2021/05/08/encoding-of-the-cyrillic-letter-%D0%B9-a-utf-8-gotcha/
        # It doesn't handle the character й well, treating it as и + diacritic in a
        # lot of cases.
        # TODO: Move this into some other function.
        normalized = q.strip().lower().replace(u"\u0438\u0306", u"\u0439")
        if not options.keep_punctuation:
            normalized = formatting.strip_punctuation(normalized)

        api = context.ReversoContextAPI(
            normalized,
            "",
            options.source_lang,
            options.target_lang)
        # Rate limit to prevent getting blocked by Reverso.
        time.sleep(SLEEP_THROTTLE_SEC)

        note = AnkiReversoNote(
            query=q,
            hints=[],
            cloze_texts=[],
            frequencies=[])

        num_retries = 0
        while num_retries < MAX_RETRIES:
            try:
                if num_retries == MAX_RETRIES:
                    raise Exception("Hit max number of retries.")
                translations = islice(
                    api.get_translations(), 0, MAX_FREQUENCIES)
                if options.prefer_short:
                    # Sort by the length of the sort text.
                    examples = list(islice(api.get_examples(),
                                           0,
                                           PREFER_SHORT_MAX_EXAMPLES))
                    examples.sort(key=lambda s: len(s[0].text))
                    examples = examples[:MAX_EXAMPLES]
                else:
                    examples = islice(api.get_examples(), 0, MAX_EXAMPLES)
                num_retries += 1
                break
            except requests.exceptions.ConnectionError:
                logger.warning("Encountered a connection error. Retrying...")
                time.sleep(RETRY_WAIT_SEC)

        # Handle frequencies.
        highest_freq = None
        for i, translation in enumerate(translations):
            if i == 0:
                highest_freq = translation.frequency
            if translation.frequency > highest_freq * FREQUENCY_THRESHOLD:
                note.frequencies.append(
                    (translation.translation, translation.frequency))

        # Handle examples.
        for source, target in examples:
            # Create the cloze part
            cloze = make_cloze(source.text, source.highlighted)
            note.cloze_texts.append(cloze)

            # Use the english translation in a list of hints. The hint won't be
            # colocated with the sentence but doesn't really matter.
            try:
                note.hints.append(
                    get_highlighted(
                        target.text,
                        target.highlighted))
            except BaseException:
                logger.warning('Hint failed on ' + q)

        # Columns: Term, cloze, hint
        if len(note.cloze_texts) != 0:
            yield note
        else:
            # Simply skip the word for now, oh well.
            logger.warning("Nothing found on Reverso: " + q)

    bar.finish()


(options, args) = parser.parse_args()
if not options.source_lang:
    parser.error('No source language given.')

# Mark the existing notes so that we can continue writing in case of large
# jobs.
existing_notes = set()

if os.path.isfile(options.output_file):
    with open(options.output_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            existing_notes.add(row[0])

with open(options.query_file, 'r') as f:
    queries = f.read().strip().split('\n')

with open(options.output_file, 'a', newline='') as csvfile:
    reversowriter = csv.writer(csvfile)
    # Write from the generator as we receive results so that progress can be
    # saved.
    for note in make_notes(queries, existing_notes, options):
        row = reverso_note_to_csv(note)
        reversowriter.writerow(row)
