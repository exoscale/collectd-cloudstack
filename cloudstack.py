# collectd-cloudstack - cloudstack.py
#
# Author : Antoine Coetsier @ exoscale
# Description : This is a collectd python module to gather stats from cloudstack
# inspired by collectd-haproxy from Michael Leinartas - https://github.com/mleinart/collectd-haproxy

from __future__ import division
import collectd
import urllib2
import urllib
import json
import hmac
import base64
import hashlib
import re
import time

class BaseClient(object):
    def __init__(self, api, apikey, secret):
        self.api = api
        self.apikey = apikey
        self.secret = secret

    def request(self, command, args):
        args['apikey']   = self.apikey
        args['command']  = command
        args['response'] = 'json'
        
        params=[]
        
        keys = sorted(args.keys())

        for k in keys:
            params.append(k + '=' + urllib.quote_plus(args[k]).replace("+", "%20"))
       
        query = '&'.join(params)

        signature = base64.b64encode(hmac.new(
            self.secret, 
            msg=query.lower(), 
            digestmod=hashlib.sha1
        ).digest())

        query += '&signature=' + urllib.quote_plus(signature)

        response = urllib2.urlopen(self.api + '?' + query)
        decoded = json.loads(response.read())
       
        propertyResponse = command.lower() + 'response'
        if not propertyResponse in decoded:
            if 'errorresponse' in decoded:
                raise RuntimeError("ERROR: " + decoded['errorresponse']['errortext'])
            else:
                raise RuntimeError("ERROR: Unable to parse the response")

        response = decoded[propertyResponse]
        result = re.compile(r"^list(\w+)s").match(command.lower())

        if not result is None:
            type = result.group(1)

            if type in response:
                return response[type]
            else:
                # sometimes, the 's' is kept, as in :
                # { "listasyncjobsresponse" : { "asyncjobs" : [ ... ] } }
                type += 's'
                if type in response:
                    return response[type]

        return response

class Client(BaseClient):
    def listHosts(self, args={}):
        return self.request('listHosts', args)
        
    def listCapabilities(self, args={}):
        return self.request('listCapabilities', args)
        
    def listCapacity(self, args={}):
        return self.request('listCapacity', args)
        
    def listSystemVms(self, args={}):
        return self.request('listSystemVms', args)
        
    def listZones(self, args={}):
        return self.request('listZones', args)

    def listVirtualMachines(self, args={}):
        return self.request('listVirtualMachines', args)

    def listAccounts(self, args={}):
        return self.request('listAccounts', args)

    def listCapacity(self, args={}):
        return self.request('listCapacity', args)

    def listVolumes(self, args={}):
        return self.request('listVolumes', args)

    def listAsyncJobs(self, args={}):
        return self.request('listAsyncJobs', args)
        
        
NAME = 'cloudstack'

DEFAULT_API = 'http://localhost:8096/client/api'
DEFAULT_AUTH = False
DEFAULT_APIKEY = ''
DEFAULT_SECRET = ''
VERBOSE_LOGGING = False

