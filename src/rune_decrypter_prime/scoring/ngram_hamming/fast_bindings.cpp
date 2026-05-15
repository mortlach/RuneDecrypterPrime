#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "FastNgramHamming.h"

namespace py = pybind11;
namespace core = FastNgramHammingCore;

static int parse_int_token(const py::handle& item, const std::string& field_name) {
    if (PyBool_Check(item.ptr()) || !PyLong_Check(item.ptr())) {
        throw std::invalid_argument(field_name + " token is not an integer");
    }
    int token = py::cast<int>(item);
    if (token < 0 || token > 28) {
        throw std::invalid_argument(field_name + " token outside 0..28");
    }
    return token;
}

static std::vector<int> parse_token_sequence(const py::handle& value, const std::string& field_name) {
    py::sequence seq = py::reinterpret_borrow<py::sequence>(value);
    std::vector<int> out;
    out.reserve(seq.size());
    for (const auto& item : seq) {
        out.push_back(parse_int_token(item, field_name));
    }
    if (out.empty()) {
        throw std::invalid_argument(field_name + " is empty");
    }
    return out;
}

static core::PhraseProfile parse_profile(const py::dict& row) {
    core::PhraseProfile profile;
    profile.profile_id = py::cast<std::string>(row["profile_id"]);
    profile.direction = py::cast<std::string>(row["direction"]);
    profile.orders = py::cast<std::vector<int>>(row["orders"]);
    profile.dictionary_cuts = py::cast<std::vector<std::string>>(row["dictionary_cuts"]);
    profile.min_phrase_token_length = py::cast<int>(row["min_phrase_token_length"]);
    profile.max_total_phrase_hd = py::cast<int>(row["max_total_phrase_hd"]);
    profile.max_word_hd = py::cast<int>(row["max_word_hd"]);
    if (row.contains("normalised_hd_ceiling") && !row["normalised_hd_ceiling"].is_none()) {
        profile.has_normalised_hd_ceiling = true;
        profile.normalised_hd_ceiling = py::cast<double>(row["normalised_hd_ceiling"]);
    }
    return profile;
}

static core::PhraseEntry parse_phrase_entry(const py::dict& row) {
    core::PhraseEntry entry;
    entry.phrase_id = py::cast<std::string>(row["phrase_id"]);
    entry.direction = py::cast<std::string>(row["direction"]);
    entry.dictionary_cut = py::cast<std::string>(row["dictionary_cut"]);
    entry.ngram_order = py::cast<int>(row["ngram_order"]);
    entry.rune_token_ids = parse_token_sequence(row["rune_token_ids"], "rune_token_ids");

    py::sequence words = py::reinterpret_borrow<py::sequence>(row["word_token_ids"]);
    entry.word_token_ids.reserve(words.size());
    for (const auto& word : words) {
        entry.word_token_ids.push_back(parse_token_sequence(word, "word_token_ids"));
    }
    if (entry.word_token_ids.empty()) {
        throw std::invalid_argument("word_token_ids is empty");
    }
    std::vector<int> flattened;
    for (const auto& word : entry.word_token_ids) {
        flattened.insert(flattened.end(), word.begin(), word.end());
    }
    if (flattened != entry.rune_token_ids) {
        throw std::invalid_argument("flatten(word_token_ids) != rune_token_ids");
    }
    if (static_cast<int>(entry.word_token_ids.size()) != entry.ngram_order) {
        throw std::invalid_argument("word_token_ids group count != ngram_order");
    }

    if (row.contains("count")) {
        entry.count = py::cast<double>(row["count"]);
    }
    if (row.contains("log_count")) {
        entry.log_count = py::cast<double>(row["log_count"]);
    }
    if (row.contains("phrase_count")) {
        entry.phrase_count = py::cast<int>(row["phrase_count"]);
    }
    return entry;
}

static py::dict hit_to_dict(const core::PhraseHit& hit) {
    py::dict row;
    row["candidate_id"] = hit.candidate_id;
    row["chunk_id"] = hit.chunk_id;
    row["damage_level"] = hit.damage_level;
    row["profile_id"] = hit.profile_id;
    row["ngram_order"] = hit.ngram_order;
    row["dictionary_cut"] = hit.dictionary_cut;
    row["phrase_id"] = hit.phrase_id;
    row["phrase_count"] = hit.phrase_count;
    row["phrase_log_count"] = hit.phrase_log_count;
    row["phrase_token_length"] = hit.phrase_token_length;
    row["word_lengths"] = hit.word_lengths;
    row["word_hds"] = hit.word_hds;
    row["total_phrase_hd"] = hit.total_phrase_hd;
    row["max_word_hd"] = hit.max_word_hd;
    row["mean_word_hd"] = hit.mean_word_hd;
    row["normalised_phrase_hd"] = hit.normalised_phrase_hd;
    row["hit_start"] = hit.hit_start;
    row["hit_end"] = hit.hit_end;
    return row;
}

static py::dict scan_result_to_dict(const core::ScanResult& result) {
    py::dict out;
    py::list hits;
    for (const auto& hit : result.phrase_hits) {
        hits.append(hit_to_dict(hit));
    }
    py::list debug_examples;
    for (const auto& hit : result.debug_examples) {
        debug_examples.append(hit_to_dict(hit));
    }
    out["phrase_hits"] = hits;
    out["candidate_tokens_scanned"] = result.candidate_tokens_scanned;
    out["candidate_start_offsets_considered"] = result.candidate_start_offsets_considered;
    out["phrase_entries_considered"] = result.phrase_entries_considered;
    out["phrase_verification_attempts"] = result.phrase_verification_attempts;
    out["phrase_verification_passes"] = result.phrase_verification_passes;
    out["opportunity_count"] = result.opportunity_count;
    out["positive_start_offset_count"] = result.positive_start_offset_count;
    out["phrase_hits_per_opportunity"] = result.phrase_hits_per_opportunity;
    out["positive_start_offset_fraction"] = result.positive_start_offset_fraction;
    out["debug_examples"] = debug_examples;
    return out;
}

PYBIND11_MODULE(_ngram_hamming_fast, m) {
    m.doc() = "Synthetic parity backend for word-structured n-gram Hamming scanning";

    m.def(
        "scan",
        [](const py::handle& tokens_obj,
           const std::vector<py::dict>& phrase_entry_rows,
           const py::dict& profile_row,
           const std::string& candidate_id,
           const std::string& chunk_id,
           const std::string& damage_level,
           int debug_example_limit) {
            std::vector<int> tokens = parse_token_sequence(tokens_obj, "candidate_tokens");
            std::vector<core::PhraseEntry> entries;
            entries.reserve(phrase_entry_rows.size());
            for (const auto& row : phrase_entry_rows) {
                entries.push_back(parse_phrase_entry(row));
            }
            core::PhraseProfile profile = parse_profile(profile_row);
            return scan_result_to_dict(core::scan(
                tokens,
                entries,
                profile,
                candidate_id,
                chunk_id,
                damage_level,
                debug_example_limit));
        },
        py::arg("tokens"),
        py::arg("phrase_entries"),
        py::arg("profile"),
        py::arg("candidate_id") = "",
        py::arg("chunk_id") = "",
        py::arg("damage_level") = "",
        py::arg("debug_example_limit") = 0,
        "Scan one candidate token sequence against in-memory phrase entries.");
}
