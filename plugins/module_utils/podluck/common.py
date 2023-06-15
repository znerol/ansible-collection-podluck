import errno
import getpass
import os
import pwd
import shlex
import tempfile

from ansible.module_utils._text import to_text


def config_get_base_dir():
    """
    Returns path to config dir.

    Either /etc or ~/.config depending whether or not the module is runnig as
    root or as an unprivileged user.
    """
    pwent = pwd.getpwnam(getpass.getuser())
    if (pwent.pw_uid == 0):
        return '/etc'
    else:
        return os.path.join(pwent.pw_dir, '.config')


def config_get_pod_dir(pod_name):
    """
    Returns path to pod config dir.

    Either /etc/podluck/pod/%pod_name or ~/.config/podluck/pod/%pod_name
    depending whether or not the module is running as root or as an
    unprivileged user.
    """
    return os.path.join(config_get_base_dir(), 'podluck', 'pod', pod_name)


def check_file_attrs(module, changed, message, diff):

    file_args = module.load_file_common_arguments(module.params)
    if module.set_fs_attributes_if_different(file_args, False, diff=diff):

        if changed:
            message += " and "
        changed = True
        message += "ownership, perms or SE linux context changed"

    return message, changed


def file_cleanup(path, result=None):
    # cleanup just in case
    if os.path.exists(path):
        try:
            os.remove(path)
        except (IOError, OSError) as e:
            # don't error on possible race conditions, but keep warning
            if result is not None:
                result['warnings'] = [
                    'Unable to remove temp file (%s): %s' % (path, e)]


def generate_env_content(vars):
    lines = []
    for key, args in vars.items():
        value = ' '.join(shlex.quote(to_text(arg)) for arg in args)
        lines.append(f'{key}={value}\n')
    return ''.join(lines)


def file_ensure_content(module, content):
    changed = False
    path_hash = None
    dest_hash = None
    backup = module.params['backup']

    dest = module.params['path']
    result = {
        'path': dest,
        'state': 'present'
    }

    diff = {
      'before_header': dest,
      'before': ''
    }
    if os.path.exists(dest):
        dest_hash = module.sha1(dest)
        with open(dest, 'r') as existing:
            diff['before'] = ''.join(existing.readlines())

    with tempfile.NamedTemporaryFile(
            mode='w', dir=module.tmpdir, delete=False) as envfile:
        envfile.write(content)

    diff['after_header'] = envfile.name
    diff['after'] = content

    path_hash = module.sha1(envfile.name)
    result['checksum'] = path_hash

    if path_hash != dest_hash:
        if not module.check_mode:
            if backup and dest_hash is not None:
                result['backup_file'] = module.backup_local(dest)

            os.makedirs(os.path.dirname(dest), exist_ok=True)
            module.atomic_move(
                envfile.name,
                dest,
                unsafe_writes=module.params['unsafe_writes']
            )

        changed = True
        msg = 'file changed'
    else:
        msg = 'file up-to-date'

    file_cleanup(envfile.name, result)

    if module.check_mode and not os.path.exists(dest):
        result['diff'] = diff
        result['msg'] = msg
        result['changed'] = changed
    else:
        attr_diff = {}
        msg, changed = check_file_attrs(module, changed, msg, attr_diff)

        attr_diff['before_header'] = '%s (file attributes)' % dest
        attr_diff['after_header'] = '%s (file attributes)' % dest

        difflist = [diff, attr_diff]
        result['diff'] = difflist
        result['msg'] = msg
        result['changed'] = changed

    return result


def file_ensure_absent(module):
    dest = module.params['path']
    result = {
        'path': dest,
        'changed': False,
        'state': 'absent'
    }

    if os.path.exists(dest):

        if not module.check_mode:
            try:
                os.unlink(dest)
            except OSError as e:
                if e.errno != errno.ENOENT:  # It may already have been removed
                    raise e

        result.update({
            'changed': True,
            'diff': {
                'before': {
                    'path': dest,
                    'state': 'present',
                },
                'after': {
                    'path': dest,
                    'state': 'absent',
                },
            },
            'state': 'absent'
        })

    return result

def podman_get_version(module):
    # pylint: disable=unused-variable
    rc, out, err = module.run_command(['podman', b'--version'])
    if rc != 0 or not out or "version" not in out:
        module.fail_json(msg="%s run failed!" % 'podman')
    return out.split("version")[1].strip()
