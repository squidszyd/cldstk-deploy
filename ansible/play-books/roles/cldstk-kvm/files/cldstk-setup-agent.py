#!/usr/bin/python
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import logging
import sys
import socket
from cloudutils.cloudException import CloudRuntimeException, CloudInternalException
from cloudutils.utilities import initLoging, bash
from cloudutils.configFileOps import  configFileOps
from cloudutils.globalEnv import globalEnv
from cloudutils.networkConfig import networkConfig
from cloudutils.syscfg import sysConfigFactory

from optparse import OptionParser

def getUserInputs():
    print "Welcome to the CloudStack Agent Setup:"

    cfo = configFileOps("/etc/cloudstack/agent/agent.properties")
    oldMgt = cfo.getEntry("host")

    mgtSvr = oldMgt
    if mgtSvr == "":
        mgtSvr = oldMgt
    try:
        socket.getaddrinfo(mgtSvr, 443)
    except:
        print "Failed to resolve %s. Please input a valid hostname or IP-Address."%mgtSvr
        exit(1)

    oldToken = cfo.getEntry("zone")
    zoneToken = oldToken

    if zoneToken == "":
        zoneToken = oldToken

    oldPod = cfo.getEntry("pod")
    podId = oldPod

    if podId == "":
       podId  = oldToken

    oldCluster = cfo.getEntry("cluster")
    clusterId = oldCluster
    if clusterId == "":
        clusterId = oldCluster

    try:
        defaultNic = networkConfig.getDefaultNetwork()
    except:
        print "Failed to get default route. Please configure your network to have a default route"
        exit(1)

    defNic = defaultNic.name
    network = defNic
    if network == "":
        if defNic == "":
            print "You need to specifiy one of Nic or bridge on your system"
            exit(1)
        elif network == "":
            network = defNic

    return [mgtSvr, zoneToken, network, podId, clusterId]

if __name__ == '__main__':
    initLoging("/var/log/cloudstack/agent//setup.log")
    glbEnv = globalEnv()

    glbEnv.mode = "Agent"
    glbEnv.agentMode = "Agent"
    parser = OptionParser()
    parser.add_option("-a", action="store_true", dest="auto", help="auto mode")
    parser.add_option("-m", "--host", dest="mgt", help="Management server hostname or IP-Address")
    parser.add_option("-z", "--zone", dest="zone", help="zone id")
    parser.add_option("-p", "--pod", dest="pod", help="pod id")
    parser.add_option("-c", "--cluster", dest="cluster", help="cluster id")
    parser.add_option("-g", "--guid", dest="guid", help="guid")
    parser.add_option("--pubNic", dest="pubNic", help="Public traffic interface")
    parser.add_option("--prvNic", dest="prvNic", help="Private traffic interface")
    parser.add_option("--guestNic", dest="guestNic", help="Guest traffic interface")

    old_config = configFileOps("/etc/cloudstack/agent/agent.properties")
    bridgeType = old_config.getEntry("network.bridge.type").lower()
    if bridgeType:
        glbEnv.bridgeType = bridgeType

    (options, args) = parser.parse_args()
    if options.auto is None:
        userInputs = getUserInputs()
        glbEnv.mgtSvr = userInputs[0]
        glbEnv.zone = userInputs[1]
        glbEnv.defaultNic = userInputs[2]
        glbEnv.pod = userInputs[3]
        glbEnv.cluster = userInputs[4]
        #generate UUID
        glbEnv.uuid = old_config.getEntry("guid")
        if glbEnv.uuid == "":
            glbEnv.uuid = bash("uuidgen").getStdout()
    else:
        for para, value in options.__dict__.items():
            if value is None:
                print "Missing operand:%s"%para
                print "Try %s --help for more information"%sys.argv[0]
                sys.exit(1)

        glbEnv.uuid = options.guid
        glbEnv.mgtSvr = options.mgt
        glbEnv.zone = options.zone
        glbEnv.pod = options.pod
        glbEnv.cluster = options.cluster
        glbEnv.nics.append(options.prvNic)
        glbEnv.nics.append(options.pubNic)
        glbEnv.nics.append(options.guestNic)
        
    print "Starting to configure your system:"
    syscfg = sysConfigFactory.getSysConfigFactory(glbEnv)
    try:
        syscfg.config()
        print "CloudStack Agent setup is done!"
    except (CloudRuntimeException,CloudInternalException), e:
        print e
        print "Try to restore your system:"
        try:
            syscfg.restore()
        except:
            pass