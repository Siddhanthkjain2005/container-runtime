#ifndef NAMESPACES_H
#define NAMESPACES_H

/* Namespace setup functions */

/* Setup mount namespace with new root filesystem */
int setup_mount_namespace(const char *rootfs_path);

/* Setup network namespace */
int setup_network_namespace(void);

/* Setup hostname in UTS namespace */
int setup_uts_namespace(const char *hostname);

/* Setup IPC namespace */
int setup_ipc_namespace(void);

/* Mount essential filesystems */
int mount_proc(void);
int mount_sys(void);
int mount_dev(void);

/* Perform pivot_root to change root filesystem */
int do_pivot_root(const char *new_root);

#endif /* NAMESPACES_H */
