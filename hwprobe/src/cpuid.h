// CPU feature flag detection.
//
// Two sources contribute to the returned set:
//
//  1. `__builtin_cpu_supports("...")` for a curated list of x86 features
//     where GCC/Clang expose runtime detection. This matches what userspace
//     compilers think the hardware supports.
//  2. /proc/cpuinfo `flags:` (x86) or `Features:` (arm64) line, which is what
//     the kernel reports. Including both makes the result stable across
//     architectures the C++ builtin doesn't know about.
//
// The two sets are unioned and lowercased.

#pragma once

#include <string>
#include <vector>

namespace hwprobe {

// Returns the list of CPU feature flag tokens, sorted and deduplicated.
std::vector<std::string> cpu_features();

// Internal: parses a `flags:`/`Features:` line into tokens. Exposed for tests.
std::vector<std::string> parse_cpuinfo(const std::string& contents);

}  // namespace hwprobe
