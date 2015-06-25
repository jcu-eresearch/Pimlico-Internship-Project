#!/usr/bin/env python
# SerialGrabber reads data from a serial port and processes it with the
# configured processor.
# Copyright (C) 2012  NigelB
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import serial
from Pimlico import SensorAPITransform
from serial_grabber.processor import TransformProcessor
from serial_grabber.reader import TransactionExtractor
from serial_grabber.reader.FileReader import FileReader, JSONLineFileReader
from serial_grabber.reader.SerialReader import SerialReader
from serial_grabber.processor.UploadProcessor import UploadProcessor
from serial_grabber.reader.Xbee import StreamRadioReader

#Serial Settings
timeout = 1
port = "/dev/ttyUSB0"
baud = 115200
parity = serial.PARITY_NONE
stop_bits = 1

#Settings
cache_collision_avoidance_delay = 1
processor_sleep = 1
watchdog_sleep = 1

reader_error_sleep = 1

drop_carriage_return = True

def packet_filter(packet):
    if packet['id'] == 'rx':
        return True
    return False

# reader = JSONLineFileReader("/home/eng-nbb/projects/Pimlico-Internship-Project/archive_2015_05_31-00_00_00.json", inter_record_delay=15)

record_size = 12
start_del = "".join(map(chr, range(record_size)))
end_del = "".join(map(chr, range(record_size - 1, -1, -1)))


def create_stream(stream_id):
    print " ".join([format(ord(x), "02x") for x in stream_id])
    return TransactionExtractor(stream_id, start_del, end_del)


reader = StreamRadioReader(create_stream, port, baud,
                           timeout=timeout,
                           parity=parity,
                           stop_bits=stop_bits,
                           # packet_filter=packet_filter,
                           ack="OK",
                           escaped=True)

uploader = UploadProcessor("http://api.thingspeak.com/update",
# uploader = UploadProcessor("https://finlay.jcu.io/cgi-bin/debug_endpoint.py",
                            request_kw={'verify': False},
                            headers={'content-type': 'application/x-www-form-urlencoded'},
                            )
processor = TransformProcessor(SensorAPITransform(), uploader)