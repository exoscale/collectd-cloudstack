#!/usr/bin/python

# collectd-cloudstack - csinstancesstats.py
#
# Author : Loic Lambiel @ exoscale
# Description : This is a collectd python module to gather the total spawned instances on cloudstack


import MySQLdb
import sys

RUN = 0

def get_nb_instances(dbhost, user, pwd, database):
    if not (dbhost and user and pwd and database):
        logger('error', "empty parameter, dbhost: %s , user: %s , pwd: %s , database: %s" % (dbhost, user, pwd, database))
        sys.exit(1)
    try:
        QUERYNBINSTANCES = "SELECT id FROM cloud.vm_instance where type like 'User';"
        con = MySQLdb.connect(dbhost, user, pwd, database)
        cursor = con.cursor()
        cursor.execute(QUERYNBINSTANCES)
        querycount = cursor.rowcount
        CSStats = {}
        CSStats['nbinstances'] = querycount
        return CSStats

    except ValueError as e:
        logger('error', "Error during mysql query: %s" % e)
        sys.exit(1)

    finally:
        if con:
            con.close()


try:
    import collectd

    NAME = "cloudstack"
    VERBOSE_LOGGING = False
    SKIP = 10

    dbhost = ""
    user = ""
    pwd = ""
    database = ""

    def config_callback(conf):
        global dbhost, user, pwd, database, VERBOSE_LOGGING, SKIP
        for node in conf.children:
            logger('verb', "Node key: %s and value %s" % (node.key, node.values[0]))
            if node.key == "DbHost":
                dbhost = node.values[0]
            elif node.key == "User":
                user = node.values[0]
            elif node.key == "Pwd":
                pwd = node.values[0]
            elif node.key == "Database":
                database = node.values[0]
            elif node.key == "Verbose":
                VERBOSE_LOGGING = bool(node.values[0])
            elif node.key == "Skip":
                SKIP = int(node.values[0])
            else:
                logger('warn', "unknown config key in puppet module: %s" % node.key)

    def read_callback():
        global RUN, SKIP
        RUN += 1
        if RUN % SKIP != 1:
            return
        cs_stats = get_nb_instances(dbhost, user, pwd, database)
        val = collectd.Values(plugin=NAME, type="gauge")
        val.values = [cs_stats['nbinstances']]
        logger('verb', "Nb of instances: %s" % cs_stats['nbinstances'])
        val.type_instance = "total-created-instances"
        val.type = "gauge"
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

    collectd.register_config(config_callback)
    collectd.register_read(read_callback)


except ImportError:
    # we're not running inside collectd
    # it's ok
    pass

if __name__ == "__main__":
    dbhost = sys.argv[1]
    user = sys.argv[2]
    pwd = sys.argv[3]
    database = sys.argv[4]
    cs_stats = get_nb_instances(dbhost, user, pwd, database)

    print "The number of instances is %s" % (cs_stats['nbinstances'])
