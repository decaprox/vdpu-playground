# About the Project

This is the main repository for my experiments with a virtual DPU and firmware for it.


# Building and running

## Obtaining the Source Code

```sh
git clone --recursive git@github.com:decaprox/vdpu-playground.git
```

## Installing dependencies:

```sh
sudo apt install -y \
  build-essential \
  git \
  cmake \
  ninja-build \
  gperf \
  ccache \
  dfu-util \
  device-tree-compiler \
  wget \
  pkg-config \
  python3 \
  python3-dev \
  python3-pip \
  python3-venv \
  python3-tk \
  xz-utils \
  file \
  make \
  gcc \
  gcc-multilib \
  g++-multilib \
  libsdl2-dev \
  libmagic1 \
  libglib2.0-dev \
  libpixman-1-dev \
  libfdt-dev \
  libslirp-dev \
  libcap-ng-dev \
  libaio-dev \
  zlib1g-dev
```

## Running

```sh
make all
```

Or you can run targets separately, e.g.:

```sh
make prepare
make firmware
make tests
```

Or choose another target

```
Usage: make <target>

Environment setup (from prepare_environment.sh):
  venv               Create Python venv and install requirements.txt
  zephyr             Init/update Zephyr west workspace (needs venv)
  sdk                Download and install Zephyr SDK 0.16.8
  qemu-configure     Run configure for qemu-vdpu
  qemu-build-install Build (-j$(nproc)) and install qemu-vdpu
  qemu               qemu-configure + qemu-build-install
  prepare            Run venv + zephyr + sdk + qemu-configure + qemu-build-install

Build & test:
  firmware           Build Zephyr firmware for qemu_cortex_a53 (from build_firmware.sh)
  test               Run pytest test suite (from run_tests.sh)

  all                prepare + firmware + test
  clean-qemu-build   Remove the qemu-vdpu build directory
```