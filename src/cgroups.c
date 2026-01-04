#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include "cgroups.h"

/* Write value to a cgroup file */
int write_cgroup_file(const char *path, const char *value) {
    int fd;
    ssize_t written;

    fd = open(path, O_WRONLY | O_TRUNC);
    if (fd < 0) {
        perror("open cgroup file");
        fprintf(stderr, "Failed to open: %s\n", path);
        return -1;
    }

    written = write(fd, value, strlen(value));
    if (written < 0) {
        perror("write cgroup file");
        fprintf(stderr, "Failed to write to: %s\n", path);
        close(fd);
        return -1;
    }

    close(fd);
    return 0;
}

/* Read value from a cgroup file */
int read_cgroup_file(const char *path, char *buffer, size_t size) {
    int fd;
    ssize_t bytes_read;

    fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open cgroup file");
        return -1;
    }

    bytes_read = read(fd, buffer, size - 1);
    if (bytes_read < 0) {
        perror("read cgroup file");
        close(fd);
        return -1;
    }

    buffer[bytes_read] = '\0';
    close(fd);
    return bytes_read;
}

/* Ensure required controllers are available */
int ensure_cgroup_controllers(void) {
    char path[512];
    char controllers[1024];
    
    /* Check if mycontainer cgroup exists */
    if (access(CGROUP_BASE_PATH, F_OK) != 0) {
        /* Create base cgroup directory */
        if (mkdir(CGROUP_BASE_PATH, 0755) < 0) {
            perror("mkdir cgroup base");
            return -1;
        }
    }

    /* Enable controllers in parent cgroup */
    snprintf(path, sizeof(path), "/sys/fs/cgroup/cgroup.subtree_control");
    strcpy(controllers, "+cpu +memory +io +pids");
    write_cgroup_file(path, controllers);

    /* Enable controllers in mycontainer cgroup */
    snprintf(path, sizeof(path), "%s/cgroup.subtree_control", CGROUP_BASE_PATH);
    write_cgroup_file(path, controllers);

    return 0;
}

/* Initialize cgroup for container */
int cgroup_init(const char *container_name) {
    char path[512];

    /* Ensure base cgroup and controllers are set up */
    if (ensure_cgroup_controllers() < 0) {
        fprintf(stderr, "Warning: Could not enable all controllers\n");
    }

    /* Create container-specific cgroup */
    snprintf(path, sizeof(path), "%s/%s", CGROUP_BASE_PATH, container_name);
    if (mkdir(path, 0755) < 0) {
        if (errno != EEXIST) {
            perror("mkdir container cgroup");
            return -1;
        }
    }

    return 0;
}

/* Set CPU limit (percentage 0-100) */
int cgroup_set_cpu_limit(const char *container_name, long cpu_percent) {
    char path[512];
    char value[128];

    if (cpu_percent <= 0 || cpu_percent > 100) {
        fprintf(stderr, "Invalid CPU percentage: %ld\n", cpu_percent);
        return -1;
    }

    snprintf(path, sizeof(path), "%s/%s/cpu.max", CGROUP_BASE_PATH, container_name);
    
    /* cpu.max format: $MAX $PERIOD
     * For percentage: (percentage * 100000) / 100 = quota
     * Period is typically 100000 (100ms)
     */
    long quota = (cpu_percent * 100000) / 100;
    snprintf(value, sizeof(value), "%ld 100000", quota);

    return write_cgroup_file(path, value);
}

/* Set memory limit in bytes */
int cgroup_set_memory_limit(const char *container_name, long memory_bytes) {
    char path[512];
    char value[128];

    if (memory_bytes <= 0) {
        fprintf(stderr, "Invalid memory limit: %ld\n", memory_bytes);
        return -1;
    }

    snprintf(path, sizeof(path), "%s/%s/memory.max", CGROUP_BASE_PATH, container_name);
    snprintf(value, sizeof(value), "%ld", memory_bytes);

    return write_cgroup_file(path, value);
}

/* Set I/O limit in bytes per second */
int cgroup_set_io_limit(const char *container_name, long io_bps) {
    char path[512];
    char value[128];
    char device_id[64];
    FILE *fp;

    if (io_bps <= 0) {
        return 0; /* Skip if no limit */
    }

    /* Get device major:minor for root device */
    fp = popen("stat -c '%d' / | awk '{print $1}'", "r");
    if (fp == NULL) {
        perror("popen stat");
        return -1;
    }
    
    if (fgets(device_id, sizeof(device_id), fp) == NULL) {
        pclose(fp);
        return -1;
    }
    pclose(fp);

    /* Remove newline */
    device_id[strcspn(device_id, "\n")] = 0;

    snprintf(path, sizeof(path), "%s/%s/io.max", CGROUP_BASE_PATH, container_name);
    snprintf(value, sizeof(value), "%s rbps=%ld wbps=%ld", device_id, io_bps, io_bps);

    /* io.max might not be available, so don't fail */
    write_cgroup_file(path, value);
    return 0;
}

/* Set PID limit */
int cgroup_set_pid_limit(const char *container_name, int max_pids) {
    char path[512];
    char value[128];

    if (max_pids <= 0) {
        max_pids = 1024; /* Default limit */
    }

    snprintf(path, sizeof(path), "%s/%s/pids.max", CGROUP_BASE_PATH, container_name);
    snprintf(value, sizeof(value), "%d", max_pids);

    return write_cgroup_file(path, value);
}

/* Add process to cgroup */
int cgroup_add_pid(const char *container_name, pid_t pid) {
    char path[512];
    char value[32];

    snprintf(path, sizeof(path), "%s/%s/cgroup.procs", CGROUP_BASE_PATH, container_name);
    snprintf(value, sizeof(value), "%d", pid);

    return write_cgroup_file(path, value);
}

/* Cleanup cgroup */
int cgroup_cleanup(const char *container_name) {
    char path[512];
    char procs_path[512];
    char buffer[4096];
    pid_t pid;
    char *line;

    snprintf(path, sizeof(path), "%s/%s", CGROUP_BASE_PATH, container_name);
    snprintf(procs_path, sizeof(procs_path), "%s/cgroup.procs", path);

    /* Kill all processes in the cgroup */
    if (read_cgroup_file(procs_path, buffer, sizeof(buffer)) > 0) {
        line = strtok(buffer, "\n");
        while (line != NULL) {
            pid = atoi(line);
            if (pid > 1) {
                kill(pid, SIGKILL);
            }
            line = strtok(NULL, "\n");
        }
    }

    /* Wait a bit for processes to die */
    usleep(100000);

    /* Remove cgroup directory */
    if (rmdir(path) < 0) {
        if (errno != ENOENT) {
            perror("rmdir cgroup");
            return -1;
        }
    }

    return 0;
}