METRIC_TYPES = {
    'memoryused': ('h_memory_used', 'memory'),
    'memorytotal': ('h_memory_total', 'memory'),
    'memoryallocated': ('h_memory_allocated', 'memory'),
    'hvmtotalrunning': ('h_vm_total_running', 'current'),
    'hvmtotalstarting': ('h_vm_total_starting', 'current'),
    'hvmtotalstopping': ('h_vm_total_stopping', 'current'),
    'hvmtotalstopped': ('h_vm_total_stopped', 'current'),
    'hvmtotal': ('h_vm_total', 'current'),
    'cpuallocated': ('h_cpu_allocated', 'percent'),
    'activeviewersessions': ('console_active_sessions', 'current'),
    'zonehosttotal': ('hosts_count', 'current'),
    'zonescount': ('zones_count', 'current'),
    'zonepublicipallocated': ('z_public_ip_allocated', 'current'),
    'zonepubliciptotal': ('z_public_ip_total', 'current'),
    'zonepublicippercent': ('z_public_ip_percent', 'percent'),
    'zonevmtotal': ('z_vm_total', 'current'),
    'zonerootdiskavgsize': ('z_disksize_avg', 'current'),
    'zonevmramavgsize': ('z_vm_ram_avg', 'current'),
    'zonevmcpuavgsize': ('z_vm_cpu_avg', 'current'),
    'zonevmtotalrunning': ('z_vm_total_running', 'current'),
    'zonevmtotalstopped': ('z_vm_total_stopped', 'current'),
    'zonevmtotalstarting': ('z_vm_total_starting', 'current'),
    'zonevmtotalstopping': ('z_vm_total_stopping', 'current'),
    'disksizetotal': ('h_disk_total', 'bytes'),
    'accountscount': ('g_accounts_total', 'current'),
    'accountenabled': ('g_accounts_total_enabled', 'current'),
    'accountdisabled': ('g_accounts_total_disabled', 'current'),
    'zonecapamemorytotal': ('z_capacity_memory_total', 'current'),
    'zonecapamemoryused': ('z_capacity_memory_used', 'current'),
    'zonecapamemorypercentused': ('z_capacity_memory_percent-used', 'current'),
    'zonecapacputotal': ('z_capacity_cpu_total', 'current'),
    'zonecapacpuused': ('z_capacity_cpu_used', 'current'),
    'zonecapacpupercentused': ('z_capacity_cpu_percent-used', 'current'),
    'zonecapadisktotal': ('z_capacity_disk_total', 'current'),
    'zonecapadiskused': ('z_capacity_disk_used', 'current'),
    'zonecapadiskpercentused': ('z_capacity_disk_percent-used', 'current'),
    'zonecapaprivateiptotal': ('z_capacity_privateip_total', 'current'),
    'zonecapaprivateipused': ('z_capacity_privateip_used', 'current'),
    'zonecapaprivateippercentused': ('z_capacity_privateip_percent-used', 'current'),
    'zonecapasstotal': ('z_capacity_SSdisk_total', 'current'),
    'zonecapassused': ('z_capacity_SSdisk_used', 'current'),
    'zonecapasspercentused': ('z_capacity_SSdisk_percent-used', 'current'),
    'zonecapadiskalloctotal': ('z_capacity_allocated_disk_total', 'current'),
    'zonecapadiskallocused': ('z_capacity_allocated_disk_used', 'current'),
    'zonecapadiskallocpercentused': ('z_capacity_allocated_disk_percent-used', 'current'),
    'asyncjobscount': ('g_async_jobs_count', 'current')
    }

METRIC_DELIM = '.'

hypervisors = []

