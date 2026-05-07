#include <algorithm>

#include <gtest/gtest.h>

#include "cpuid.h"

namespace {

bool contains(const std::vector<std::string>& v, const std::string& s) {
    return std::find(v.begin(), v.end(), s) != v.end();
}

}  // namespace

TEST(ParseCpuinfo, ExtractsFlagsLineAndLowercases) {
    const char* contents =
        "processor\t: 0\n"
        "vendor_id\t: GenuineIntel\n"
        "flags\t\t: fpu vme de SSE4_2 AVX\n"
        "model\t\t: 158\n";
    auto tokens = hwprobe::parse_cpuinfo(contents);
    EXPECT_TRUE(contains(tokens, "fpu"));
    EXPECT_TRUE(contains(tokens, "sse4_2"));
    EXPECT_TRUE(contains(tokens, "avx"));
    EXPECT_FALSE(contains(tokens, "AVX"));
}

TEST(ParseCpuinfo, HandlesArmFeaturesLine) {
    const char* contents =
        "processor\t: 0\n"
        "Features\t: fp asimd evtstrm aes pmull\n";
    auto tokens = hwprobe::parse_cpuinfo(contents);
    EXPECT_TRUE(contains(tokens, "fp"));
    EXPECT_TRUE(contains(tokens, "asimd"));
    EXPECT_TRUE(contains(tokens, "aes"));
}

TEST(ParseCpuinfo, EmptyOrNoFlagsReturnsEmpty) {
    EXPECT_TRUE(hwprobe::parse_cpuinfo("").empty());
    EXPECT_TRUE(hwprobe::parse_cpuinfo("processor: 0\n").empty());
}

TEST(ParseCpuinfo, Deduplicates) {
    const char* contents =
        "flags\t: foo bar foo\n"
        "flags\t: bar baz\n";
    auto tokens = hwprobe::parse_cpuinfo(contents);
    EXPECT_EQ(tokens.size(), 3u);
    EXPECT_TRUE(contains(tokens, "foo"));
    EXPECT_TRUE(contains(tokens, "bar"));
    EXPECT_TRUE(contains(tokens, "baz"));
}

TEST(CpuFeatures, RuntimeReturnsSomethingOrNothing) {
    // We can't assert content (varies across machines/CI), but the call
    // must complete without throwing and produce sorted unique tokens.
    auto f = hwprobe::cpu_features();
    auto sorted = f;
    std::sort(sorted.begin(), sorted.end());
    EXPECT_EQ(f, sorted);
}
