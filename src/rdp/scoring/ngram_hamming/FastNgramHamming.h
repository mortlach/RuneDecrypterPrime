#pragma once

#include <algorithm>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace FastNgramHammingCore {

struct PhraseProfile {
    std::string profile_id;
    std::string direction;
    std::vector<int> orders;
    std::vector<std::string> dictionary_cuts;
    int min_phrase_token_length = 0;
    int max_total_phrase_hd = 0;
    int max_word_hd = 0;
    bool has_normalised_hd_ceiling = false;
    double normalised_hd_ceiling = 0.0;
    std::vector<int> exact_match_word_lengths;
};

struct PhraseEntry {
    std::string phrase_id;
    std::string direction;
    std::string dictionary_cut;
    int ngram_order = 0;
    std::vector<std::vector<int>> word_token_ids;
    std::vector<int> rune_token_ids;
    double count = 0.0;
    double log_count = 0.0;
    int phrase_count = 1;
};

struct PhraseHit {
    std::string candidate_id;
    std::string chunk_id;
    std::string damage_level;
    std::string profile_id;
    int ngram_order = 0;
    std::string dictionary_cut;
    std::string phrase_id;
    int phrase_count = 1;
    double phrase_log_count = 0.0;
    int phrase_token_length = 0;
    std::vector<int> word_lengths;
    std::vector<int> word_hds;
    int total_phrase_hd = 0;
    int max_word_hd = 0;
    double mean_word_hd = 0.0;
    double normalised_phrase_hd = 0.0;
    int hit_start = 0;
    int hit_end = 0;
};

struct ScanResult {
    std::vector<PhraseHit> phrase_hits;
    int candidate_tokens_scanned = 0;
    int candidate_start_offsets_considered = 0;
    int phrase_entries_considered = 0;
    int phrase_verification_attempts = 0;
    int phrase_verification_passes = 0;
    int opportunity_count = 0;
    int positive_start_offset_count = 0;
    double phrase_hits_per_opportunity = 0.0;
    double positive_start_offset_fraction = 0.0;
    std::vector<PhraseHit> debug_examples;
};

inline void validate_tokens(const std::vector<int>& tokens, const std::string& field_name) {
    if (tokens.empty()) {
        throw std::invalid_argument(field_name + " is empty");
    }
    for (int token : tokens) {
        if (token < 0 || token > 28) {
            throw std::invalid_argument(field_name + " token outside 0..28");
        }
    }
}

inline std::vector<int> word_lengths(const PhraseEntry& entry) {
    std::vector<int> out;
    out.reserve(entry.word_token_ids.size());
    for (const auto& word : entry.word_token_ids) {
        out.push_back(static_cast<int>(word.size()));
    }
    return out;
}

inline int phrase_token_length(const PhraseEntry& entry) {
    return static_cast<int>(entry.rune_token_ids.size());
}

inline bool contains_int(const std::vector<int>& values, int value) {
    return std::find(values.begin(), values.end(), value) != values.end();
}

inline bool contains_string(const std::vector<std::string>& values, const std::string& value) {
    return std::find(values.begin(), values.end(), value) != values.end();
}

inline bool profile_allows_entry(const PhraseEntry& entry, const PhraseProfile& profile) {
    return entry.direction == profile.direction &&
        contains_int(profile.orders, entry.ngram_order) &&
        contains_string(profile.dictionary_cuts, entry.dictionary_cut) &&
        phrase_token_length(entry) >= profile.min_phrase_token_length;
}

inline bool phrase_could_fit_at_start(
    const std::vector<int>& tokens,
    int start,
    const PhraseEntry& entry,
    const PhraseProfile& profile) {
    if (!profile_allows_entry(entry, profile)) {
        return false;
    }
    return start + phrase_token_length(entry) <= static_cast<int>(tokens.size());
}

inline int hamming_at(const std::vector<int>& tokens, int start, const std::vector<int>& word) {
    int distance = 0;
    for (int idx = 0; idx < static_cast<int>(word.size()); ++idx) {
        if (tokens[start + idx] != word[idx]) {
            distance += 1;
        }
    }
    return distance;
}

