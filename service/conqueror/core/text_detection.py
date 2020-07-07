"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import re
from .base import StatefulObject


class TextExtractor(StatefulObject):
    def __init__(self, min_length=5, gather=5, processor=None):
        self.min_length = min_length
        self.gather = gather
        self.processor = processor

    def has_exception(self, some_text):
        some_text = some_text.lower().strip()
        ret, has_any_matches = self.processor.has_match(some_text)
        print(ret)
        print(has_any_matches)
        return ret, has_any_matches

    def extract_address(self, some_text):
        address_matcher = re.compile(r'[a-zA-Z0-9\-\.\?&:\/=%]+?')
        address_partials = [
            re.compile(r'\/[a-zA-Z0-9\.\-]'),
            re.compile(r'[.]')
        ]
        some_text = some_text.lower().strip().replace('\n', '')

        words = some_text.split(' ')# re.split('\s', some_text)
        for word in words:
            if len(word) < self.min_length:
                continue

            found = True
            for ap in address_partials:
                if not ap.findall(word, re.I):
                    found = False
                    break

            if address_matcher.fullmatch(word, re.I) and found:
                return word

        return None

    def extract_exception(self, some_text):
        some_text = some_text.lower().strip()
        some_text = re.sub('\s+', ' ', some_text)

        mm, has_any = self.has_exception(some_text)

        if has_any:
            return mm
        return None


class TextPostprocessor(object):
    """
    Class that postprocesses retrieved text
    """
    def process(self, raw_text):
        raw_text = raw_text.replace("\n", " ")
        return raw_text
