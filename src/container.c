#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sched.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include "container.h"
#include "cgroups.h"
#include "namespaces.h"

#define STACK_SIZE (1024 * 1024)

/* Print error message to stderr */
void print_error(const char *msg) {
    fprintf(stderr, "ERROR: %s\n", msg);
}

/* Parse memory limit string (e.g., "512M", "1G") */
long parse_memory_limit(const char *limit_str) {
    long value;
    char unit;
    int parsed;

    if (limit_str == NULL || strlen(limit_str) == 0) {
        return 0;
    }

    parsed = sscanf(limit_str, "%ld%c", &value, &unit);
    if (parsed < 1) {
        return -1;
    }

    if (parsed == 1) {
        return value; /* Assume bytes */
    }

    /* Convert based on unit */
    switch (unit) {
        case 'K':
        case 'k':
            return value * 1024;
        case 'M':
        case 'm':
            return value * 1024 * 1024;
        case 'G':
        case 'g':
            return value * 1024 * 1024 * 1024;
        default:
            return -1;
    }
}

/* Validate container configuration */
int validate_config(struct container_config *config) {
    if (config == NULL) {
        print_error("Invalid configuration");
        return -1;
    }

    if (config->name == NULL || strlen(config->name) == 0) {
        print_error("Container name is required");
        return -1;
    }

    if (config->rootfs_path == NULL || strlen(config->rootfs_path) == 0) {
        print_error("Rootfs path is required");
        return -1;
    }

    /* Check if rootfs exists */
    struct stat st;
    if (stat(config->rootfs_path, &st) < 0) {
        print_error("Rootfs path does not exist");
        return -1;
    }

    if (!S_ISDIR(st.st_mode)) {
        print_error("Rootfs path is not a directory");
        return -1;
    }

    if (config->command == NULL || strlen(config->command) == 0) {
        print_error("Command is required");
        return -1;
    }

    /* Validate resource limits */
    if (config->cpu_limit < 0 || config->cpu_limit > 100) {
        print_error("CPU limit must be between 0 and 100");
        return -1;
    }

    if (config->memory_limit < 0) {
        print_error("Memory limit must be positive");
        return -1;
    }

    return 0;
}

/* Child process execution function */
int container_child_exec(void *arg) {
    struct container_config *config = (struct container_config *)arg;

    /* Setup UTS namespace (hostname) */
    if (setup_uts_namespace(config->name) < 0) {
        print_error("Failed to setup UTS namespace");
        return -1;
    }

    /* Setup mount namespace */
    if (setup_mount_namespace(config->rootfs_path) < 0) {
        print_error("Failed to setup mount namespace");
        return -1;
    }

    /* Pivot root */
    if (do_pivot_root(config->rootfs_path) < 0) {
        print_error("Failed to pivot root");
        return -1;
    }

    /* Mount essential filesystems */
    if (mount_proc() < 0) {
        fprintf(stderr, "Warning: Failed to mount /proc\n");
    }
    if (mount_sys() < 0) {
        fprintf(stderr, "Warning: Failed to mount /sys\n");
    }
    if (mount_dev() < 0) {
        fprintf(stderr, "Warning: Failed to mount /dev\n");
    }

    /* Setup network namespace */
    setup_network_namespace();

    /* Setup IPC namespace */
    setup_ipc_namespace();

    /* Execute the command */
    if (config->argc > 0 && config->args != NULL) {
        execvp(config->command, config->args);
    } else {
        char *args[] = {config->command, NULL};
        execvp(config->command, args);
    }

    /* If we reach here, exec failed */
    perror("execvp");
    return -1;
}

