CC      ?= clang
CFLAGS  ?= -O3 -march=native -ffast-math -Wall -Wextra -Iinclude -pthread
LDFLAGS ?= -pthread
AR      ?= ar

BUILD   := build
LIB     := lib/libgemm.a
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

# gemm_amx.c 必须用 -O2：-O3 下 clang 的优化会与 AMX 内联汇编的寄存器假设冲突，
# 实测导致按空指针执行 ldx（SIGSEGV）。见 L4 implementation.md「AMX -O3 冲突」。
$(BUILD)/gemm_amx.o: src/gemm_amx.c include/gemm.h src/amx_asm.h | $(BUILD)
	$(CC) $(CFLAGS:-O3=-O2) -O2 -c $< -o $@

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
	rm -rf $(BUILD) lib
