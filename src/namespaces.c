#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <errno.h>
#include <fcntl.h>
#include "namespaces.h"

/* Setup mount namespace with new root filesystem */
int setup_mount_namespace(const char *rootfs_path) {
    /* Mount the rootfs as private to prevent propagation */
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        perror("mount private /");
        return -1;
    }

    /* Bind mount the rootfs to itself to make it a mount point */
    if (mount(rootfs_path, rootfs_path, NULL, MS_BIND | MS_REC, NULL) < 0) {
        perror("bind mount rootfs");
        return -1;
    }

    return 0;
}

/* Perform pivot_root to change root filesystem */
int do_pivot_root(const char *new_root) {
    /* Change to new root */
    if (chdir(new_root) < 0) {
        perror("chdir new_root");
        return -1;
    }

    /* Create put_old directory inside new_root */
    if (mkdir(".pivot_root", 0755) < 0 && errno != EEXIST) {
        perror("mkdir .pivot_root");
        return -1;
    }

    /* Pivot root - use current directory (.) as new root, 
     * and .pivot_root as old root */
    if (syscall(SYS_pivot_root, ".", ".pivot_root") < 0) {
        perror("pivot_root");
        return -1;
    }

    /* Change to new root */
    if (chdir("/") < 0) {
        perror("chdir /");
        return -1;
    }

    /* Unmount old root */
    if (umount2("/.pivot_root", MNT_DETACH) < 0) {
        perror("umount old root");
        return -1;
    }

    /* Remove put_old directory */
    if (rmdir("/.pivot_root") < 0) {
        perror("rmdir .pivot_root");
        /* Not a critical error */
    }

    return 0;
}

/* Mount /proc filesystem */
int mount_proc(void) {
    /* Create /proc directory if it doesn't exist */
    if (mkdir("/proc", 0555) < 0 && errno != EEXIST) {
        perror("mkdir /proc");
        return -1;
    }

    /* Mount proc */
    if (mount("proc", "/proc", "proc", 0, NULL) < 0) {
        if (errno != EBUSY) {  /* Already mounted is okay */
            perror("mount /proc");
            return -1;
        }
    }

    return 0;
}

/* Mount /sys filesystem */
int mount_sys(void) {
    /* Create /sys directory if it doesn't exist */
    if (mkdir("/sys", 0555) < 0 && errno != EEXIST) {
        perror("mkdir /sys");
        return -1;
    }

    /* Mount sysfs */
    if (mount("sysfs", "/sys", "sysfs", 0, NULL) < 0) {
        if (errno != EBUSY) {  /* Already mounted is okay */
            perror("mount /sys");
            return -1;
        }
    }

    return 0;
}

/* Mount /dev filesystem */
int mount_dev(void) {
    /* Create /dev directory if it doesn't exist */
    if (mkdir("/dev", 0755) < 0 && errno != EEXIST) {
        perror("mkdir /dev");
        return -1;
    }

    /* Mount tmpfs on /dev */
    if (mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_STRICTATIME, "mode=755") < 0) {
        if (errno != EBUSY) {  /* Already mounted is okay */
            perror("mount /dev");
            return -1;
        }
    }

    /* Create essential device nodes */
    mknod("/dev/null", S_IFCHR | 0666, makedev(1, 3));
    mknod("/dev/zero", S_IFCHR | 0666, makedev(1, 5));
    mknod("/dev/random", S_IFCHR | 0666, makedev(1, 8));
    mknod("/dev/urandom", S_IFCHR | 0666, makedev(1, 9));

    /* Create /dev/pts for pseudo-terminals */
    if (mkdir("/dev/pts", 0755) < 0 && errno != EEXIST) {
        perror("mkdir /dev/pts");
    }

    return 0;
}

/* Setup network namespace */
int setup_network_namespace(void) {
    /* Network namespace is created by clone() flag */
    /* Additional setup like creating veth pairs would go here */
    /* For now, we have isolated network */
    return 0;
}

/* Setup hostname in UTS namespace */
int setup_uts_namespace(const char *hostname) {
    if (sethostname(hostname, strlen(hostname)) < 0) {
        perror("sethostname");
        return -1;
    }
    return 0;
}

/* Setup IPC namespace */
int setup_ipc_namespace(void) {
    /* IPC namespace is created by clone() flag */
    /* No additional setup needed */
    return 0;
}