def get_stats():
    stats = dict()
    hvmrunning = dict()
    hvmstopped = dict()
    hvmstopping = dict()
    hvmstarting = dict()

    logger('verb', "get_stats calls API %s KEY %s SECRET %s" % (API_MONITORS, APIKEY_MONITORS, SECRET_MONITORS))
    cloudstack = Client(API_MONITORS, APIKEY_MONITORS, SECRET_MONITORS)	
    try:
        logger('verb', "Performing listhosts API call")
        query_tmp = None
        querypage = 1
        querypagesize = 500
        hypervisors = cloudstack.listHosts({
                        'type': 'Routing',
                        'resourcestate': 'Enabled',
                        'page': str(querypage),
                        'pagesize': str(querypagesize),
                        'state': 'Up'
                        })
        all_hypervisors = []
        if len(hypervisors) == querypagesize:
            query_tmp = hypervisors
            while len(query_tmp) > 1:
                all_hypervisors.extend(query_tmp)
                querypage = querypage + 1
                query_tmp = cloudstack.listHosts({
                            'type': 'Routing',
                            'resourcestate': 'Enabled',
                            'page': str(querypage),
                            'pagesize': str(querypagesize),
                            'state': 'Up'
                            })
        else:
            all_hypervisors.extend(hypervisors)
        hypervisors = all_hypervisors
        logger('verb', "Completed listhosts API call")

    except:
        logger('warn', "status err Unable to connect to CloudStack URL at %s for Hosts" % API_MONITORS)

    for  h in hypervisors:
        metricnameMemUsed = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'memoryused' ])
        metricnameMemTotal = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'memorytotal' ])
        metricnameMemAlloc = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'memoryallocated' ])
        metricnameCpuAlloc = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'cpuallocated' ])
        #metricnameDiskAlloc = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'disksizeallocated' ])
        #metricnameDiskTotal = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'disksizetotal' ])
    try:
        stats[metricnameMemUsed] = h['memoryused'] 
        stats[metricnameMemTotal] = h['memorytotal'] 
        stats[metricnameMemAlloc] = h['memoryallocated']
        cpuallocated = h['cpuallocated'].replace("%", "")
        stats[metricnameCpuAlloc] = cpuallocated
        logger('verb', "readings :  %s memory used %s " % (h['name'], h['memoryused']))

    except (TypeError, ValueError), e:
        pass

  # collect number of active console sessions
    try:
        logger('verb', "Performing listSystemVms API call")
        query_tmp = None
        querypage = 1
        querypagesize = 500
        systemvms = cloudstack.listSystemVms({
                    'systemvmtype': 'consoleproxy',
                    'page': str(querypage),
                    'pagesize': str(querypagesize)
                    })
        all_systemvms = []
        if len(systemvms) == querypagesize:
            query_tmp = systemvms
            while len(query_tmp) > 1:
                all_systemvms.extend(query_tmp)
                querypage = querypage + 1
                query_tmp = cloudstack.listSystemVms({
                            'systemvmtype': 'consoleproxy',
                            'page': str(querypage),
                            'pagesize': str(querypagesize)
                            })
        else:
            all_systemvms.extend(systemvms)
        systemvms = all_systemvms
        logger('verb', "Completed listSystemVms API call")

    except:
        logger('warn', "status err Unable to connect to CloudStack URL at %s for SystemVms" % API_MONITORS)

    for systemvm in systemvms:
        metricnameSessions = METRIC_DELIM.join([ 'activeviewersessions', systemvm['zonename'].lower(), systemvm['name'].lower(), 'activeviewersessions' ])
        if 'activeviewersessions' in systemvm:
            stats[metricnameSessions] = systemvm['activeviewersessions']

  # collect number of zones, available public ips and VMs
    try:
        logger('verb', "Performing listZones API call")
        query_tmp = None
        querypage = 1
        querypagesize = 500
        zones = cloudstack.listZones({
                'showcapacities': 'true',
                'page': str(querypage),
                'pagesize': str(querypagesize)
                })
        all_zones = []
        if len(zones) == querypagesize:
            query_tmp = zones
            while len(query_tmp) > 1:
                all_zones.extend(query_tmp)
                querypage = querypage + 1
                query_tmp = cloudstack.listZones({
                            'showcapacities': 'true',
                            'page': str(querypage),
                            'pagesize': str(querypagesize)
                            })
        else:
            all_zones.extend(zones)
        zones = all_zones
        logger('verb', "Completed listZones API call")

    except:
        logger('warn', "status err Unable to connect to CloudStack URL at %s for ListZone" % API_MONITORS)

    for zone in zones:
        metricnameIpAllocated = METRIC_DELIM.join([ 'zonepublicipallocated', zone['name'].lower(),  'zonepublicipallocated' ])
        metricnameIpTotal = METRIC_DELIM.join([ 'zonepubliciptotal', zone['name'].lower(),  'zonepubliciptotal' ])
        metricnameIpAllocatedPercent = METRIC_DELIM.join([ 'zonepublicippercent', zone['name'].lower(),  'zonepublicippercent' ])
        metricnameVmZoneTotalRunning = METRIC_DELIM.join([ 'zonevmtotalrunning', zone['name'].lower(),  'zonevmtotalrunning' ])
        metricnameVmZoneTotalStopped = METRIC_DELIM.join([ 'zonevmtotalstopped', zone['name'].lower(),  'zonevmtotalstopped' ])
        metricnameVmZoneTotalStopping = METRIC_DELIM.join([ 'zonevmtotalstopping', zone['name'].lower(),  'zonevmtotalstopping' ])
        metricnameVmZoneTotalStarting = METRIC_DELIM.join([ 'zonevmtotalstarting', zone['name'].lower(),  'zonevmtotalstarting' ])
        metricnameVmZoneTotal = METRIC_DELIM.join([ 'zonevmtotal', zone['name'].lower(),  'zonevmtotal' ])
        metricnameZonesCount = METRIC_DELIM.join([ 'zonescount',  'zonescount' ])
        metricnameHostZoneTotal = METRIC_DELIM.join([ 'zonehosttotal', zone['name'].lower(),  'zonehosttotal' ])
        metricnameVMZoneRAMavgSize= METRIC_DELIM.join([ 'zonevmramavgsize', zone['name'].lower(),  'zonevmramavgsize' ])
        metricnameVMZoneCPUavgSize= METRIC_DELIM.join([ 'zonevmcpuavgsize', zone['name'].lower(),  'zonevmcpuavgsize' ])

        # collect number of virtual machines 
        try:
            logger('verb', "Performing listVirtualMachines API call")
            query_tmp = None
            querypage = 1
            querypagesize = 500
            virtualmachines = cloudstack.listVirtualMachines({
                                'listall': 'true',
                                'details': 'all',
                                'page': str(querypage),
                                'pagesize': str(querypagesize)
                                })
            all_virtualmachines = []
            if len(virtualmachines) == querypagesize:
                query_tmp = virtualmachines
                while len(query_tmp) > 1:
                    all_virtualmachines.extend(query_tmp)
                    querypage = querypage + 1
                    query_tmp = cloudstack.listVirtualMachines({
                                'listall': 'true',
                                'details': 'all',
                                'page': str(querypage),
                                'pagesize': str(querypagesize)
                                })
            else:
                all_virtualmachines.extend(virtualmachines)
            virtualmachines = all_virtualmachines
            logger('verb', "Completed listVirtualMachines API call")
            

    
        except:
            logger('warn', "status err Unable to connect to CloudStack URL at %s for ListVms" % API_MONITORS)

        
        
        
        
        virtualMachineZoneRunningCount = 0
        virtualMachineZoneStoppedCount = 0
        virtualMachineZoneStartingCount = 0
        virtualMachineZoneStoppingCount = 0
        cpu = 0
        ram = 0

        for virtualmachine in virtualmachines:
            cpu += virtualmachine['cpunumber']
            ram += virtualmachine['memory']
            if virtualmachine['state'] == 'Running':
                virtualMachineZoneRunningCount = virtualMachineZoneRunningCount + 1
            elif virtualmachine['state'] == 'Stopped':
                virtualMachineZoneStoppedCount = virtualMachineZoneStoppedCount + 1
            elif virtualmachine['state'] == 'Stopping':
                virtualMachineZoneStartingCount = virtualMachineZoneStartingCount + 1
            elif virtualmachine['state'] == 'Starting':
                virtualMachineZoneStoppingCount = virtualMachineZoneStoppingCount + 1
        
        ram = (ram / 1024)
        ramavg = (ram/len(virtualmachines))
        cpuavg = (cpu/len(virtualmachines))
        stats[metricnameVMZoneRAMavgSize] = ramavg
        stats[metricnameVMZoneCPUavgSize] = cpuavg
        stats[metricnameVmZoneTotal] = len(virtualmachines)
        stats[metricnameVmZoneTotalRunning] = virtualMachineZoneRunningCount
        stats[metricnameVmZoneTotalStopped] = virtualMachineZoneStoppedCount
        stats[metricnameVmZoneTotalStopping] = virtualMachineZoneStoppingCount
        stats[metricnameVmZoneTotalStarting] = virtualMachineZoneStartingCount

        # collect number of root volumes 
        try:
            logger('verb', "Performing listVolumes API call")
            query_tmp = None
            querypage = 1
            querypagesize = 500
            rootvolumes = cloudstack.listVolumes({
                            'listall': 'true',
                            'type': 'ROOT',
                            'page': str(querypage),
                            'pagesize': str(querypagesize)
                            })
            all_rootvolumes = []
            if len(rootvolumes) == querypagesize:
                query_tmp = rootvolumes
                while len(query_tmp) > 1:
                    all_rootvolumes.extend(query_tmp)
                    querypage = querypage + 1
                    query_tmp = cloudstack.listVolumes({
                                'listall': 'true',
                                'type': 'ROOT',
                                'page': str(querypage),
                                'pagesize': str(querypagesize)
                                })
            else:
                all_rootvolumes.extend(rootvolumes)
            rootvolumes = all_rootvolumes
            logger('verb', "Completed listVolumes API call")
            
        except:
            logger('warn', "status err Unable to connect to CloudStack URL at %s for ListVolumes" % API_MONITORS)

        rootvolsize = 0 
        for rootvolume in rootvolumes:
            rootvolsize += rootvolume['size']

            if rootvolume['vmstate'] == 'Running':
                #add to a dict to get the Running VMs per hypervisor
                host = (rootvolume['storage'])
                if host in hvmrunning:
                    hvmrunning[host] += 1
                else:
                    hvmrunning[host] = 1
            elif rootvolume['vmstate'] == 'Stopped':
                #add to a dict to get the Stopped VMs per hypervisor
                host = (rootvolume['storage'])
                if host in hvmstopped:
                    hvmstopped[host] += 1
                else:
                    hvmstopped[host] = 1
            elif rootvolume['vmstate'] == 'Stopping':
                #add to a dict to get the Stopping VMs per hypervisor
                host = (rootvolume['storage'])
                if host in hvmstopping:
                    hvmstopping[host] += 1
                else:
                    hvmstopping[host] = 1
            elif rootvolume['vmstate'] == 'Starting':
                #add to a dict to get the Starting VMs per hypervisor
                host = (rootvolume['storage'])
                if host in hvmstarting:
                    hvmstarting[host] += 1
                else:
                    hvmstarting[host] = 1

        rootvolsize = (rootvolsize / 1073741824)
        rootavgsize = rootvolsize / len(rootvolumes)
        metricnameRootAvgSizeZone= METRIC_DELIM.join([ 'zonerootdiskavgsize', zone['name'].lower(),  'zonerootdiskavgsize' ])
        stats[metricnameRootAvgSizeZone] = rootavgsize
     
        #add metric VMs per hypervisor
        for h in hypervisors:
            virtualMachineHTotalCount = 0
            metricnameVmHTotal = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'hvmtotal' ])
            metricnameVmHTotalRunning = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'hvmtotalrunning' ])
            metricnameVmHTotalStarting = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'hvmtotalstarting' ])
            metricnameVmHTotalStopping = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'hvmtotalstopping' ])
            metricnameVmHTotalStopped = METRIC_DELIM.join([ h['name'].lower(), h['podname'].lower(), re.sub(r"\s+", '-', h['zonename'].lower()), 'hvmtotalstopped' ])

            hname = h['name'].lower()
            if hname in hvmrunning:
                virtualMachineHTotalCount = virtualMachineHTotalCount + hvmrunning[hname]
                stats[metricnameVmHTotalRunning] = hvmrunning[hname]
            else:
                stats[metricnameVmHTotalRunning] = 0
            if hname in hvmstarting:
                virtualMachineHTotalCount = virtualMachineHTotalCount + hvmstarting[hname]
                stats[metricnameVmHTotalStarting] = hvmstarting[hname]
            else:
                stats[metricnameVmHTotalStarting] = 0
            if hname in hvmstopping:
                virtualMachineHTotalCount = virtualMachineHTotalCount + hvmstopping[hname]
                stats[metricnameVmHTotalStopping] = hvmstopping[hname]
            else:
                stats[metricnameVmHTotalStopping] = 0
            if hname in hvmstopped:
                virtualMachineHTotalCount = virtualMachineHTotalCount + hvmstopped[hname]
                stats[metricnameVmHTotalStopped] = hvmstopped[hname]
            else:
                stats[metricnameVmHTotalStopped] = 0
            
            stats[metricnameVmHTotal] = virtualMachineHTotalCount


        for capacity in zone['capacity']:
            if capacity['type'] == 8:
                stats[metricnameIpTotal] = capacity['capacitytotal']
                stats[metricnameIpAllocated] = capacity['capacityused']
                stats[metricnameIpAllocatedPercent] = capacity['percentused']

    stats[metricnameZonesCount] = len(zones)
    stats[metricnameHostZoneTotal] = len(hypervisors)
 

  # collect accounts
    try:
        logger('verb', "Performing listAccounts API call")
        query_tmp = None
        querypage = 1
        querypagesize = 500
        accounts = cloudstack.listAccounts({
                    'listall': 'true',
                    'page': str(querypage),
                    'pagesize': str(querypagesize)
                    })
        all_accounts = []
        if len(accounts) == querypagesize:
            query_tmp = accounts
            while len(query_tmp) > 1:
                all_accounts.extend(query_tmp)
                querypage = querypage + 1
                query_tmp = cloudstack.listAccounts({
                            'listall': 'true',
                            'page': str(querypage),
                            'pagesize': str(querypagesize)
                            })
        else:
            all_accounts.extend(accounts)
        accounts = all_accounts
        logger('verb', "Completed listAccounts API call")
    except:
        print("status err Unable to connect to CloudStack URL at %s for ListAccounts")

    metricnameAccountsTotal = METRIC_DELIM.join([ 'accounts',  'accountscount' ])
    metricnameAccountsTotalEnabled = METRIC_DELIM.join([ 'accounts',  'accountenabled' ])
    metricnameAccountsTotalDisabled = METRIC_DELIM.join([ 'accounts',  'accountdisabled' ])
    accountsEnabledCount = 0
    accountsDisabledCount = 0

    for account in accounts:
        if account['state'] == 'enabled':
            accountsEnabledCount = accountsEnabledCount + 1
        elif account['state'] == 'disabled':
            accountsDisabledCount = accountsDisabledCount + 1

    stats[metricnameAccountsTotal] = len(accounts)
    stats[metricnameAccountsTotalEnabled] = accountsEnabledCount
    stats[metricnameAccountsTotalDisabled] = accountsDisabledCount

  # collect capacity
    try:
        capacity = cloudstack.listCapacity()
    except:
        print("status err Unable to connect to CloudStack URL at %s for ListCapacity")


    for c in capacity['capacity']:
        if c['type'] == 0:
            metricnameCapaZoneMemoryTotal = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapamemorytotal' ])
            metricnameCapaZoneMemoryUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapamemoryused' ])
            metricnameCapaZoneMemoryPercentUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapamemorypercentused' ])
            stats[metricnameCapaZoneMemoryTotal] = c['capacitytotal']
            stats[metricnameCapaZoneMemoryUsed] = c['capacityused']
            stats[metricnameCapaZoneMemoryPercentUsed] = c['percentused']
        elif c['type'] == 1:
            metricnameCapaZoneCpuTotal = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapacputotal' ])
            metricnameCapaZoneCpuUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapacpuused' ])
            metricnameCapaZoneCpuPercentUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapacpupercentused' ])
            stats[metricnameCapaZoneCpuTotal] = c['capacitytotal']
            stats[metricnameCapaZoneCpuUsed] = c['capacityused']
            stats[metricnameCapaZoneCpuPercentUsed] = c['percentused']
        elif c['type'] == 2:
            metricnameCapaZoneDiskTotal = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapadisktotal' ])
            metricnameCapaZoneDiskUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapadiskused' ])
            metricnameCapaZoneDiskPercentUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapadiskpercentused' ])
            stats[metricnameCapaZoneDiskTotal] = c['capacitytotal']
            stats[metricnameCapaZoneDiskUsed] = c['capacityused']
            stats[metricnameCapaZoneDiskPercentUsed] = c['percentused']
        elif c['type'] == 5:
            metricnameCapaZonePrivateipTotal = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapaprivateiptotal' ])
            metricnameCapaZonePrivateipUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapaprivateipused' ])
            metricnameCapaZonePrivateipPercentUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapaprivateippercentused' ])
            stats[metricnameCapaZonePrivateipTotal] = c['capacitytotal']
            stats[metricnameCapaZonePrivateipUsed] = c['capacityused']
            stats[metricnameCapaZonePrivateipPercentUsed] = c['percentused']
        elif c['type'] == 6:
            metricnameCapaZoneSSTotal = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapasstotal' ])
            metricnameCapaZoneSSUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapassused' ])
            metricnameCapaZoneSSPercentUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapasspercentused' ])
            stats[metricnameCapaZoneSSTotal] = c['capacitytotal']
            stats[metricnameCapaZoneSSUsed] = c['capacityused']
            stats[metricnameCapaZoneSSPercentUsed] = c['percentused']
        elif c['type'] == 9:
            metricnameCapaZoneDiskAllocTotal = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapadiskalloctotal' ])
            metricnameCapaZoneDiskAllocUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapadiskallocused' ])
            metricnameCapaZoneDiskAllocPercentUsed = METRIC_DELIM.join([ 'zonecapacity', c['zonename'].lower(),  'zonecapadiskallocpercentused' ])
            stats[metricnameCapaZoneDiskAllocTotal] = c['capacitytotal']
            stats[metricnameCapaZoneDiskAllocUsed] = c['capacityused']
            stats[metricnameCapaZoneDiskAllocPercentUsed] = c['percentused']

  # collect async jobs
  # disabled as doing it from database in a separate script
    #try:
  #      logger('verb', "Performing listAsyncJobs API call")
  #      query_tmp = None
  #     querypage = 1
  #     querypagesize = 500
  #     jobs = cloudstack.listAsyncJobs({
  #              'listall': 'true',
  #              'page': str(querypage),
  #              'pagesize': str(querypagesize)
  #              })
  #     all_jobs = []
  #     if len(jobs) == querypagesize:
  #     query_tmp = jobs
  #         while len(query_tmp) > 1:
  #             all_jobs.extend(query_tmp)
  #             querypage = querypage + 1
  #             query_tmp = cloudstack.listAsyncJobs({
  #                         'listall': 'true',
  #                         'page': str(querypage),
  #                         'pagesize': str(querypagesize)
  #                         })
  #     else:
  #         all_jobs.extend(jobs)
  #     jobs = all_jobs
  #     logger('verb', "Completed listAsyncJobs API call")
  # except:
  #     print("status err Unable to connect to CloudStack URL at %s for listAsyncJobs")
  #
  # metricnameJobsCount = METRIC_DELIM.join([ 'asyncjobscount',  'asyncjobscount' ])
  # stats[metricnameJobsCount] = len(jobs)

    time.sleep(SLEEPTIME)  
    return stats

