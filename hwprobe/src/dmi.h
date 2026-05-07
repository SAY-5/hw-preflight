// DMI fields exposed by sysfs.
//
// /sys/class/dmi/id/* contains files such as `bios_vendor`, `product_name`,
// `sys_vendor`. Reads are non-privileged for most fields but a few (e.g.
// `product_serial`) are root-only and silently skipped.

#pragma once

#include <map>
#include <string>

namespace hwprobe {

std::map<std::string, std::string> dmi_fields(const std::string& root = "/sys/class/dmi/id");

}  // namespace hwprobe
