// Standalone CLI for the hwprobe helper. Useful for debugging the same
// data the Python binding sees, without going through Python.
//
//   $ hwprobe cpuid     # prints {"features": [...]}
//   $ hwprobe dmi       # prints {"<field>": "<value>", ...}

#include <iostream>
#include <string>
#include <string_view>

#include "cpuid.h"
#include "dmi.h"

namespace {

std::string json_escape(std::string_view s) {
    std::string out;
    out.reserve(s.size() + 2);
    for (char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += c;
                }
        }
    }
    return out;
}

void print_cpuid() {
    auto features = hwprobe::cpu_features();
    std::cout << "{\"features\": [";
    for (size_t i = 0; i < features.size(); ++i) {
        if (i) std::cout << ", ";
        std::cout << "\"" << json_escape(features[i]) << "\"";
    }
    std::cout << "]}\n";
}

void print_dmi() {
    auto fields = hwprobe::dmi_fields();
    std::cout << "{";
    bool first = true;
    for (const auto& [k, v] : fields) {
        if (!first) std::cout << ", ";
        first = false;
        std::cout << "\"" << json_escape(k) << "\": \"" << json_escape(v) << "\"";
    }
    std::cout << "}\n";
}

void usage(int code) {
    std::cerr << "usage: hwprobe {cpuid|dmi}\n";
    std::exit(code);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) usage(2);
    std::string cmd = argv[1];
    if (cmd == "cpuid") {
        print_cpuid();
        return 0;
    }
    if (cmd == "dmi") {
        print_dmi();
        return 0;
    }
    if (cmd == "-h" || cmd == "--help") {
        usage(0);
    }
    usage(2);
}
