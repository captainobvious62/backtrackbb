#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
from tatka_modules.parse_config import parse_config
from tatka_modules.bp_types import Trigger, Pick
from obspy import read
from obspy.core import AttribDict

"""
using output file xxx_OUT2_grouped.dat of BackProj.py
to create events data
to run: ./backtrack2eventdata.py config_file xxx_OUT2_grouped.dat (station.dat --> optional)
"""

def main():
    if len(sys.argv) < 3:
        print "this_code config_file xxx_OUT2_grouped.dat [station_file]"
        sys.exit(1)
    else:
        config_file = sys.argv[1]
        infile = sys.argv[2]
        try:
            station_file = sys.argv[3]
        except IndexError:
            station_file = None

    config = parse_config(config_file)

    ##--reading station information
    coord_sta = {}
    if station_file:
        for line in open(station_file, 'r'):
            data = line.split()
            coord_sta[data[0]] = map(float, data[2:5])

    ## -----reading output file saving parameters as trigger type--------------------------------------
    triggers = []
    for line in open(infile, 'r'):
        try:
            trigger = Trigger()
            trigger.from_str(line)
            triggers.append(trigger)
        except ValueError:
            try:
                pick = Pick()
                pick.from_str(line)
                triggers[-1].add_pick(pick)
            except ValueError:
                continue

    ##---creating output directories if they do not exist----------------------------------------------
    if not os.path.exists(config.event_dir):
        os.mkdir(config.event_dir)

    for trigger in triggers:
        print trigger.eventid
        out_event_dir = os.path.join(config.event_dir, trigger.eventid)
        if not os.path.exists(out_event_dir):
            os.mkdir(out_event_dir)

        ##-------writing eventid.dat file -------------------------------------------------------------
        event_dat_base = '.'.join((trigger.eventid, 'dat'))
        event_dat = os.path.join(out_event_dir, event_dat_base)
        with open(event_dat, 'w') as f:
            f.write(str(trigger) + '\n')
            for pick in trigger.picks:
                f.write(str(pick) + '\n')

        ##-------writing eventid_nll.obs file ---------------------------------------------------------
        event_dat_base = '.'.join((trigger.eventid , 'pick'))
        event_dat = os.path.join(out_event_dir, event_dat_base)

        with open(event_dat, 'w') as f:
            #f.write('#%s %f %f %f %s\n' % (trigger.eventid, trigger.lon, trigger.lat, trigger.z, trigger.origin_time))
            for pick in trigger.picks:
                f.write('%-6s ?    ?    ? %-6s ? ' % (pick.station, pick.arrival_type))
                if pick.arrival_type is 'P':
                    time = trigger.origin_time + pick.pick_time
                else:
                    time = trigger.origin_time + pick.theor_time
                f.write('%s ' % time.strftime('%Y%m%d'))
                f.write('%s ' % time.strftime('%H%M'))
                f.write('%s.' % time.strftime('%S'))
                msec = int(round(int(time.strftime('%f'))/100.))
                f.write('%04d ' % msec)
                # We approximate the error with decay_const/10
                # TODO: improve this?
                decay_const = float(config.decay_const)
                f.write('GAU  %.2e  0.00e+00  0.00e+00  0.00e+00' % (decay_const/10.))
                f.write('\n')

        ## reading data, cutting events and saving data in specified format-----------------------------
        for pick in trigger.picks:
            if pick.arrival_type is not 'P':
                continue

            read_starttime = trigger.origin_time + pick.theor_time - config.pre_P
            read_endtime = trigger.origin_time + pick.theor_time + config.post_P
            filename = os.path.join(config.data_dir, '*' + pick.station + '*')

            st = read(filename, starttime=read_starttime,
                      endtime=read_endtime)

            for tr in st:
                file_out_base = '.'.join((trigger.eventid,
                                         tr.stats.station,
                                         tr.stats.channel,
                                         tr.stats.network,
                                         tr.stats.location,
                                         config.out_data_format))
                file_out_data = os.path.join(out_event_dir, file_out_base)
                if config.out_data_format == 'sac':
                    tr.stats.sac = AttribDict()
                    tr.stats.sac.kevnm = str(trigger.eventid)
                    if station_file:
                        tr.stats.sac.stla = coord_sta[tr.stats.station][0]
                        tr.stats.sac.stlo = coord_sta[tr.stats.station][1]
                        tr.stats.sac.stel = coord_sta[tr.stats.station][2]

                tr.write(file_out_data, format=config.out_data_format)


if __name__ == '__main__':
    main()
