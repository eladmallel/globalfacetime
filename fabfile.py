from fabric.api import *
from fabric.contrib.console import confirm
from deploy import fabconfig
import json
import os
import posixpath

TARGET_DEFAULT = {
    'GIT_BRANCH' : 'master',
}

env.hosts = []

_target_server = None

@task
def bastion():
    _precondition_validation('')

    if 'BASTION_SERVER' not in _target_server:
        warn('Target %s does not have a configured bastion server. Skipping bastion.'%_target_server['NAME'])
    else:
        env.gateway = _target_server['BASTION_SERVER']

@task
def target(name):
    """
    Set the target for the deploy, this task has to run before the deploy task.
    The options for the targets are part of the fabconfig.py file that the project has to set.
    """
    global _target_server
    try:
        _target_server = TARGET_DEFAULT.copy()
        _target_server.update(fabconfig.TARGETS[name])
        _target_server['NAME'] = name
    except KeyError:
        abort('target %s not found, try one of the following: %s' % (name, fabconfig.TARGETS.keys()))

    env.hosts += [_target_server['HOST']]
    if 'KEY_FILENAME' in _target_server:
        env.key_filename = _target_server['KEY_FILENAME']

@task
def restart(params=''):
    params = _precondition_validation(params)
    service('restart',params)

@task
def start(params=''):
    params = _precondition_validation(params)
    service('start',params)

@task
def stop(params=''):
    params = _precondition_validation(params)
    service('stop',params)

@task
def backup(params=''):
    params = _precondition_validation(params)
    service('backup',params)


def _get_service_action(action_name):
    if hasattr(fabconfig, action_name):
        action = getattr(fabconfig, action_name)
        if hasattr(action, 'is_service_command') and action.is_service_command:
            return action

    return None

def _action_needs_root(action):
    return hasattr(action, 'use_root') and action.use_root and _target_server.get('SERVICE_NEEDS_ROOT', False)

def _run_local_service(action_name, params_dict):
    action = _get_service_action(action_name)

    if action is None:
        return False

    if _action_needs_root(action) and os.getuid() != 0:
        abort('This service needs root to %s - Please re-run under root' % action_name)

    action(_target_server, params_dict)

    return True

# This runs locally on the target server
@task
def local_service(action, params=''):
    params = _precondition_validation(params)

    # Change directory to the target
    os.chdir(_target_server.get('SERVER_DIR', _target_server['BASE_DIR']))

    params_dict = _parse_params(params)

    if not _run_local_service(action, params_dict):
        print "action not found"

# This runs remotely
@task
def service(action,params=''):
    params = _precondition_validation(params)
    with cd(_target_server.get('SERVER_DIR', _target_server['BASE_DIR'])):
        command = 'fab target:%s local_service:action=%s,params="%s"'%(_target_server['NAME'],action,params)

        if 'VENV_LOCATION' in _target_server:
            command = 'source %s && %s'%(posixpath.join(_target_server['VENV_LOCATION'],'bin/activate'),command) # Use posixpath, as we're running on a linux target

        # Check if this action needs root
        action_f = _get_service_action(action)
        if action_f is None:
            abort('Action %s not a valid action' % action)

        if _action_needs_root(action_f):
            sudo(command)
        else:
            run(command)

@task
def deploy(params=''):
    """
    The deploy task makes sure we have a target set (using the target task) and then deploys the project to the server
    using the following steps:
        1) connect to remote server
        2) open project directory
        3) git checkout branch and then git pull
        4) fabconfig.stop() - to stop the current running process
        5) fabconfig.install() - to install the any new needed setups (e.g. pip install)
        6) fabconfig.start() - to start the new updated process
    @param params a json of parameters for thee deploy function
    """
    params = _precondition_validation(params)
    with cd(_target_server['BASE_DIR']):
        service('stop', params)
        service('backup', params)
        _git_pull()
        service('install', params)
        service('start', params)
        service('verify', params)

@task
def test():
    local('nosetests')

def _parse_params(params):
    params_dict = {}
    if params:
        # replacing ' with " for json compatability
        params = params.replace("'", '"')
        params_dict = json.loads(params)
    return params_dict

def _add_param(params, key, value):
    """
    Add a new parameter into a parameters string and return a string
    """
    params_dict = {}
    if params:
        params_dict = json.loads(params)
    params_dict[key] = value
    # replacing " with ' for easier escaping when passing parameters to the server command line
    return json.dumps(params_dict).replace('"', "'")

def _precondition_validation(params):
    if _target_server is None:
        abort('no target set, please use target:[name] with one of these options: %s' % fabconfig.TARGETS.keys())

    if 'WARNING' in _target_server:
        if not 'skip_warning' in params:
            if confirm(_target_server['WARNING']):
                params = _add_param(params, 'skip_warning', True)
            else:
                abort("Aborting at user request")
    return params

def _git_pull():
    if _target_server.get('INSTALLED_AS_ROOT', False):
        _remote_run = sudo
    else:
        _remote_run = run

    branch = _target_server.get('GIT_BRANCH')
    with settings(warn_only=True):
        if _remote_run("git checkout %s" % branch).return_code != 0:
            _remote_run("git fetch origin %s:%s" % (branch, branch))
    _remote_run("git checkout %s" % branch)
    _remote_run("git pull origin %s" % branch)
