CC = gcc
CFLAGS = -Wall -Wextra -O2 -std=gnu11
LDFLAGS = 
TARGET = container_runtime
SRC_DIR = src
BUILD_DIR = build

SOURCES = $(SRC_DIR)/container.c $(SRC_DIR)/cgroups.c $(SRC_DIR)/namespaces.c
OBJECTS = $(SOURCES:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

.PHONY: all clean install

all: $(BUILD_DIR) $(TARGET)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf $(BUILD_DIR) $(TARGET)

install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

.PHONY: help
help:
	@echo "Container Runtime Build System"
	@echo ""
	@echo "Targets:"
	@echo "  all      - Build the container runtime (default)"
	@echo "  clean    - Remove build artifacts"
	@echo "  install  - Install to /usr/local/bin"
	@echo "  help     - Show this help message"
