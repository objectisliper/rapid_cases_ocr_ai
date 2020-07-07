"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Base classes for processor

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import pickle


class StatefulObject(object):
    def __init__(self):
        self.state_file = getattr(self.Meta, 'state_file', 'state.obj')

    def save(self):
        with open(self.state_file, 'wb') as output:
            pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)

    def restore(self):
        ret = None
        with open(self.state_file, 'rb') as state:
            ret = pickle.load(state)

        return ret
