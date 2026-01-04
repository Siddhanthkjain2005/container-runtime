#ifndef CONTAINER_H
#define CONTAINER_H

#include <sys/types.h>

/* Container configuration structure */
struct container_config {
    char *name;
    char *rootfs_path;
    char *command;
    char **args;
    int argc;
    long cpu_limit;      /* CPU limit in percentage (0-100) */
    long memory_limit;   /* Memory limit in bytes */
    long io_limit;       /* I/O limit in bytes per second */
    int pid_limit;       /* Maximum number of PIDs */
};

/* Container runtime functions */
int container_create(struct container_config *config);
int container_child_exec(void *arg);
void cleanup_container(const char *name);

/* Utility functions */
void print_error(const char *msg);
long parse_memory_limit(const char *limit_str);
int validate_config(struct container_config *config);

#endif /* CONTAINER_H */
