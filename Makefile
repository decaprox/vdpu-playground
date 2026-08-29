SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := help

BOARD             := qemu_cortex_a53
VENV              := environment/venv
ZEPHYR_WORKSPACE  := build/zephyr_workspace
APP_BUILD_DIR     := ../../build/app-build
APP               := vdpu-firmware/app

QEMU_PRODUCT      := qemu-vdpu
QEMU_SRC_DIR      := $(CURDIR)/$(QEMU_PRODUCT)
QEMU_BUILD_DIR    := $(CURDIR)/build/$(QEMU_PRODUCT)
QEMU_TARGET_DIR   := $(CURDIR)/environment/$(QEMU_PRODUCT)

SDK_VERSION       := 0.16.8
SDK_DIR           := environment/zephyr-sdk-$(SDK_VERSION)
SDK_ARCHIVE       := zephyr-sdk-$(SDK_VERSION)_linux-x86_64_minimal.tar.xz
SDK_URL           := https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v$(SDK_VERSION)/$(SDK_ARCHIVE)

QEMU_CONFIGURE_FLAGS := \
	--prefix=$(QEMU_TARGET_DIR) \
	--target-list=aarch64-softmmu \
	--disable-gtk \
	--disable-sdl \
	--disable-vnc \
	--disable-spice \
	--disable-curses \
	--disable-opengl

.PHONY: help venv zephyr sdk qemu qemu-configure qemu-build-install prepare firmware test all clean-qemu-build

help: ## Show this help
	@echo "Usage: make <target>"
	@echo ""
	@echo "Environment setup (from prepare_environment.sh):"
	@echo "  venv               Create Python venv and install requirements.txt"
	@echo "  zephyr             Init/update Zephyr west workspace (needs venv)"
	@echo "  sdk                Download and install Zephyr SDK $(SDK_VERSION)"
	@echo "  qemu-configure     Run configure for qemu-vdpu"
	@echo "  qemu-build-install Build (-j\$$(nproc)) and install qemu-vdpu"
	@echo "  qemu               qemu-configure + qemu-build-install"
	@echo "  prepare            Run venv + zephyr + sdk + qemu-configure + qemu-build-install"
	@echo ""
	@echo "Build & test:"
	@echo "  firmware           Build Zephyr firmware for $(BOARD) (from build_firmware.sh)"
	@echo "  test               Run pytest test suite (from run_tests.sh)"
	@echo ""
	@echo "  all                prepare + firmware + test"
	@echo "  clean-qemu-build   Remove the qemu-vdpu build directory"

venv: ## Create Python venv and pip install -r requirements.txt
	python3 -m venv $(VENV)
	source $(VENV)/bin/activate &&
		pip install -r requirements.txt

zephyr: ## west init/update Zephyr workspace, zephyr-export, pip install
	source $(VENV)/bin/activate
	if [ -f "$(ZEPHYR_WORKSPACE)/.west/config" ]; then
		echo "Zephyr workspace already initialized, skipping west init"
	elif [ -d "$(ZEPHYR_WORKSPACE)/.west" ]; then
		echo "error: $(ZEPHYR_WORKSPACE)/.west exists but has no config file." >&2
		echo "       'west init' was likely interrupted last time, leaving a" >&2
		echo "       stale/incomplete workspace. Remove it and re-run:" >&2
		echo "           rm -rf $(ZEPHYR_WORKSPACE)" >&2
		echo "           make zephyr" >&2
		exit 1
	else
		mkdir -p "$(CURDIR)/build" &&
			west init -m "file://$(CURDIR)/vdpu-firmware" --mf west.yml "$(ZEPHYR_WORKSPACE)" &&
			rm -rf "$(ZEPHYR_WORKSPACE)/vdpu-firmware" &&
			ln -s "$(CURDIR)/vdpu-firmware" "$(ZEPHYR_WORKSPACE)/vdpu-firmware"
	fi
	cd "$(ZEPHYR_WORKSPACE)" &&
		west update &&
		west zephyr-export &&
		pip install -r zephyr/scripts/requirements.txt

sdk: ## Download & install Zephyr SDK $(SDK_VERSION) (aarch64-zephyr-elf)
	if [ -d "$(SDK_DIR)" ]; then
		echo "Zephyr SDK already installed, skipping"
	else
		mkdir -p environment &&
			cd environment &&
			wget -q "$(SDK_URL)" &&
			tar xf "$(SDK_ARCHIVE)" &&
			rm "$(SDK_ARCHIVE)" &&
			cd "zephyr-sdk-$(SDK_VERSION)" &&
			./setup.sh -t aarch64-zephyr-elf -c
	fi

qemu-configure: ## Create build dirs and run configure for qemu-vdpu
	mkdir -p $(QEMU_TARGET_DIR)
	mkdir -p $(QEMU_BUILD_DIR)
	cd $(QEMU_BUILD_DIR) &&
		$(QEMU_SRC_DIR)/configure $(QEMU_CONFIGURE_FLAGS)

qemu-build-install: ## Build (-j$(nproc)) and install qemu-vdpu (configure must have run already)
	if [ ! -f "$(QEMU_BUILD_DIR)/Makefile" ]; then
		echo "error: $(QEMU_BUILD_DIR) is not configured yet." >&2
		echo "       Run 'make qemu-configure' first (or 'make qemu' for both steps)." >&2
		exit 1
	fi
	cd $(QEMU_BUILD_DIR) &&
		make -j$$(nproc) &&
		make install

qemu: qemu-configure qemu-build-install ## Configure, then build and install qemu-vdpu

prepare: venv zephyr sdk qemu-configure qemu-build-install

firmware: ## west build -b $(BOARD) -p always (pristine build)
	source $(VENV)/bin/activate &&
		cd $(ZEPHYR_WORKSPACE) &&
		west build -b $(BOARD) -d $(APP_BUILD_DIR) $(APP) -p always

test: ## cd tests && pytest
	cd tests &&
		pytest

all: prepare firmware test ## prepare + firmware + test

clean-qemu-build: ## Remove build/qemu-vdpu (forces reconfigure+rebuild)
	rm -rf $(QEMU_BUILD_DIR)