# callback configuration for module
def configure_callback(conf):
    global API_MONITORS, APIKEY_MONITORS, SECRET_MONITORS, AUTH_MONITORS, VERBOSE_LOGGING, SLEEPTIME
    API_MONITORS = '' 
    APIKEY_MONITORS = ''
    SECRET_MONITORS = ''
    AUTH_MONITORS = DEFAULT_AUTH
    VERBOSE_LOGGING = False
    SLEEPTIME = 300

    for node in conf.children:
        if node.key == "Api":
            API_MONITORS = node.values[0]
        elif node.key == "ApiKey":
            APIKEY_MONITORS = node.values[0]
        elif node.key == "Secret":
            SECRET_MONITORS = node.values[0]
        elif node.key == "Auth":
            AUTH_MONITORS = node.values[0]
        elif node.key == "Verbose":
            VERBOSE_LOGGING = bool(node.values[0])
        else:
            logger('warn', 'Unknown config key: %s' % node.key)

    if not API_MONITORS:
        API_MONITORS += DEFAULT_API

def read_callback():
    logger('verb', "beginning read_callback")
    info = get_stats()

    if not info:
        logger('warn', "%s: No data received" % NAME)
        return

    for key,value in info.items():
        key_prefix = ''
        key_root = key
        logger('verb', "read_callback key %s" % (key))
        logger('verb', "read_callback value %s" % (value))
        if not value in METRIC_TYPES:
            try:
                key_prefix, key_root = key.rsplit(METRIC_DELIM,1)
            except ValueError, e:
                pass
        if not key_root in METRIC_TYPES:
            continue

        key_root, val_type = METRIC_TYPES[key_root]
        key_name = METRIC_DELIM.join([key_prefix, key_root])
        logger('verb', "key_name %s" % (key_name))
        val = collectd.Values(plugin=NAME, type=val_type)
        val.type_instance = key_name
        val.values = [ value ]
        val.dispatch()


# logging function
def logger(t, msg):
    if t == 'err':
        collectd.error('%s: %s' % (NAME, msg))
    elif t == 'warn':
        collectd.warning('%s: %s' % (NAME, msg))
    elif t == 'verb':
        if VERBOSE_LOGGING:
            collectd.info('%s: %s' % (NAME, msg))
    else:
        collectd.notice('%s: %s' % (NAME, msg))
# main
collectd.register_config(configure_callback)
collectd.register_read(read_callback)
