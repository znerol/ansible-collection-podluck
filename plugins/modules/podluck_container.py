#!/usr/bin/python
# Copyright (c) 2021 Lorenz Schori
#
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r'''
module: podluck_container
author:
  - "Lorenz Schori"
version_added: '1.0.0'
short_description: Configure podman containers managed by systemd
description:
  - Install and remove configuration for Podman containers managed by systemd
requirements:
  - containers.podman
  - Python 3.6 or better
options:
  name:
    description:
      - Name of the container
    required: True
    type: str
  pod:
    description:
      - Name of a pod created using M(znerol.podluck.podluck_pod).
    required: True
    type: str
  path:
    description:
      - >-
        Path to the container configuration file. Use the defaults, since this
        is what the `podluck-service@.service` systemd unit expects.
      - >-
        Defaults to
        `/etc/podluck/pod/{{ pod }}/systemd-container-{{ name }}-env` when
        module is executed as I(root).
      - >-
        Defaults to
        `~/.config/podluck/pod/{{ pod }}/systemd-container-{{ name }}-env` when
        module is executed as an unprivileged user.
    type: str
  state:
    description:
      - >-
        I(absent) - A podluck configuration file for the container in the
        specified pod is unlinked if it exists.
      - >-
        I(present) - A podluck configuration file for the container in the
        specified pod is created and populated with cli arguments matching the
        desired configuration. Returns `changed: True` if existing
        configuration does not match the current config. The calling playbook /
        role is responsible for restarting the container / pod if necessary.
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
    M(containers.podman.podman_container) with the following exceptions:
    I(cgroups), I(cidfile), I(conmon_pidfile), I(detach), I(executable),
    I(generate_systemd), I(infra_conmon_pidfile), I(pod_id_file), I(recreate),
    I(replace).
extends_documentation_fragment:
  - files
'''

EXAMPLES = '''
- name: Container config for wildfly in demo.example.com pod present
  znerol.podpourri.podman_container:
    name: wildfly
    pod: demo.example.com
    image: quay.io/bitnami/wildfly:latest
    state: present
    publish:
      - '8080:8080'
      - '9990:9990'
    volumes:
      - wildfly.demo.example.com:/bitnami/wildfly
    mode: 0600

- name: Container config for wildfly in demo.example.com pod absent
  znerol.podpourri.podman_container:
    name: wildfly
    pod: demo.example.com
    state: absent
'''

import os  # noqa: F402

from ansible.module_utils.basic import AnsibleModule  # noqa: F402
from ansible_collections.containers.podman.plugins.module_utils.podman.podman_container_lib import ARGUMENTS_SPEC_CONTAINER  # noqa: F402,E501
from ansible_collections.containers.podman.plugins.module_utils.podman.podman_container_lib import PodmanModuleParams  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import config_get_pod_dir  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import file_ensure_absent  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import file_ensure_content  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import generate_env_content  # noqa: F402,E501
from ansible_collections.znerol.podluck.plugins.module_utils.podluck.common import podman_get_version  # noqa: F402,E501


class PodluckModuleParams(PodmanModuleParams):
    def construct_args_from_params(self):
        """Create args from given module parameters.
        Returns:
           list -- list of strings for PODLUCK_CONTAINER_ARGS env var
        """
        cmd = []
        all_param_methods = [func for func in dir(self)
                             if callable(getattr(self, func))
                             and func.startswith("addparam")]
        params_set = (i for i in self.params if self.params[i] is not None)
        for param in params_set:
            func_name = "_".join(["addparam", param])
            if func_name in all_param_methods:
                cmd = getattr(self, func_name)(cmd)

        return cmd


def _generate_container_config(module):
    params = {
        'name': 'ignored_name',
        'image': 'ignored_image',
        'command': [],
    }
    params.update(module.params)
    args = PodluckModuleParams(
        'create',
        params,
        podman_get_version(module),
        module
    ).construct_args_from_params()

    result = {
        'PODLUCK_CONTAINER_ARGS': args,
        'PODLUCK_CONTAINER_IMAGE': [module.params['image']],
    }

    if module.params['command']:
        if isinstance(module.params['command'], list):
            cmd = module.params['command']
        else:
            cmd = module.params['command'].split()
        result['PODLUCK_CONTAINER_IMAGE_CMD'] = cmd

    return result


def main():
    ignored_container_args = [
        'cgroups',
        'cidfile',
        'conmon_pidfile',
        'detach',
        'executable',
        'generate_systemd',
        'infra_conmon_pidfile',
        'pod_id_file',
        'recreate',
        'replace',
    ]
    spec = {
        key: value
        for (key, value)
        in ARGUMENTS_SPEC_CONTAINER.items()
        if key not in ignored_container_args
    }
    spec['pod']['required'] = True
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
    pod = module.params.pop('pod')
    default_dest = os.path.join(
        config_get_pod_dir(pod),
        f'systemd-container-{name}-env'
    )

    module.params.setdefault('path', default_dest)

    result = dict()
    if module.params['state'] == 'present':
        content = generate_env_content(_generate_container_config(module))
        result = file_ensure_content(module, content)

    elif module.params['state'] == 'absent':
        result = file_ensure_absent(module)

    # Mission complete
    result['msg'] = f'OK: {result["msg"]}' if 'msg' in result else 'OK'
    module.exit_json(**result)


if __name__ == '__main__':
    main()
