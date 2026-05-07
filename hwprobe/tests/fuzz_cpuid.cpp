// libFuzzer harness for parse_cpuinfo.
//
// Build with:
//   cmake -S hwprobe -B hwprobe/build -DHWPROBE_FUZZ=ON \
//         -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
//   cmake --build hwprobe/build --target hwprobe_fuzz_cpuid
//
// Run a short sweep:
//   ./hwprobe/build/hwprobe_fuzz_cpuid -runs=10000 -max_len=4096
//
// The harness only asserts that parse_cpuinfo returns sorted, unique
// strings; any crash or invariant violation surfaces as a libFuzzer
// failure.

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>

#include "cpuid.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    std::string input(reinterpret_cast<const char*>(data), size);
    auto tokens = hwprobe::parse_cpuinfo(input);
    auto copy = tokens;
    std::sort(copy.begin(), copy.end());
    copy.erase(std::unique(copy.begin(), copy.end()), copy.end());
    if (copy.size() != tokens.size()) {
        __builtin_trap();
    }
    return 0;
}