inline bool verify_phrase_at_start(
    const std::vector<int>& tokens,
    int start,
    const PhraseEntry& entry,
    const PhraseProfile& profile,
    const std::string& candidate_id,
    const std::string& chunk_id,
    const std::string& damage_level,
    PhraseHit& out_hit) {
    int offset = start;
    std::vector<int> hds;
    hds.reserve(entry.word_token_ids.size());
    for (const auto& word : entry.word_token_ids) {
        int end = offset + static_cast<int>(word.size());
        if (end > static_cast<int>(tokens.size())) {
            return false;
        }
        int distance = hamming_at(tokens, offset, word);
        if (contains_int(profile.exact_match_word_lengths, static_cast<int>(word.size())) && distance != 0) {
            return false;
        }
        if (distance > profile.max_word_hd) {
            return false;
        }
        hds.push_back(distance);
        offset = end;
    }

    int total_hd = 0;
    int max_hd = 0;
    for (int distance : hds) {
        total_hd += distance;
        max_hd = std::max(max_hd, distance);
    }
    if (total_hd > profile.max_total_phrase_hd) {
        return false;
    }

    int token_length = phrase_token_length(entry);
    double normalised = token_length > 0 ? static_cast<double>(total_hd) / static_cast<double>(token_length) : 0.0;
    if (profile.has_normalised_hd_ceiling && normalised > profile.normalised_hd_ceiling) {
        return false;
    }

    out_hit.candidate_id = candidate_id;
    out_hit.chunk_id = chunk_id;
    out_hit.damage_level = damage_level;
    out_hit.profile_id = profile.profile_id;
    out_hit.ngram_order = entry.ngram_order;
    out_hit.dictionary_cut = entry.dictionary_cut;
    out_hit.phrase_id = entry.phrase_id;
    out_hit.phrase_count = entry.phrase_count;
    out_hit.phrase_log_count = entry.log_count;
    out_hit.phrase_token_length = token_length;
    out_hit.word_lengths = word_lengths(entry);
    out_hit.word_hds = std::move(hds);
    out_hit.total_phrase_hd = total_hd;
    out_hit.max_word_hd = max_hd;
    out_hit.mean_word_hd = out_hit.word_hds.empty()
        ? 0.0
        : static_cast<double>(total_hd) / static_cast<double>(out_hit.word_hds.size());
    out_hit.normalised_phrase_hd = normalised;
    out_hit.hit_start = start;
    out_hit.hit_end = start + token_length;
    return true;
}

inline ScanResult scan(
    const std::vector<int>& tokens,
    const std::vector<PhraseEntry>& phrase_entries,
    const PhraseProfile& profile,
    const std::string& candidate_id,
    const std::string& chunk_id,
    const std::string& damage_level,
    int debug_example_limit) {
    validate_tokens(tokens, "candidate_tokens");

    std::vector<PhraseEntry> entries;
    entries.reserve(phrase_entries.size());
    for (const auto& entry : phrase_entries) {
        if (profile_allows_entry(entry, profile)) {
            entries.push_back(entry);
        }
    }

    ScanResult result;
    result.candidate_tokens_scanned = static_cast<int>(tokens.size());
    result.candidate_start_offsets_considered = static_cast<int>(tokens.size());
    result.phrase_entries_considered = static_cast<int>(entries.size());

    std::unordered_set<int> opportunity_offsets;
    std::unordered_set<int> positive_offsets;

    for (int start = 0; start < static_cast<int>(tokens.size()); ++start) {
        bool any_fit = false;
        for (const auto& entry : entries) {
            if (!phrase_could_fit_at_start(tokens, start, entry, profile)) {
                continue;
            }
            any_fit = true;
            result.phrase_verification_attempts += 1;
            PhraseHit hit;
            if (verify_phrase_at_start(tokens, start, entry, profile, candidate_id, chunk_id, damage_level, hit)) {
                result.phrase_verification_passes += 1;
                positive_offsets.insert(start);
                result.phrase_hits.push_back(hit);
                if (static_cast<int>(result.debug_examples.size()) < std::max(0, debug_example_limit)) {
                    result.debug_examples.push_back(hit);
                }
            }
        }
        if (any_fit) {
            opportunity_offsets.insert(start);
        }
    }

    result.opportunity_count = static_cast<int>(opportunity_offsets.size());
    result.positive_start_offset_count = static_cast<int>(positive_offsets.size());
    if (result.opportunity_count > 0) {
        result.phrase_hits_per_opportunity =
            static_cast<double>(result.phrase_hits.size()) / static_cast<double>(result.opportunity_count);
        result.positive_start_offset_fraction =
            static_cast<double>(result.positive_start_offset_count) / static_cast<double>(result.opportunity_count);
    }
    return result;
}

}  // namespace FastNgramHammingCore
