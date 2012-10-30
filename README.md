collectd-cloudstack
================
This is a plugin for collecting stats from the CloudStack API. It can get information about zones, pods, storage, clusters and hosts.
It requires the python plugin in collectd in order to gather data.

Requirements
------------

*CloudStack*  
In order to use this module, you need to have a valid API access on the root domain. This module has been tested and developped against CloudStack 3.0.x API.

*collectd*  
collectd must have the Python plugin installed. See (<http://collectd.org/documentation/manpages/collectd-python.5.shtml>)

Options
-------
* `Api`  
URL of cloudstack API to monitor and the TCP on which your API runs
* `Auth`  
Wether your API is protected or not. Default unprotected API listens on 8096 on CloudStack
* `ApiKey`  
API key from an account on the root level.
* `Secret`  
Associated API Secret from the account.
* `Verbose`  
Vervose logging. Default to false.

Example
-------
    <LoadPlugin python>
        Globals true
    </LoadPlugin>

    <Plugin python>
        # cloudstack.py is at /usr/lib/collectd/cloudstack.py
        ModulePath "/usr/lib64/collectd/"

        Import "cloudstack"

        <Module cloudstack>
          Api "https://mycloudstack.com:443/client/api"
	  Auth "True"
	  ApiKey "RANDOM-KEY-FROM-CS"
	  Secret "SECRET-FROM-CS"
	</Module>
    </Plugin>

