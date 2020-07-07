"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Video conversion routines

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
import os
import ffmpeg


class Converter(object):
    def __init__(self, temp_dir, target_format='mp4', max_hw=640):
        self.temp_dir = temp_dir
        self.max_hw = max_hw
        self.target_format = target_format

    def process(self, vfile):
        # processes VideoFile object (declared in video.py) and
        # performs the transformations needed on the video
        fname = os.path.join(self.temp_dir, f'{vfile.signature}.{vfile.format}')
        with open(fname, 'wb') as f:
            f.write(vfile.video_data)
        vfile.stored_file = fname

        out_fname = f'{vfile.signature}.{self.target_format}'
        if vfile.format == self.target_format:
            out_fname = f'o_{out_fname}'
        out_fname = os.path.join(self.temp_dir, out_fname)

        ff_stream = ffmpeg.input(fname)
        args = {
            'vf': 'scale=' + str(self.max_hw) + ':-2'
        }
        if not self.max_hw:
            del args['vf']

        ff_stream = ffmpeg.output(
            ff_stream.video,
            out_fname,
            **args
        )
        ffmpeg.run(ff_stream, overwrite_output=True)

        with open(out_fname, 'rb') as f:
            vfile.video_data = f.read()
        vfile.stored_file = out_fname
        vfile.recalculate_signature()

        return vfile
