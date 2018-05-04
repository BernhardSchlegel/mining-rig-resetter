import datetime         # converting ints to datestrings
import json             # decompiling json
import os               # executing other python script
import threading        # execute mainloop cyclically
import requests
import time
import csv


from socket import error as SocketError

# Settings
setting_time_before_first_run_min = 5  # time in minutes before main loop is executed for the first time
setting_main_cycle_time_min = 1        # every X minutes all rigs will be checked
settings_on_queue_cycle_s = 5          # every X seconds queue will be checked if there are rigs to be turned on again

# Globals
first_main_loop_iteration = True       # True for first iteration, False else
pools = []          # pools, holds all infos about pools, atm only the adress. As well as all information about
                    # the rigs like name, ip, last reset
turn_on_queue = []  # rigs that are off, that are scheduled to be turned on again
                    # objects are shaped {name: 'rig1', ip: '192.168.178.2', ts: 1501376201}


"""
logs to the file
"""
def log_file(level, type, rig, value):
    now = datetime.datetime.now()
    row = [now.strftime("%Y-%m-%d %H:%M"), level, type, rig, value]
    with open('log.csv', 'a') as f:
        w = csv.writer(f)
        w.writerow(row)

"""
logs to the console
"""
def log_console(level, type, rig, value):
    now = datetime.datetime.now()
    print(now.strftime("%Y-%m-%d %H:%M") + " [" + level + "]: " + type + ", " + rig + ", " + value)

"""
Logs a info to the csv logfile and prints it to the console.
"""
def log_info(type, rig, value):
    log_file('INFO', type, rig, value)
    log_console('INFO', type, rig, value)

"""
Logs a warning to the csv logfile and prints it to the console.
"""
def log_warn(type, rig, value):
    log_file('WARN', type, rig, value)
    log_console('WARN', type, rig, value)


"""
Sends to command to the smart plug.
what should be executed is 'python tplink-smartplug.py -t 192.168.178.10 -c on'
"""
def dropCommand(ip, cmd):
    # TODO: call asynchronously
    # from subprocess import Popen
    # p = Popen(['python2', '\"' + path_to_py + '\" -t ' + ip + ' -c ' + cmd])  # something long running

    path_to_py = os.path.join(os.getcwd(), "tplink-smartplug.py")
    os.system('python2 \"' + path_to_py + '\" -t ' + ip + ' -c ' + cmd)


"""
This is the main function - checking rigs according to timeouts and grace periods.
"""
def check_rigs(data, rigs):
    global turn_on_queue

    for rig in rigs:

        ts_current_time = round(time.time())

        result = data
        rig_in_json = False

        # get corresponding result from json
        for rig_result in data["data"]:
            if rig_result[rig["name_field"]] == rig["name"]:
                result = rig_result[rig["time_field"]]
                rig_in_json = True
                break

        # not found
        if not rig_in_json:
            # rig is not in the config file
            log_warn('rig_not_in_json', rig['name'], '')
            result = 0

        rig['ts_last_alive'] = result

        if result is None: # not 'ts_last_alive' in rig.keys():
            # rig is not in the json server response
            rig['ts_last_alive'] = 0

        log_console('INFO', 'alive', rig['name'], 'last alive signal from worker {} was at {} - {} minutes ago.'.format(
            rig['name'], rig['ts_last_alive'], round((ts_current_time-rig['ts_last_alive'])/60)))

        log_info('last_alive', rig['name'], str(round((ts_current_time-rig['ts_last_alive'])/60)))

        # check if rig needs reset
        rig_needs_reset = False
        if (rig_in_json is False or rig['ts_last_alive'] + rig['timeout'] * 60) < ts_current_time:
            log_info('worker_down', rig['name'], str(rig['last_reset']))
            rig_needs_reset = True

        # check if grace is violated
        rig_reset = False
        rig_is_in_grace_periode = (rig['last_reset'] + rig['grace'] * 60) > ts_current_time
        if rig_needs_reset and not rig_is_in_grace_periode:
            rig_reset = True
        elif rig_needs_reset and rig_is_in_grace_periode:
            log_warn('grace_violated', rig['name'], str(rig['last_reset']))

        # check if it needs to be rebooted
        if rig_reset:
            log_info('reset', rig['name'], '')
            log_info('uptime', rig['name'], str(ts_current_time - rig['last_reset']))
            dropCommand(rig['ip'], 'off')
            log_info('switch_off', rig['name'], '')
            turn_on_queue.append(
                {'name': rig['name'],
                 'ip': rig['ip'],
                 'ts': ts_current_time + rig['distance']}
            )
            rig['last_reset'] = ts_current_time

        rig['last_check'] = round(time.time())

