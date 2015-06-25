# !/usr/bin/env python
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

import os
import struct
import json
import logging
from datetime import datetime
from serial_grabber import constants
import SensorMap

from serial_grabber.transform import Transform, TransformException, DebugTransformException
from uuid import getnode as get_mac

record_size = 12
header_size = 10
value_field="value"
base_voltage = 4.096

def caculate_humidity(temp, voltage):
    vOut = float(voltage)
    T = float(temp)
    sensorRH = ((vOut/base_voltage) - 0.1515)/0.00636
    trueRH = sensorRH/(1.0546 - (0.00216 * T))
    return trueRH


def ts_to_iso8901(ts):
    return to_iso8901(datetime.fromtimestamp(ts/1000))

def to_iso8901(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def get_platform_id():
    return ':'.join(("%012X" % get_mac())[i:i+2] for i in range(0, 12, 2))


class SensorAPITransform(Transform):
    logger = logging.getLogger("EnvirocomsSensorAPITransform")

    def create_address(self, address):
        a=["%02X"%x for x in address]
        return "0x%s"% "".join(a)

    def transform(self, process_entry):
        payload = process_entry[constants.data][constants.payload]
        stream_id = process_entry[constants.data][constants.stream_id]
        node_id = stream_id.replace(" ",":")
        payload = payload[record_size:-record_size]
        message_type, ts, code = struct.unpack("<hiI", payload[:header_size])
        payload = payload[header_size:]
        values={}
        if message_type == 1:
            while len(payload) > 0:
                record = payload[:record_size]
                payload = payload[record_size:]
                try:
                    a, b, c, d, e, f, g, h, value = struct.unpack("<BBBBBBBBf", record)
                    values[self.create_address([a, b, c, d, e, f, g, h])] = {"value":value, "address":[a, b, c, d, e, f, g, h]}
                except struct.error, e:
                    raise TransformException("Could not parse record data for device: %s, after reading %s sensors."%(node_id, len(values)), e)

            self.logger.info("%s sent data for %s sensor(s)."%(node_id, len(values)))
            sensor_feed = []
            for sensor_name in SensorMap.Sensors:
                try:
                    mapping = SensorMap.Sensors[sensor_name]
                    datapoint = {
                        'key': mapping[SensorMap.api_key],
                        'field1': ts_to_iso8901(ts * 1000),
                        'field2': values[mapping[SensorMap.temperature]][value_field],
                        'field3': caculate_humidity(values[mapping[SensorMap.temperature]][value_field], values[mapping[SensorMap.humidity]][value_field]),
                        'field4': values[mapping[SensorMap.humidity]][value_field],
                    }
                    sensor_feed.append({constants.payload: datapoint})
                except KeyError, e:
                    print "Data Missing", e
                    continue

            process_entry[constants.multiple_uploads] = True
            process_entry[constants.data][constants.payload] = sensor_feed
            return process_entry

        elif message_type == 2:
            self.logger.error("Received an error message code: %s"%code)
        raise TransformException("Dropping")
