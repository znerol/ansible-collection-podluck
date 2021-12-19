# Ansible Role - znerol.podluck.podluck_pod_systemd

Runs podman pods under systemd.

Note that the systemd units installed by this role are designed to always
*create* and *remove* all containers in a pod when *starting* and *stopping*
them respectively. As a result, the systemd units are working well with `podman
auto-update`.

Units can be installed both, in the `user` scope (`~/.config/systemd/user`) as
well as in `system` scope (`/etc/systemd/system`). As a result, this collection
supports rootfull as well as rootless deployments.

## Requirements

* Ansible>=2.10
* Python 3.6 or better
* containers.podman collection

## Installation

Using a `requirements.yml` file:

```yaml
collections:
  - name: znerol.podluck
```

## Reference

### Variables for `znerol.podluck.podluck_pod_systemd` role

```yaml
---
# Required: Pod name, also used as the systemd service name. Must be defined
# when role is imported / included.
# podluck_pod_name: no-default

# Optional: State, either `present` or `absent`. Defaults to `present`.
podluck_pod_state: present

# Recommended: Whether systemd units are enabled (`true`) or disabled (`false`).
# No changes if omitted.
# podluck_pod_enabled: default(omit)

# Recommended: List of container names to start / stop when pod is started /
# stopped.
podluck_pod_containers: []

# Optional: Mapping of dependencies where keys are container names, and values
# are lists of container names which need to be started before.
podluck_pod_dependencies: {}

# Optional: Systemd scope (either 'system' or 'user')
podluck_systemd_scope: system

# Optional: Path to systemd units. Defaults to /usr/local/lib/systemd/system if
# `podluck_systemd_scope` is `system` and `~/.config/systemd/user` if
# `podluck_systemd_scope` is `user`.
podluck_systemd_unit_dir: "{{ podluck_systemd_unit_dirs[podluck_systemd_scope] }}"

# Optional: Path to systemd config directory. Defaults to /etc/systemd/system if
# `podluck_systemd_scope` is `system` and `~/.config/systemd/user` if
# `podluck_systemd_scope` is `user`.
podluck_systemd_config_dir: "{{ podluck_systemd_config_dirs[podluck_systemd_scope] }}"

# Optional: Path to directory with podluck systemd unit files. Defaults to the
# ones shipped with this role.
podluck_systemd_skel_src: systemd-skel

# Optional: Whether or not to look for podluck systemd unit files on the remote
# machine. Defaults to `false`.
# podluck_systemd_skel_remote_src: default(omit)

# Optional: Owner of copied systemd unit files. Omitted by default.
# podluck_systemd_unit_file_owner: default(omit)

# Optional: Group of copied systemd unit files. Omitted by default.
# podluck_systemd_unit_file_group: default(omit)

# Optional: Mode of copied systemd unit files. Defaults to rw-r--r--
podluck_systemd_unit_file_mode: 0644

# Optional: Owner of systemd unit override directory. Omitted by default.
# podluck_systemd_override_dir_owner: default(omit)

# Optional: Group of systemd unit override directory. Omitted by default.
# podluck_systemd_override_dir_group: default(omit)

# Optional: Mode of systemd unit override directory. Defaults to rwxr-xr-x
podluck_systemd_override_dir_mode: 0755

# Optional: Owner of systemd unit override files. Omitted by default.
# podluck_systemd_override_file_owner: default(omit)

# Optional: Group of systemd unit override files. Omitted by default.
# podluck_systemd_override_file_group: default(omit)

# Optional: Mode of systemd unit override files. Defaults to rw-r--r--
podluck_systemd_override_file_mode: 0644
```

## Example

### Minimal rootless example

```yaml
---
- name: Minimal rootless example
  hosts: localhost
  gather_facts: no
  vars:
    podluck_systemd_scope: user
    podluck_pod_name: minimal.example.com
    podluck_pod_state: present
    podluck_pod_enabled: true
    podluck_pod_containers:
      - hello-world
  tasks:
    - name: Pod configuration present
      znerol.podluck.podluck_pod:
        name: "{{ podluck_pod_name }}"
        state: "{{ podluck_pod_state }}"
        share: net,uts
        mode: 0600

    - name: Container configuration present
      znerol.podluck.podluck_container:
        name: hello-world
        image: docker.io/library/hello-world:latest
        pod: "{{ podluck_pod_name }}"
        state: "{{ podluck_pod_state }}"
        log_driver: journald
        cap_drop: ALL
        mode: 0600

    - name: Systemd configuration present
      import_role:
        name: znerol.podluck.podluck_pod_systemd

    - name: Pod started
      when: podluck_pod_state != 'absent'
      systemd:
        name: "{{ podluck_pod_name }}.service"
        scope: "{{ podluck_systemd_scope }}"
        state: started
```

After running this playbook, the `minimal.example.com` pod should be up and
running along with `hello-world.minimal.example.com` container. Also systemd
units `minimal.example.com.service` as well as `minimal.example.com@hello-world`
are expected to be started. Inspect the results as follows:

```
$ systemctl --user status minimal.example.com.service
● minimal.example.com.service - Podman pod minimal.example.com managed by podluck
[...]

$ systemctl --user status minimal.example.com@hello-world.service
● minimal.example.com@hello-world.service - Podman container hello-world in pod minimal.example.com managed by podluck
[...]

$ journalctl --user --unit minimal.example.com.service
-- Journal begins at Sat 2021-05-22 14:40:55 CEST, ends at Sun 2021-12-19 14:49:14 CET. --
systemd[676]: Starting Podman pod minimal.example.com managed by podluck...
[...]

$ journalctl --user --unit minimal.example.com@hello-world.service
-- Journal begins at Sat 2021-05-22 14:40:55 CEST, ends at Sun 2021-12-19 14:49:14 CET. --
systemd[676]: Starting Podman container hello-world in pod minimal.example.com managed by podluck...
[...]
conmon[20303]:
conmon[20303]: Hello from Docker!
conmon[20303]: This message shows that your installation appears to be working correctly.
conmon[20303]:
conmon[20303]: To generate this message, Docker took the following steps:
conmon[20303]:  1. The Docker client contacted the Docker daemon.
conmon[20303]:  2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
conmon[20303]:     (amd64)
conmon[20303]:  3. The Docker daemon created a new container from that image which runs the
conmon[20303]:     executable that produces the output you are currently reading.
conmon[20303]:  4. The Docker daemon streamed that output to the Docker client, which sent it
conmon[20303]:     to your terminal.
conmon[20303]:
conmon[20303]: To try something more ambitious, you can run an Ubuntu container with:
conmon[20303]:  $ docker run -it ubuntu bash
conmon[20303]:
conmon[20303]: Share images, automate workflows, and more with a free Docker ID:
conmon[20303]:  https://hub.docker.com/
conmon[20303]:
conmon[20303]: For more examples and ideas, visit:
conmon[20303]:  https://docs.docker.com/get-started/
conmon[20303]:
[...]
systemd[676]: minimal.example.com@hello-world.service: Succeeded.
systemd[676]: minimal.example.com@hello-world.service: Consumed 1.344s CPU time.
```

## License

* [GPL-3 or later](https://www.gnu.org/licenses/gpl-3.0.en.html)
