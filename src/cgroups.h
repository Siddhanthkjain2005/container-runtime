#ifndef CGROUPS_H
#define CGROUPS_H

#include <sys/types.h>

/* cgroups v2 management */

#define CGROUP_BASE_PATH "/sys/fs/cgroup/mycontainer"

/* Initialize cgroup for container */
int cgroup_init(const char *container_name);

/* Set resource limits */
int cgroup_set_cpu_limit(const char *container_name, long cpu_percent);
int cgroup_set_memory_limit(const char *container_name, long memory_bytes);
int cgroup_set_io_limit(const char *container_name, long io_bps);
int cgroup_set_pid_limit(const char *container_name, int max_pids);

/* Add process to cgroup */
int cgroup_add_pid(const char *container_name, pid_t pid);

/* Cleanup cgroup */
int cgroup_cleanup(const char *container_name);

/* Utility functions */
int ensure_cgroup_controllers(void);
int write_cgroup_file(const char *path, const char *value);
int read_cgroup_file(const char *path, char *buffer, size_t size);

#endif /* CGROUPS_H */
