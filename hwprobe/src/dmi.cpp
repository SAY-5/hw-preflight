#include "dmi.h"

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <sstream>

namespace hwprobe {

namespace fs = std::filesystem;

namespace {

std::string trim(std::string s) {
    auto not_space = [](unsigned char c) { return !std::isspace(c); };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
    s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
    return s;
}

}  // namespace

std::map<std::string, std::string> dmi_fields(const std::string& root) {
    std::map<std::string, std::string> out;
    std::error_code ec;
    if (!fs::exists(root, ec) || !fs::is_directory(root, ec)) {
        return out;
    }
    for (const auto& entry : fs::directory_iterator(root, ec)) {
        if (ec) break;
        if (!entry.is_regular_file()) continue;
        std::ifstream in(entry.path());
        if (!in) continue;
        std::ostringstream oss;
        oss << in.rdbuf();
        std::string value = trim(oss.str());
        if (value.empty()) continue;
        out.emplace(entry.path().filename().string(), value);
    }
    return out;
}

}  // namespace hwprobe
