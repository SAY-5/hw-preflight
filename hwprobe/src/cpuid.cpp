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

// __builtin_cpu_supports is x86-only on GCC/Clang. We probe a curated set
// and add whichever the runtime reports. On non-x86 the function is either
// absent or returns 0, in which case we return an empty list and rely on
// /proc/cpuinfo for the canonical answer.
std::vector<std::string> builtin_features() {
    std::vector<std::string> out;
#if defined(__x86_64__) || defined(__i386__)
    static constexpr const char* names[] = {
        "mmx",  "sse",     "sse2", "sse3", "ssse3", "sse4.1", "sse4.2", "avx",
        "avx2", "avx512f", "bmi",  "bmi2", "fma",   "popcnt", "aes",    "pclmul",
    };
    for (const char* n : names) {
        if (__builtin_cpu_supports(n)) {
            // Normalize "sse4.1"/"sse4.2" to "sse4_1"/"sse4_2" to match the
            // /proc/cpuinfo spelling that hw-preflight's check expects.
            std::string token = n;
            for (auto& c : token) {
                if (c == '.') c = '_';
            }
            out.push_back(token);
        }
    }
#endif
    return out;
}

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
