#    EWMod uses PyEW to interface a PyEWPlot to the EW Transport system
#    Copyright (C) 2019  Francisco J Hernandez Ramirez
#    You may contact me at FJHernandez89@gmail.com, FHernandez@boritechsolutions.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>
#
# For Python2
#import matplotlib as mpl
#mpl.use('Agg')

import configparser, logging, os, time, PyEW, obspy, io
from obspy.core import Trace, Stats, UTCDateTime
from obspy.realtime import RtTrace
from threading import Thread
import numpy as np

logger = logging.getLogger(__name__)

class EWPyPlotter():

  def __init__(self, minutes = 1, RING_ID = 1000, MOD_ID = 9, INST_ID = 141 , HB = 30, debug = False):
    
    # Create a thread for self
    self.myThread = Thread(target=self.run)
    
    # Start an EW Module with parent ring 1000, mod_id 8, inst_id 141, heartbeat 30s, debug = False (MODIFY THIS!)
    self.ring2plot = PyEW.EWModule(RING_ID, MOD_ID, INST_ID, HB, debug)
    
    # Add our Input ring as Ring 0
    self.ring2plot.add_ring(RING_ID)
    
    # Buffer (minutes to buffer for)
    self.minutes = minutes
    self.wave_buffer = {}
    self.plot_buffer = {}
    
    # Allow it to run
    self.runs = True
    self.debug = debug
    logger.info("EW Module Started")
    
  def save_wave(self):
  
     # Fetch a wave from Ring 0
    wave = self.ring2plot.get_wave(0) 
    
    # if wave is empty return
    if wave == {}: 
        return
    
    # Lets try to buffer with python dictionaries and obspy
    name = wave["station"] + '.' + wave["channel"] + '.' + wave["network"] + '.' + wave["location"]
    
    if name in self.wave_buffer :
    
        # Determine max samples for buffer
        max_samp = wave["samprate"] * 60 * self.minutes
        
        # Create a header:
        wavestats = Stats()
        wavestats.station = wave["station"]
        wavestats.network = wave["network"]
        wavestats.channel = wave["channel"]
        wavestats.location = wave["location"]
        wavestats.sampling_rate = wave["samprate"]
        wavestats.starttime = UTCDateTime(wave['startt'])
        
        # Create a trace
        wavetrace = Trace(header= wavestats)
        wavetrace.data = wave["data"]
        
        # Append data to buffer
        try:
            self.wave_buffer[name].append(wavetrace, gap_overlap_check=True)
        except TypeError as err:
            logger.warning(err)
            self.runs = False
        except:
            raise
            self.runs = False
        
        # Print Starttime (Debug)
        #print(name, self.wave_buffer[name].stats.starttime)
        
        # Debug data
        if self.debug:
            logger.info("Station Channel combo is in buffer:")
            logger.info(name)
            logger.info("Size:")
            logger.info(self.wave_buffer[name].count())
            logger.debug("Data:")
            logger.debug(self.wave_buffer[name])
           
    else:
        # First instance of data in buffer, create a header:
        wavestats = Stats()
        wavestats.station = wave["station"]
        wavestats.network = wave["network"]
        wavestats.channel = wave["channel"]
        wavestats.location = wave["location"]
        wavestats.sampling_rate = wave["samprate"]
        wavestats.starttime = UTCDateTime(wave['startt'])
        
        # Create a trace
        wavetrace = Trace(header=wavestats)
        wavetrace.data = wave["data"]
        
        # Create a RTTrace
        rttrace = RtTrace(int(self.minutes*60))
        self.wave_buffer[name] = rttrace
        
        # Append data and add io buffer
        self.wave_buffer[name].append(wavetrace, gap_overlap_check=True)
        self.plot_buffer[name] = io.BytesIO()
        
        # Debug data
        if self.debug:
            logger.info("First instance of station/channel:")
            logger.info(name)
            logger.info("Size:")
            logger.info(self.wave_buffer[name].count())
            logger.debug("Data:")
            logger.debug(self.wave_buffer[name])
  
  def get_frame(self, station):
    # Function returns a bytearray of the current graph
    if station in self.wave_buffer :
      try:
        # New plot params go here.
        figx = 800 ## figure size parameter x
        figy = 600  ## figure size parameter y
        
        #Flush buffer!
        self.plot_buffer[station].truncate(0)
        self.plot_buffer[station].seek(0)
        
        # Plot and output
        self.wave_buffer[station].plot(size=(figx, figy), outfile=self.plot_buffer[station], format = 'jpg')
      except OSError as e:
        logger.error(e)
      return self.plot_buffer[station].getvalue()
    else:
      return
      
  def get_menu(self):
    # Function returns a dictionary of station and channels
    return self.wave_buffer.keys()
  
  def status(self):
    return self.runs
    
  def run(self):
    # The main loop
    while self.runs:
      if self.ring2plot.mod_sta() is False:
        break
      time.sleep(0.001)
      self.save_wave()
    self.ring2plot.goodbye()
    logger.info("EW Module Stopped")
      
  def start(self):
    self.myThread.start()
    
  def stop(self):
    self.runs = False
 
