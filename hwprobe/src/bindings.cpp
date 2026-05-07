// pybind11 entry point. Exposes the same primitives the standalone CLI uses.
//
// Built only when CMake is invoked with -DHWPROBE_BUILD_BINDINGS=ON. The
// Python wrapper in src/hw_preflight/_hwprobe.py imports the module
// `hw_preflight._hwprobe_ext` lazily and falls back to pure-Python parsers
// when the extension is unavailable.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "cpuid.h"
#include "dmi.h"

namespace py = pybind11;

PYBIND11_MODULE(_hwprobe_ext, m) {
    m.doc() = "C++ helper for hw-preflight: CPUID feature flags and DMI fields";
    m.def("cpu_features", &hwprobe::cpu_features,
          "Return the list of CPU feature flag tokens reported by the kernel "
          "merged with __builtin_cpu_supports detection on x86.");
    m.def("dmi_fields", &hwprobe::dmi_fields, py::arg("root") = std::string("/sys/class/dmi/id"),
          "Return a dict of DMI field name -> value, read from /sys/class/dmi/id.");
}