"""
This loop will check the queue if there are rigs that need to be turned on
"""
def check_on_queue():
    global turn_on_queue

    turn_on_queue_copy = turn_on_queue.copy()
    ts_current_time = round(time.time())

    for task in turn_on_queue_copy:
        if task['ts'] < ts_current_time:
            dropCommand(task['ip'], 'on')
            turn_on_queue.remove(task)
            log_info('switch_on', task['name'], '')

    threading.Timer(settings_on_queue_cycle_s, check_on_queue).start()


"""
This loop will do all checkings and shut down the rigs
"""
def main_loop():
    global first_main_loop_iteration

    distance_next_time = setting_main_cycle_time_min * 60

    if first_main_loop_iteration:
        if setting_time_before_first_run_min > 0:
            distance_next_time = setting_time_before_first_run_min * 60
        else:
            distance_next_time = 1

        first_main_loop_iteration = False
        log_info('skipped', 'general',
                 'first iteration skipped. next will be in {} minutes.'.format(setting_time_before_first_run_min))
    else:
        try:
            for pool in pools:
                # get last alive from api
                response = requests.get(pool['json_url'])
                data = json.loads(response.content.decode())

                check_rigs(data, pool['rigs'])

        except SocketError as e:
            log_warn('error', 'main_loop', str(e))
            pass  # continue after exception

    threading.Timer(distance_next_time, main_loop).start()

# read in configuration JSON
def field_exists(field_name, json, target = 'general'):
    if field_name not in json:
        msg = field_name + ' missing'
        log_warn('conf_error', target, msg)
        raise ValueError('Bad config: ' + msg)
        return False
    else:
        return True

with open('config.json') as conf_file:
    conf_json = json.load(conf_file)

    # general settings
    field_name = 'time_before_first_run_min'
    if field_exists(field_name, conf_json):
        setting_time_before_first_run_min = conf_json[field_name]

    field_name = 'main_cycle_time_minutes'
    if field_exists(field_name, conf_json):
        setting_main_cycle_time_min = conf_json[field_name]

    field_name = 'on_queue_cycle_seconds'
    if field_exists(field_name, conf_json):
        settings_on_queue_cycle_s = conf_json[field_name]

    # pool setup
    field_name = 'pools'
    pool_id = 1
    if field_exists(field_name, conf_json):
        for pool in conf_json[field_name]:
            field_name = 'json_url'
            if field_exists(field_name, pool):
                temp_json_url = pool[field_name]

            temp_pool_id = pool_id
            pool_id += 1
            temp_rigs = []

            # rig setup
            field_name = 'rigs'
            if field_exists(field_name, pool):
                for object in pool[field_name]:
                    field_name = 'name'
                    if field_exists(field_name, object):
                        temp_name = object[field_name]

                    field_name = 'name_field'
                    if field_exists(field_name, object, target=temp_name):
                        temp_name_field = object[field_name]

                    field_name = 'time_field'
                    if field_exists(field_name, object, target=temp_name):
                        temp_time_field = object[field_name]

                    field_name = 'ip'
                    if field_exists(field_name, object, target=temp_name):
                        temp_ip = object[field_name]

                    field_name = 'timeout_minutes'
                    if field_exists(field_name, object, target=temp_name):
                        temp_timeout = object[field_name]

                    field_name = 'distance_seconds'
                    if field_exists(field_name, object, target=temp_name):
                        temp_distance = object[field_name]

                    field_name = 'grace_minutes'
                    if field_exists(field_name, object, target=temp_name):
                        temp_grace = object[field_name]

                    temp_rig = {'name': temp_name,
                                'name_field': temp_name_field,
                                'time_field': temp_time_field,
                                'ip': temp_ip,
                                'timeout': temp_timeout,  # minutes
                                'distance': temp_distance,  # seconds
                                'grace': temp_grace}  # minutes

                    log_info('rig_init', temp_name, 'name_field={}, time_field={}, ip={}, '
                                                    'timeout={}, distance={}, grace={}'.format(temp_name_field,
                                                                                               temp_time_field,
                                                                                               temp_ip,
                                                                                               temp_timeout,
                                                                                               temp_distance,
                                                                                               temp_grace))
                    temp_rig['last_reset'] = round(time.time()) - 60 * 60
                    temp_rig['last_check'] = round(time.time()) - 60 * 60
                    temp_rigs.append(temp_rig)

            temp_pool = {'json_url': temp_json_url,
                         'pool_id': temp_pool_id,
                         'rigs': temp_rigs}
            pools.append(temp_pool)
            log_info('pool_init', str(temp_pool_id), 'json_url={}, num_of_rigs={}'.format(temp_json_url, len(temp_rigs)))

# execute loops
log_info('startup', 'general', 'rig-resetter v.1.1 initialized')
main_loop()
check_on_queue()
