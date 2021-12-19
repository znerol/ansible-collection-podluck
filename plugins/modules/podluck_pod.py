#!/usr/bin/python
# Copyright (c) 2021 Lorenz Schori
#
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r'''
module: podluck_pod
author:
  - "Lorenz Schori"
version_added: '1.0.0'
short_description: Configure podman pods managed by systemd
description:
  - Install and remove configuration for Podman pods managed by systemd
requirements:
  - containers.podman
  - Python 3.6 or better
options:
  name:
    description:
      - Name of the pod
    required: True
    type: str
  path:
    description:
      - >-
        Path to the pod configuration file. Use the defaults, since this
        is what the `podluck-service.service` systemd unit expects.
      - >-
        Defaults to `/etc/podluck/pod/{{ name }}/systemd-pod-env`
        when module is executed as I(root).
      - >-
        Defaults to `~/.config/podluck/pod/{{ name }}/systemd-pod-env`
        when module is executed as an unprivileged user.
    type: str
  state:
    description:
      - >-
        I(absent) - A podluck configuration file for the pod in the is unlinked
        if it exists.
      - >-
        I(present) - A podluck configuration file for the pod in the is created
        and populated with cli arguments matching the desired configuration.
        Returns `changed: True` if existing configuration does not match the
        current config. The calling playbook / role is responsible for
        restarting the pod if necessary.
    type: str
    default: present
    choices:
      - absent
      - present
notes:
  - >-
    This module supports check mode.
  - >-
    This module supports all options provided by
    M(containers.podman.podman_pod) with the following exceptions:
    I(executable), I(infra_conmon_pidfile), I(pod_id_file), I(recreate),
    I(replace).
extends_documentation_fragment:
  - files
'''

EXAMPLES = '''
- name: Pod config for demo.example.com pod present
  znerol.podpourri.podman_pod:
    name: demo.example.com
    state: present
    network: example.com
    share: net,uts

- name: Pod config for demo.example.com pod absent
  znerol.podpourri.podman_container:
    name: demo.example.com
    state: absent
'''

import os  # noqa: F402

from ansible.module_utils.basic import AnsibleModule  # noqa: F402
from ansible_collections.containers.podman.plugins.module_utils.podman.podman_pod_lib import ARGUMENTS_SPEC_POD  # noqa: F402,E501
from ansible_collections.containers.podman.plugins.module_utils.podman.podman_pod_lib import PodmanPodModuleParams  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import config_get_pod_dir  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import file_ensure_absent  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import file_ensure_content  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import generate_env_content  # noqa: F402,E501


def _generate_pod_config(module):
    b_command = PodmanPodModuleParams(
        'create',
        module.params,
        None,
        module
    ).construct_command_from_params()

    return {
        'PODLUCK_POD_ARGS': b_command[1:]
    }


def main():
    ignored_pod_args = [
        'executable',
        'infra_conmon_pidfile',
        'pod_id_file',
        'recreate',
        'replace'
        'state',
    ]

    spec = {
        key: value
        for (key, value)
        in ARGUMENTS_SPEC_POD.items()
        if key not in ignored_pod_args
    }
    spec['backup'] = dict(type='bool', default=False)
    spec['state'] = dict(type='str', default="present", choices=[
        'present',
        'absent',
    ])

    module = AnsibleModule(
        argument_spec=spec,
        add_file_common_args=True,
        supports_check_mode=True,
    )

    name = module.params.pop('name')
    default_dest = os.path.join(
        config_get_pod_dir(name),
        'systemd-pod-env'
    )

    module.params.setdefault('path', default_dest)

    result = dict()
    if module.params['state'] == 'present':
        content = generate_env_content(_generate_pod_config(module))
        result = file_ensure_content(module, content)

    elif module.params['state'] == 'absent':
        result = file_ensure_absent(module)

    # Mission complete
    result['msg'] = f'OK: {result["msg"]}' if 'msg' in result else 'OK'
    module.exit_json(**result)


if __name__ == '__main__':
    main()
