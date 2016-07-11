# -------------------------------------------------------------------------
# Name:        Configuration
# Purpose:
#
# Author:      burekpe
#
# Created:     16/05/2016
# Copyright:   (c) burekpe 2016
# -------------------------------------------------------------------------

from management_modules.globals import *

import ConfigParser
import re

import optparse
import os
import sys
import time
import datetime
import shutil
import glob



class ExtParser(ConfigParser.SafeConfigParser):
     #implementing extended interpolation
     def __init__(self, *args, **kwargs):
         self.cur_depth = 0
         ConfigParser.SafeConfigParser.__init__(self, *args, **kwargs)


     def get(self, section, option, raw=False, vars=None):
         r_opt = ConfigParser.SafeConfigParser.get(self, section, option, raw=True, vars=vars)
         if raw:
             return r_opt

         ret = r_opt
         re_newintp1 = r'\$\((\w*):(\w*)\)'  # other section
         re_newintp2 = r'\$\((\w*)\)'  # same section

         re_old1 = re.findall('\$\(\w*:\w*\)', r_opt)
         re_old2 = re.findall('\$\(\w*\)', r_opt)

         m_new1 = re.findall(re_newintp1, r_opt)
         m_new2 = re.findall(re_newintp2, r_opt)

         if m_new1:
             i = 0
             for f_section, f_option in m_new1:
                 self.cur_depth = self.cur_depth + 1
                 if self.cur_depth < ConfigParser.MAX_INTERPOLATION_DEPTH:
                     sub = self.get(f_section,f_option, vars=vars)
                     ret = ret.replace(re_old1[i], sub)
                     i += 1
                 else:
                     raise ConfigParser.InterpolationDepthError, (option, section, r_opt)

         if m_new2:
             i = 0
             for l_option in m_new2:
                 self.cur_depth = self.cur_depth + 1
                 if self.cur_depth < ConfigParser.MAX_INTERPOLATION_DEPTH:
                     sub = self.get(section, l_option, vars=vars)
                     ret = ret.replace(re_old2[i], sub)
                     i =+ 1
                 else:
                     raise ConfigParser.InterpolationDepthError, (option, section, r_opt)

         self.cur_depth = self.cur_depth - 1
         return ret



def parse_configuration(settingsFileName):

    #config = ConfigParser.ConfigParser()
    config = ExtParser()
    config.optionxform = str
    config.sections()
    config.read(settingsFileName)
    for sec in config.sections():
        #print sec
        options = config.options(sec)
        for opt in options:
            if sec=="OPTIONS":
                option[opt] = config.getboolean(sec, opt)
            else:
                binding[opt] = config.get(sec, opt)