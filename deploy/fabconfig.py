"""
example of command line activation: fab target:dev deploy
"""
import os
from fabric.api import local, abort
from .daemon_runner import DaemonRunner, DaemonRunnerException, DaemonDefinition
import time
import posixpath

TARGETS = {
    'production' : {
        'HOST' : 'chatsummit@galhochberg.com',
        'BASE_DIR' : '/home/chatsummit/chatsummit/globalfacetime',
        'VENV_LOCATION': '/home/chatsummit/chatsummit/venv',
        'PID_DIR': '/home/chatsummit/chatsummit/storage',
        'GIT_BRANCH' : 'master',
        'LISTEN_PORT': 80,
        },
    }

def use_root(f):
    f.use_root = True
    return f

def service_command(f):
    f.is_service_command = True
    return f

# Don't want to fork or such, as we want to run in the same process to get the signals (kill)
def _run_script(directory,filename,func_name,*args,**kwargs):
    import signal

    def handle_sigterm(signum,frame):
        raise KeyboardInterrupt() # Turn SIGTERM into a Keyboard Interrupt to kill our processes

    signal.signal(signal.SIGTERM, handle_sigterm)

    import os
    os.chdir(directory)

    import sys
    sys.path.append(os.path.join(directory, filename))

    local(func_name)

    # g = {}
    # execfile(os.path.join(directory, filename), g)

    # g[func_name](*args, **kwargs)

def _get_daemon_runner(server_config):
    service_name = 'moriarty_'+server_config['NAME']
    log_directory = os.path.join(server_config['BASE_DIR'],'logs')
    user = server_config.get('GID', None)
    group = server_config.get('GID', None)
    umask = server_config.get('UMASK', None)

    return DaemonRunner(service_name, log_directory, user, group, server_config.get('PID_DIR', None), umask)

@use_root
@service_command
def stop(server_config, params):
    """
    kill all processes that have supersloth in them
    @param params a dict of parameters from the command line to be used by the script
    """

    daemon_runner = _get_daemon_runner(server_config)
    try:
        daemon_runner.stop(include_children=True) # Stop the daemons
    except DaemonRunnerException, e:
        abort('STOP FAILED: %s'%e)

    if not daemon_runner.verify_stopped():
        abort('STOP FAILED: Could not stop all processes.')

    print "Stop... Successful"

@use_root
@service_command
def install(server_config, params):
    # If using sudo, we have to run our own virtualenv
    command = 'pip install -r requirements.txt'

    if 'VENV_LOCATION' in server_config:
        command = 'source %s && %s'%(posixpath.join(server_config['VENV_LOCATION'],'bin/activate'),command)

    local(command)

    # Lets also install setproctitle to get the nice proc titles
    command = 'pip install setproctitle'

    if 'VENV_LOCATION' in server_config:
        command = 'source %s && %s' % (posixpath.join(server_config['VENV_LOCATION'],'bin/activate'),command)

    local(command)

    # Compile all .pys to .pycs in the non-root user
    command = 'python -m compileall .'

    if 'VENV_LOCATION' in server_config:
        command = 'source %s && %s' % (posixpath.join(server_config['VENV_LOCATION'],'bin/activate'),command)

    local(command)

    # Run a DB migration
    # If using sudo, we have to run our own virtualenv
    if 'VENV_LOCATION' in server_config:
        command = '%s %s migrate' % (os.path.join(server_config['VENV_LOCATION'], 'bin', 'python'), os.path.join(server_config['BASE_DIR'], 'moriarty', 'manage.py'))
    else:
        command = 'python %s migrate' %  os.path.join(server_config['BASE_DIR'], 'moriarty', 'manage.py')


    # This assumes the deploy user has sudo permissions
    # This is because migrate needs to touch the storage dir
    # Which means we have to su into it
    # Which we need to be root to do - but we don't want to be root

    # TODO: Find a way around this
    if 'UID' in server_config:
        command = 'sudo -u %s HIREDSCORE_ENVIRONMENT=$HIREDSCORE_ENVIRONMENT %s' % (server_config['UID'], command)

    local(command)


@use_root
@service_command
def start(server_config, params):
    """
    start screenit inside venv
    @param params a dict of parameters from the command line to be used by the script
    """
    daemons = []
    daemons.append(DaemonDefinition('moriarty', _run_script, os.path.join(server_config['BASE_DIR'], 'moriarty'),
                                    'manage.py', 'python manage.py runserver 0.0.0.0:%s --noreload'%server_config.get('LISTEN_PORT',80)))

    daemon_runner = _get_daemon_runner(server_config)

    try:
        daemon_runner.start(daemons) # Start the daemons
    except DaemonRunnerException, e:
        abort('START FAILED: %s' % e)

    # Wait for them to spin up
    time.sleep(1)

    try:
        daemon_runner.verify({'moriarty': 1})
    except DaemonRunnerException,e:
        abort('START VERIFICATION FAILED: %s'%e)

    print "Start... Successful"

@use_root
@service_command
def backup(server_config, params):
    """
    backup the system if needed
    """
    pass

@use_root
@service_command
def verify(server_config, params):
    """
    verify that the deploy worked
    @param params a dict of parameters from the command line to be used by the script
    """
    daemon_runner = _get_daemon_runner(server_config)

    try:
        daemon_runner.verify({'moriarty':1}) # Verify they were started
    except DaemonRunnerException,e:
        abort('VERIFICATION FAILED: %s'%e)

    print "VERIFICATION SUCCESSFUL! system is up!"

@use_root
@service_command
def restart(server_config, params):
    stop(server_config, params)
    start(server_config, params)