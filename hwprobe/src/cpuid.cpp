#include "cpuid.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

namespace hwprobe {

namespace {

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

// __builtin_cpu_supports is x86-only on GCC/Clang and requires a string
// literal at the call site (GCC enforces this). We unroll the probe
// through a macro so every call sees a literal. On non-x86 the macro
// expands to nothing and we rely on /proc/cpuinfo for the canonical
// answer.
//
// The "kernel" name (second arg) matches the spelling in /proc/cpuinfo's
// flags: line, which is the spelling hw-preflight's check expects.
#define HWPROBE_PROBE(out, builtin_name, kernel_name) \
    do {                                              \
        if (__builtin_cpu_supports(builtin_name)) {   \
            (out).push_back(kernel_name);             \
        }                                             \
    } while (0)

std::vector<std::string> builtin_features() {
    std::vector<std::string> out;
#if defined(__x86_64__) || defined(__i386__)
    HWPROBE_PROBE(out, "mmx", "mmx");
    HWPROBE_PROBE(out, "sse", "sse");
    HWPROBE_PROBE(out, "sse2", "sse2");
    HWPROBE_PROBE(out, "sse3", "sse3");
    HWPROBE_PROBE(out, "ssse3", "ssse3");
    HWPROBE_PROBE(out, "sse4.1", "sse4_1");
    HWPROBE_PROBE(out, "sse4.2", "sse4_2");
    HWPROBE_PROBE(out, "avx", "avx");
    HWPROBE_PROBE(out, "avx2", "avx2");
    HWPROBE_PROBE(out, "avx512f", "avx512f");
    HWPROBE_PROBE(out, "bmi", "bmi1");
    HWPROBE_PROBE(out, "bmi2", "bmi2");
    HWPROBE_PROBE(out, "fma", "fma");
    HWPROBE_PROBE(out, "popcnt", "popcnt");
    HWPROBE_PROBE(out, "aes", "aes");
    HWPROBE_PROBE(out, "pclmul", "pclmulqdq");
#endif
    return out;
}

#undef HWPROBE_PROBE

}  // namespace

std::vector<std::string> parse_cpuinfo(const std::string& contents) {
    std::set<std::string> tokens;
    std::istringstream iss(contents);
    std::string line;
    while (std::getline(iss, line)) {
        const auto colon = line.find(':');
        if (colon == std::string::npos) continue;
        std::string key = line.substr(0, colon);
        // strip trailing whitespace
        while (!key.empty() && std::isspace(static_cast<unsigned char>(key.back()))) {
            key.pop_back();
        }
        const std::string lkey = lower(key);
        if (lkey != "flags" && lkey != "features") continue;
        std::string rhs = line.substr(colon + 1);
        std::istringstream rss(rhs);
        std::string tok;
        while (rss >> tok) {
            tokens.insert(lower(tok));
        }
    }
    return std::vector<std::string>(tokens.begin(), tokens.end());
}

std::vector<std::string> cpu_features() {
    std::set<std::string> merged;
    for (auto& f : builtin_features()) merged.insert(lower(f));

    std::ifstream in("/proc/cpuinfo");
    if (in) {
        std::ostringstream oss;
        oss << in.rdbuf();
        for (auto& f : parse_cpuinfo(oss.str())) merged.insert(f);
    }
    return std::vector<std::string>(merged.begin(), merged.end());
}

}  // namespace hwprobe
