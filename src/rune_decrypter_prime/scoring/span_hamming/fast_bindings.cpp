#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "FastSpanHamming.h"

namespace py = pybind11;

static py::dict interval_to_dict(const FastSpanHamming::Interval& interval) {
    py::dict row;
    row["start"] = interval.start;
    row["end"] = interval.end;
    row["length"] = interval.length;
    row["distance"] = interval.distance;
    row["quality"] = interval.quality;
    row["weight"] = interval.weight;
    return row;
}

static py::dict stats_to_dict(const FastSpanHamming::Stats& stats) {
    py::dict out;
    out["span_raw"] = stats.span_raw;
    out["coverage"] = stats.coverage;
    out["quality"] = stats.quality;
    out["n_chars"] = stats.n_chars;
    out["chars_covered"] = stats.chars_covered;
    out["n_intervals_selected"] = stats.n_intervals_selected;
    out["length_bins"] = stats.length_bins;
    out["span_raw_by_len"] = stats.span_raw_by_len;
    out["coverage_by_len"] = stats.coverage_by_len;
    out["quality_by_len"] = stats.quality_by_len;
    out["selected_intervals_by_len"] = stats.selected_intervals_by_len;
    out["chars_covered_by_len"] = stats.chars_covered_by_len;
    out["n_windows_total"] = stats.n_windows_total;
    out["n_windows_scored"] = stats.n_windows_scored;
    out["n_candidates_considered"] = stats.n_candidates_considered;
    out["n_candidates_pruned_cap"] = stats.n_candidates_pruned_cap;

    py::list selected;
    for (const auto& interval : stats.selected_intervals) {
        selected.append(interval_to_dict(interval));
    }
    out["selected_intervals"] = selected;

    py::list raw;
    for (const auto& interval : stats.raw_intervals) {
        raw.append(interval_to_dict(interval));
    }
    out["raw_intervals"] = raw;
    return out;
}

PYBIND11_MODULE(_span_hamming_fast, m) {
    m.doc() = "Fast span-Hamming backend for report-only calibration and parity probes";

    py::class_<FastSpanHamming>(m, "FastSpanHamming")
        .def(py::init<>())
        .def(
            "update_words_index",
            &FastSpanHamming::update_words_index,
            py::arg("length"),
            py::arg("input_words"),
            py::arg("max_hd"),
            "Load dictionary entries for a span length.")
        .def(
            "score",
            [](FastSpanHamming& self,
               const std::vector<int>& text,
               int len_min,
               int len_max,
               int max_hd,
               int start_stride,
               int max_windows_total,
               int max_candidates_per_window,
               int max_intervals_considered_per_start,
               double min_quality_threshold,
               bool return_selected_intervals,
               bool return_raw_intervals) {
                FastSpanHamming::Config config;
                config.len_min = len_min;
                config.len_max = len_max;
                config.max_hd = max_hd;
                config.start_stride = start_stride;
                config.max_windows_total = max_windows_total;
                config.max_candidates_per_window = max_candidates_per_window;
                config.max_intervals_considered_per_start = max_intervals_considered_per_start;
                config.min_quality_threshold = min_quality_threshold;
                return stats_to_dict(self.score(text, config, return_selected_intervals, return_raw_intervals));
            },
            py::arg("text"),
            py::arg("len_min"),
            py::arg("len_max"),
            py::arg("max_hd"),
            py::arg("start_stride"),
            py::arg("max_windows_total"),
            py::arg("max_candidates_per_window"),
            py::arg("max_intervals_considered_per_start"),
            py::arg("min_quality_threshold"),
            py::arg("return_selected_intervals") = false,
            py::arg("return_raw_intervals") = false,
            "Score one numeric rune/base-29 token sequence.");
}
