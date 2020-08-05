"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Simple video saver

Vyacheslav Morozov, 2020
vyacheslav@behealthy.ai
"""
import os


class VideoSaver(object):
    def __init__(self, temp_dir, target_format='webm', max_hw=640):
        self.temp_dir = temp_dir
        self.max_hw = max_hw
        self.target_format = target_format

    def process(self, vfile):
        # processes VideoFile object (declared in video.py)
        fname = os.path.join(self.temp_dir, f'{vfile.signature}.{vfile.format}')
        with open(fname, 'wb') as f:
            f.write(vfile.video_data)
        vfile.stored_file = fname

        return vfile
