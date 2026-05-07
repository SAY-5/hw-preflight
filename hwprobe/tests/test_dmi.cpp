#include <cstdio>
#include <filesystem>
#include <fstream>

#include <gtest/gtest.h>

#include "dmi.h"

namespace fs = std::filesystem;

namespace {

class TempDir {
public:
    TempDir() {
        path_ = fs::temp_directory_path() / "hwprobe_dmi_test";
        std::error_code ec;
        fs::remove_all(path_, ec);
        fs::create_directories(path_);
    }
    ~TempDir() {
        std::error_code ec;
        fs::remove_all(path_, ec);
    }
    void write(const std::string& name, const std::string& body) {
        std::ofstream out(path_ / name);
        out << body;
    }
    std::string str() const { return path_.string(); }

private:
    fs::path path_;
};

}  // namespace

TEST(DmiFields, ReadsFilesAndTrimsWhitespace) {
    TempDir td;
    td.write("bios_vendor", "Acme Corp\n");
    td.write("product_name", "  ProductX  \n");
    td.write("empty_field", "\n");
    auto fields = hwprobe::dmi_fields(td.str());
    EXPECT_EQ(fields["bios_vendor"], "Acme Corp");
    EXPECT_EQ(fields["product_name"], "ProductX");
    EXPECT_EQ(fields.count("empty_field"), 0u);
}

TEST(DmiFields, MissingDirectoryReturnsEmpty) {
    auto fields = hwprobe::dmi_fields("/nonexistent/path/for/test/12345");
    EXPECT_TRUE(fields.empty());
}
