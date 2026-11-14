CC      ?= clang
CFLAGS  ?= -O3 -march=native -ffast-math -Wall -Wextra -Iinclude -pthread
LDFLAGS ?= -pthread
AR      ?= ar

# USE_AMX 开启时使用独立构建目录：彻底避免两种模式的 .o 互相复用
# （曾用时间戳 stamp 隔离，但同秒切换/空标志会导致漏重编，实测两次假通过）
ifeq ($(USE_AMX),1)
BUILD   := build-amx
else
BUILD   := build
endif
LIB     := $(BUILD)/libgemm.a
SRCS    := src/gemm_ref.c src/gemm_blocked.c src/gemm_amx.c
OBJS    := $(SRCS:src/%.c=$(BUILD)/%.o)

# AMX 实验后端：make USE_AMX=1（仅 arm64 macOS）
ifeq ($(USE_AMX),1)
CFLAGS += -DUSE_AMX=1
endif

TEST_BIN  := $(BUILD)/test_gemm
BENCH_BIN := $(BUILD)/bench_gemm
TEST_SRC  := tests/test_gemm.c
BENCH_SRC := bench/bench_gemm.c

.PHONY: all test bench clean

all: $(LIB)

$(BUILD) lib:
	mkdir -p $@

$(BUILD)/%.o: src/%.c include/gemm.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(LIB): $(OBJS) | lib
	$(AR) rcs $@ $(OBJS)

$(TEST_BIN): $(TEST_SRC) $(LIB) | $(BUILD)
	$(CC) $(CFLAGS) $< $(LIB) -o $@ $(LDFLAGS)

$(BENCH_BIN): $(BENCH_SRC) $(LIB) | $(BUILD)
	$(CC) $(CFLAGS) $< $(LIB) -o $@ $(LDFLAGS) -framework Accelerate

test: $(TEST_BIN)
	./$(TEST_BIN)

bench: $(BENCH_BIN)
	./$(BENCH_BIN)

clean:
	rm -rf build build-amx lib

# 构建产物（build/ build-amx/ lib/）由 .gitignore 排除