/* Create and start a container */
int container_create(struct container_config *config) {
    pid_t child_pid;
    char *stack;
    char *stack_top;
    int flags;

    /* Validate configuration */
    if (validate_config(config) < 0) {
        return -1;
    }

    /* Check if running as root */
    if (geteuid() != 0) {
        print_error("Must be run as root");
        return -1;
    }

    /* Initialize cgroup */
    if (cgroup_init(config->name) < 0) {
        print_error("Failed to initialize cgroup");
        return -1;
    }

    /* Set resource limits */
    if (config->cpu_limit > 0) {
        if (cgroup_set_cpu_limit(config->name, config->cpu_limit) < 0) {
            fprintf(stderr, "Warning: Failed to set CPU limit\n");
        }
    }

    if (config->memory_limit > 0) {
        if (cgroup_set_memory_limit(config->name, config->memory_limit) < 0) {
            fprintf(stderr, "Warning: Failed to set memory limit\n");
        }
    }

    if (config->io_limit > 0) {
        if (cgroup_set_io_limit(config->name, config->io_limit) < 0) {
            fprintf(stderr, "Warning: Failed to set I/O limit\n");
        }
    }

    if (config->pid_limit > 0) {
        if (cgroup_set_pid_limit(config->name, config->pid_limit) < 0) {
            fprintf(stderr, "Warning: Failed to set PID limit\n");
        }
    }

    /* Allocate stack for child process */
    stack = malloc(STACK_SIZE);
    if (stack == NULL) {
        print_error("Failed to allocate stack");
        cgroup_cleanup(config->name);
        return -1;
    }
    stack_top = stack + STACK_SIZE;

    /* Setup namespaces flags */
    flags = CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWUTS | CLONE_NEWIPC | SIGCHLD;

    /* Clone process with namespaces */
    child_pid = clone(container_child_exec, stack_top, flags, config);
    if (child_pid < 0) {
        perror("clone");
        print_error("Failed to create container process");
        free(stack);
        cgroup_cleanup(config->name);
        return -1;
    }

    /* Add child process to cgroup */
    if (cgroup_add_pid(config->name, child_pid) < 0) {
        fprintf(stderr, "Warning: Failed to add PID to cgroup\n");
    }

    /* Print container PID for tracking */
    printf("%d\n", child_pid);
    fflush(stdout);

    /* Wait for child process */
    int status;
    waitpid(child_pid, &status, 0);

    /* Cleanup */
    free(stack);

    return WEXITSTATUS(status);
}

/* Cleanup container resources */
void cleanup_container(const char *name) {
    if (name == NULL) {
        return;
    }

    /* Cleanup cgroup */
    cgroup_cleanup(name);
}

/* Main function for standalone testing */
int main(int argc, char *argv[]) {
    struct container_config config = {0};
    char rootfs_absolute[PATH_MAX];

    if (argc < 4) {
        fprintf(stderr, "Usage: %s <name> <rootfs> <command> [args...]\n", argv[0]);
        fprintf(stderr, "Environment variables:\n");
        fprintf(stderr, "  CPU_LIMIT: CPU limit percentage (0-100)\n");
        fprintf(stderr, "  MEMORY_LIMIT: Memory limit (e.g., 512M, 1G)\n");
        fprintf(stderr, "  IO_LIMIT: I/O limit in bytes per second\n");
        fprintf(stderr, "  PID_LIMIT: Maximum number of PIDs\n");
        return 1;
    }

    /* Parse arguments */
    config.name = argv[1];
    
    /* Convert rootfs path to absolute */
    if (realpath(argv[2], rootfs_absolute) == NULL) {
        perror("realpath");
        fprintf(stderr, "Failed to resolve rootfs path: %s\n", argv[2]);
        return 1;
    }
    config.rootfs_path = rootfs_absolute;
    
    config.command = argv[3];
    config.argc = argc - 3;
    config.args = &argv[3];

    /* Parse environment variables for limits */
    char *env_val;
    
    env_val = getenv("CPU_LIMIT");
    if (env_val != NULL) {
        config.cpu_limit = atol(env_val);
    }

    env_val = getenv("MEMORY_LIMIT");
    if (env_val != NULL) {
        config.memory_limit = parse_memory_limit(env_val);
    }

    env_val = getenv("IO_LIMIT");
    if (env_val != NULL) {
        config.io_limit = atol(env_val);
    }

    env_val = getenv("PID_LIMIT");
    if (env_val != NULL) {
        config.pid_limit = atoi(env_val);
    }

    /* Create container */
    int ret = container_create(&config);

    /* Cleanup */
    cleanup_container(config.name);

    return ret;
}
