"""
Helper functions relating to parsing the API output.
"""

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



