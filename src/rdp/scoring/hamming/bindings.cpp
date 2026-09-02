#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Hamming.h"
#include "Types.h"

namespace py = pybind11;
using namespace CommonTypes;

PYBIND11_MODULE(_hamming, m) {
    m.doc() = "Hamming word-distance backend (C++)";

    py::class_<Hamming>(m, "Hamming")
        .def(py::init<>())
        .def("update_all_words_index",
             &Hamming::update_all_words_index,
             py::arg("wordlength"), py::arg("input_list"),
             "Load dictionary entries for a given word length.")
        .def("get_min_hamming_distance",
             &Hamming::get_min_hamming_distance,
             py::arg("runes_index"), py::arg("word_indices"),
             "Minimum Hamming distance for a single word.")
        .def("find_min_HD",
             &Hamming::find_min_HD,
             py::arg("runes_index"), py::arg("wli_data"), py::arg("max_hd"),
             "Total minimum Hamming distance across all words (uses WLI to segment).")
        .def("get_min_hamming_distance_verbose",
             &Hamming::get_min_hamming_distance_verbose,
             py::arg("runes_index"), py::arg("word_indices"))
        .def("find_min_HD_verbose",
             &Hamming::find_min_HD_verbose,
             py::arg("runes_index"), py::arg("wli_data"), py::arg("max_hd"))
        .def("status", &Hamming::status);
}
