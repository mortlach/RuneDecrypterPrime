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


static py::dict fingerprint_bin_to_dict(const FastSpanHamming::FingerprintBin& bin) {
    py::dict row;
    row["offset"] = bin.offset;
    row["length"] = bin.length;
    row["hd"] = bin.hd;
    row["raw_match_count"] = bin.raw_match_count;
    return row;
}

static py::dict fingerprint_match_dump_row_to_dict(const FastSpanHamming::FingerprintMatchDumpRow& row_in) {
    py::dict row;
    row["offset"] = row_in.offset;
    row["length"] = row_in.length;
    row["word_id"] = row_in.word_id;
    row["hd"] = row_in.hd;
    return row;
}

static py::dict fingerprint_stats_to_dict(const FastSpanHamming::FingerprintStats& stats) {
    py::dict out;
    out["n_chars"] = stats.n_chars;
    out["n_windows_total"] = stats.n_windows_total;
    out["n_windows_scored"] = stats.n_windows_scored;
    out["n_candidates_considered"] = stats.n_candidates_considered;
    out["n_candidates_pruned_cap"] = stats.n_candidates_pruned_cap;
    out["length_bins"] = stats.length_bins;
    out["n_windows_total_by_len"] = stats.n_windows_total_by_len;
    out["n_windows_scored_by_len"] = stats.n_windows_scored_by_len;
    out["n_candidates_considered_by_len"] = stats.n_candidates_considered_by_len;
    out["n_candidates_pruned_cap_by_len"] = stats.n_candidates_pruned_cap_by_len;
    out["fingerprint_scope"] = "raw_hamming_counts";
    out["hd_max_policy"] = "length_minus_one";
    out["supports_uncapped_or_full_scan"] = true;

    py::list chunk_bins;
    for (const auto& bin : stats.chunk_bins) {
        chunk_bins.append(fingerprint_bin_to_dict(bin));
    }
    out["chunk_bins"] = chunk_bins;

    py::list offset_bins;
    for (const auto& bin : stats.offset_bins) {
        offset_bins.append(fingerprint_bin_to_dict(bin));
    }
    out["offset_bins"] = offset_bins;

    py::list match_dump_rows;
    for (const auto& row : stats.match_dump_rows) {
        match_dump_rows.append(fingerprint_match_dump_row_to_dict(row));
    }
    out["match_dump_rows"] = match_dump_rows;

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
            "Score one numeric rune/base-29 token sequence.")
        .def(
            "fingerprint_raw_hamming_counts",
            [](FastSpanHamming& self,
               const std::vector<int>& text,
               int len_min,
               int len_max,
               int start_stride,
               int max_windows_total,
               int max_candidates_per_window,
               bool include_offset_rows,
               bool include_match_dump) {
                FastSpanHamming::FingerprintConfig config;
                config.len_min = len_min;
                config.len_max = len_max;
                config.start_stride = start_stride;
                config.max_windows_total = max_windows_total;
                config.max_candidates_per_window = max_candidates_per_window;
                config.include_offset_rows = include_offset_rows;
                config.include_match_dump = include_match_dump;
                return fingerprint_stats_to_dict(self.fingerprint_raw_hamming_counts(text, config));
            },
            py::arg("text"),
            py::arg("len_min"),
            py::arg("len_max"),
            py::arg("start_stride"),
            py::arg("max_windows_total"),
            py::arg("max_candidates_per_window") = 0,
            py::arg("include_offset_rows") = false,
            py::arg("include_match_dump") = false,
            "Return raw length-by-HD span-Hamming fingerprint counts. HD bins are 0..length-1.");
}
