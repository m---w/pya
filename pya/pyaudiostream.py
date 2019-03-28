import pyaudio
import numpy as np
from pya.helpers import * 
import time
import scipy.signal as signal


class PyaudioStream():
    def __init__(self, bs = 256,  sr = 44100, channels = 1):
        # self.signal = 0 # This is supposed to be replaced by qt signal
        self.pa = pyaudio.PyAudio()
        self.outputChannels =  channels# Init, but change based on the chosen device. 
        self.fs = sr  # The divider helps us to use a smaller samping rate. 
        self.chunk = bs # The smaller the smaller latency 
        self.audioformat = pyaudio.paInt16
        self.recording = False
        self.il = [] # input list 
        self.bufflist = [] # Buffer for input audio tracks
        self.ol = [] # out list
        self.waveform = [] # maybe this is a mistake. 
        self.totalChunks = 0 # This is the len of bufflist. 
        self.masterVol = 1 # Master volume. 
        self.maxInputChannels = 6
        self.maxOutputChannels = 6
        self.emitsignal = False
        for i in range(self.pa.get_device_count()):
            if self.pa.get_device_info_by_index(i)['maxInputChannels'] > 0:
                self.il.append(self.pa.get_device_info_by_index(i))
            if self.pa.get_device_info_by_index(i)['maxOutputChannels'] > 0:
                self.ol.append(self.pa.get_device_info_by_index(i))
        self.inputIdx = 0 
        self.outputIdx = 1
        self.inVol = np.ones(self.maxInputChannels) # Current version has 6 inputs max. But should taylor this. 
        self.outVol = np.ones(self.maxOutputChannels)
    
    def printAudioDevices(self):
        for i in range(self.pa.get_device_count()):
            print (self.pa.get_device_info_by_index(i))

    def _playcallback(self, in_data, frame_count, time_info, flag):
        
        if (self.frameCount < self.totalChunks):
            out_data = self._outputgain(self.play_data[self.frameCount])
            self.frameCount += 1
            return out_data, pyaudio.paContinue
        else: # The last one . 
            out_data = bytes(np.zeros(self.chunk * self.outputChannels))
            return out_data, pyaudio.paComplete

    def _recordCallback(self, in_data, frame_count, time_info, flag):
        audio_data = (np.frombuffer(in_data, dtype = np.int16) * self.inVol[0]).astype(np.int16)
        self.bufflist.append(audio_data)
        # out_data = self._outputgain(middle_data) # Individual channel gain and master gain
        return audio_data, pyaudio.paContinue

    def record(self):
        # What is the chunk size ? is it scaled based on input channels or output channels. 
        try:  # restarting recording without closing stream, resulting an unstoppable stream. 
             # This can happen in Jupyter when you trigger record multple times without stopping it first. 
            self.stream.stop_stream()
            self.stream.close()
            # print ("Record stream closed. ")
        except AttributeError:
            pass
        print ("Start Recording")
        self.recording = True 
        self.bufflist = []
        self.stream = self.pa.open(
            format = self.audioformat,
            channels = self.outputChannels, 
            rate = self.fs,
            input = True,
            output = True,
            input_device_index=self.inputIdx,
            output_device_index=self.outputIdx,
            frames_per_buffer = self.chunk,
            stream_callback=self._recordCallback)
        self.stream.start_stream()

    def stopRecording(self):
        try:  # To prevent self.stream not created before stop button pressed
            self.stream.stop_stream()
            self.stream.close()
            print ("Record stream closed. ")
        except AttributeError:
            print ("No stream, stop button did nothing. ")

    # Put plot in a separate class maybe 
    def getWaveform(self):
        try:
            # The commented one is for bytes 
            # self.waveform = np.frombuffer(b''.join(self.bufflist), 'Int16')
            self.waveform = np.hstack(self.bufflist)
        except ValueError:
            self.waveform = np.zeros(self.chunk)
        return self.waveform, len(self.waveform)/self.fs

    def stopPlaying(self):
        try: # To prevent self.playStream not created before stop button pressed
            self.playStream.stop_stream()
            self.playStream.close()
            print ("Play Stream Stopped. ")
        except AttributeError:
            print ("No stream, stop button did nothing. ")

    def play(self, sig = None):
        """
            Step 1: try to close any excessive stream. 
            Step 2: check if there's any input sigal, if not play internal buffer, else do nothing
            Step 3: Convert data into int16
            Step 4: Convert to the correct channels (not implemented at this stage. )
            Step 5: Convert the sig in to certain chunks for playback: 
                This method needs to be changed to suit multiple sounds being played together. 
            Step 6: Switch on the stream. 
        """
        try:  
            self.playStream.stop_stream()
            self.playStream.close()
        except AttributeError:
            pass
        if sig is None:
            if self.bufflist:
                self.play_data = self.bufflist
            else: 
                raise Warning("Play called but no audio.")
        else:
            if sig.dtype == np.dtype('float64'):
                sig = (sig * 32767).astype(np.int16)
            elif sig.dtype == np.dtype('int8'):
                sig = (sig * 256).astype(np.int16)
            elif sig.dtype == np.dtype('int16'): # Correct format
                pass
            else:
                msg = str(sig.dtype) + " is not a supported date type. Supports int16, float64 and int8."
                raise TypeError(msg)

            # sig = self.mono2nchan(sig,self.outputChannels) # duplicate based on channels
            self.play_data = self.makechunk(sig, self.chunk*self.outputChannels) 
        self.totalChunks = len(self.play_data) # total chunks
        self.frameCount = 0 # Start from the beginning. 
        # This method will only work with pyqt, because if not it will only run 1 iteration.  
        self.playStream = self.pa.open(
            format = self.audioformat,
            channels = self.outputChannels, 
            rate = self.fs,
            input = False,
            output = True,
            output_device_index=self.outputIdx,
            frames_per_buffer = self.chunk,
            stream_callback=self._playcallback
           )
        self.playStream.start_stream()

    def makechunk(self, lst, chunk):
        result = []
        # TODO. Find a faster solution for this. 
        for i in np.arange(0, len(lst), chunk):
            temp = lst[i:i + chunk]
            if len(temp) < chunk:
                temp = np.pad(temp, (0, chunk - len(temp)), 'constant')
            result.append(temp)
        return result

    def mono2nchan(self, mono, channels = 2):
        # convert a mono signal to multichannel by duplicating it to each channel. 
        return np.repeat(mono, channels)

    def _outputgain(self, sig):
        out_data =  self._multichannelgain(sig, \
                self.outputChannels, self.outVol)
        return bytes((out_data * self.masterVol).astype(np.int16))

    def _multichannelgain(self, data , channels,  glist):
        data = data.astype(np.float32)
        data_col = data.reshape([self.chunk, channels])
        data_col *= glist[:channels] # Only apply the list matching the channels. 
        return data.astype(np.int16)