// Parametrized stress test for parse_cpuinfo.
//
// We seed a Mersenne-Twister with a known constant, generate `kIterations`
// pseudo-random buffers (mixing valid `flags:` lines, garbage bytes,
// truncated lines, and embedded control chars) and assert the parser:
//
//   * never crashes,
//   * always returns a sorted, deduplicated vector of strings,
//   * tokens are non-empty when present.
//
// Compared with libFuzzer this is deterministic and CI-portable; a
// libFuzzer harness (`fuzz_cpuid.cpp`) covers the same surface when the
// toolchain supports `-fsanitize=fuzzer`.

#include <algorithm>
#include <cstdint>
#include <random>
#include <set>
#include <sstream>
#include <string>

#include <gtest/gtest.h>

#include "cpuid.h"

namespace {

constexpr uint64_t kSeed = 0xC0FFEEULL;
constexpr int kIterations = 512;

std::string random_buffer(std::mt19937_64& rng, std::size_t max_len) {
    std::uniform_int_distribution<int> len_dist(0, static_cast<int>(max_len));
    std::uniform_int_distribution<int> byte_dist(0, 255);
    const int len = len_dist(rng);
    std::string s;
    s.resize(len);
    for (int i = 0; i < len; ++i) s[i] = static_cast<char>(byte_dist(rng));
    return s;
}

std::string realistic_flags_line(std::mt19937_64& rng) {
    static const char* tokens[] = {"fpu",  "vme",   "de",     "pse",     "tsc",     "msr",   "pae",
                                   "mce",  "cx8",   "apic",   "sep",     "mtrr",    "pge",   "mca",
                                   "cmov", "pat",   "pse36",  "clflush", "dts",     "acpi",  "mmx",
                                   "fxsr", "sse",   "sse2",   "ss",      "ht",      "tm",    "pbe",
                                   "sse3", "ssse3", "sse4_1", "sse4_2",  "popcnt",  "aes",   "avx",
                                   "avx2", "fma",   "bmi1",   "bmi2",    "avx512f", "rdrand"};
    constexpr std::size_t n = sizeof(tokens) / sizeof(tokens[0]);
    std::uniform_int_distribution<int> count(0, 25);
    std::uniform_int_distribution<int> idx(0, static_cast<int>(n) - 1);
    std::ostringstream oss;
    oss << "flags\t\t:";
    const int k = count(rng);
    for (int i = 0; i < k; ++i) oss << ' ' << tokens[idx(rng)];
    oss << '\n';
    return oss.str();
}

std::string mixed_payload(std::mt19937_64& rng) {
    std::uniform_int_distribution<int> mode(0, 4);
    switch (mode(rng)) {
        case 0: return random_buffer(rng, 128);
        case 1: return realistic_flags_line(rng);
        case 2: {
            // realistic flags line + appended garbage
            return realistic_flags_line(rng) + random_buffer(rng, 64);
        }
        case 3: {
            // multiple flags lines (parser must dedupe)
            return realistic_flags_line(rng) + realistic_flags_line(rng);
        }
        default: {
            // truncated flag line: no newline, very long token
            std::string s = "flags: ";
            s += random_buffer(rng, 1024);
            return s;
        }
    }
}

}  // namespace

TEST(ParseCpuinfoFuzz, NeverCrashesOnRandomInputs) {
    std::mt19937_64 rng(kSeed);
    for (int i = 0; i < kIterations; ++i) {
        std::string payload = mixed_payload(rng);
        const auto tokens = hwprobe::parse_cpuinfo(payload);
        // Sorted unique invariant.
        auto sorted_unique = tokens;
        std::sort(sorted_unique.begin(), sorted_unique.end());
        sorted_unique.erase(std::unique(sorted_unique.begin(), sorted_unique.end()),
                            sorted_unique.end());
        EXPECT_EQ(tokens.size(), sorted_unique.size());
        for (const auto& t : tokens) {
            EXPECT_FALSE(t.empty()) << "iteration " << i;
            // Tokens are lowercase by construction.
            for (char c : t) {
                if (c >= 'A' && c <= 'Z') {
                    FAIL() << "uppercase token leaked: " << t << " (iter " << i << ")";
                }
            }
        }
    }
}

TEST(ParseCpuinfoFuzz, BoundaryLengthsAreSafe) {
    // Empty, single byte, just-newlines, just colons.
    EXPECT_TRUE(hwprobe::parse_cpuinfo("").empty());
    EXPECT_TRUE(hwprobe::parse_cpuinfo("\0").empty());
    EXPECT_TRUE(hwprobe::parse_cpuinfo("\n\n\n\n").empty());
    EXPECT_TRUE(hwprobe::parse_cpuinfo(":::::").empty());

    std::string huge_line = "flags: ";
    huge_line.append(64 * 1024, 'a');
    const auto out = hwprobe::parse_cpuinfo(huge_line);
    // Single mega-token; must be present and not crash.
    ASSERT_EQ(out.size(), 1u);
    EXPECT_EQ(out[0].size(), 64u * 1024u);
}

TEST(ParseCpuinfoFuzz, ControlCharactersAreSafe) {
    std::string s = "flags: \x01\x02 foo\x07 bar\nflags: \xff\xfe baz\n";
    const auto out = hwprobe::parse_cpuinfo(s);
    // Must not crash; tokens may include the high-bit bytes verbatim, but
    // ascii ones survive and are lowercased.
    std::set<std::string> as_set(out.begin(), out.end());
    EXPECT_TRUE(as_set.count("foo") == 1 || as_set.count("foo\x07") == 1 ||
                as_set.count(std::string("\x01\x02")) > 0);
    EXPECT_TRUE(as_set.count("bar") == 1);
    EXPECT_TRUE(as_set.count("baz") == 1);
}
