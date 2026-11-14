CC      ?= clang
CFLAGS  ?= -O3 -march=native -ffast-math -Wall -Wextra -Iinclude -pthread
LDFLAGS ?= -pthread
AR      ?= ar

BUILD   := build
LIB     := lib/libgemm.a
SRCS    := src/gemm_ref.c src/gemm_blocked.c
OBJS    := $(SRCS:src/%.c=$(BUILD)/%.o)

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
	rm -rf $(BUILD) lib
