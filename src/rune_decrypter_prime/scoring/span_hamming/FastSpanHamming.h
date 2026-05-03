#ifndef FAST_SPAN_HAMMING_H
#define FAST_SPAN_HAMMING_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

class FastSpanHamming {
public:
    struct Config {
        int len_min = 3;
        int len_max = 14;
        int max_hd = 2;
        int start_stride = 1;
        int max_windows_total = 0;
        int max_candidates_per_window = 256;
        int max_intervals_considered_per_start = 4;
        double min_quality_threshold = 1e-9;
    };

    struct Interval {
        int start = 0;
        int end = 0;
        int length = 0;
        int distance = 0;
        double quality = 0.0;
        double weight = 0.0;

        std::tuple<int, int, int> canonical_key() const {
            return std::make_tuple(end, start, -length);
        }
    };

    struct Stats {
        double span_raw = 0.0;
        double coverage = 0.0;
        double quality = 0.0;
        int n_chars = 0;
        int chars_covered = 0;
        int n_intervals_selected = 0;
        std::vector<int> length_bins;
        std::vector<double> span_raw_by_len;
        std::vector<double> coverage_by_len;
        std::vector<double> quality_by_len;
        std::vector<int> selected_intervals_by_len;
        std::vector<int> chars_covered_by_len;
        int n_windows_total = 0;
        int n_windows_scored = 0;
        std::int64_t n_candidates_considered = 0;
        std::int64_t n_candidates_pruned_cap = 0;
        std::vector<Interval> selected_intervals;
        std::vector<Interval> raw_intervals;
    };

    void update_words_index(int length, const std::vector<std::vector<int>>& input_words, int max_hd) {
        if (length < 1) {
            throw std::invalid_argument("length must be >= 1");
        }
        if (max_hd < 0) {
            throw std::invalid_argument("max_hd must be >= 0");
        }

        LengthIndex index;
        index.length = length;
        index.max_hd = max_hd;

        std::vector<std::vector<int>> words;
        for (const auto& word : input_words) {
            if (static_cast<int>(word.size()) == length) {
                words.push_back(word);
            }
        }
        std::sort(words.begin(), words.end());
        words.erase(std::unique(words.begin(), words.end()), words.end());
        index.words = std::move(words);

        if (index.words.empty()) {
            indexes_[length] = std::move(index);
            return;
        }

        index.n_parts = std::min(length, max_hd + 1);
        index.part_slices = partition_slices(length, index.n_parts);
        index.use_packed_keys = true;
        for (const auto& slice : index.part_slices) {
            if (slice.second - slice.first > 12) {
                index.use_packed_keys = false;
                break;
            }
        }
        index.seen_generation.assign(index.words.size(), 0);

        for (int word_id = 0; word_id < static_cast<int>(index.words.size()); ++word_id) {
            const auto& word = index.words[static_cast<size_t>(word_id)];
            for (int part_id = 0; part_id < index.n_parts; ++part_id) {
                const auto& slice = index.part_slices[static_cast<size_t>(part_id)];
                if (index.use_packed_keys) {
                    std::uint64_t key = make_packed_key(part_id, word, slice.first, slice.second);
                    index.buckets64[key].push_back(word_id);
                } else {
                    std::string key = make_string_key(part_id, word, slice.first, slice.second);
                    index.buckets_string[key].push_back(word_id);
                }
            }
        }

        indexes_[length] = std::move(index);
    }

    Stats score(
        const std::vector<int>& text,
        const Config& config,
        bool return_selected_intervals,
        bool return_raw_intervals
    ) {
        validate_config(config);

        Stats stats;
        stats.n_chars = static_cast<int>(text.size());
        for (int length = config.len_min; length <= config.len_max; ++length) {
            stats.length_bins.push_back(length);
        }
        const size_t n_bins = stats.length_bins.size();
        stats.span_raw_by_len.assign(n_bins, 0.0);
        stats.coverage_by_len.assign(n_bins, 0.0);
        stats.quality_by_len.assign(n_bins, 0.0);
        stats.selected_intervals_by_len.assign(n_bins, 0);
        stats.chars_covered_by_len.assign(n_bins, 0);

        if (stats.n_chars == 0 || stats.n_chars < config.len_min) {
            return stats;
        }

        const int max_dist = config.max_hd + 1;
        std::vector<Interval> intervals;
        bool reached_window_cap = false;

        for (int start = 0; start < stats.n_chars; start += config.start_stride) {
            std::vector<Interval> intervals_for_start;

            for (int length : stats.length_bins) {
                const int end = start + length;
                if (end > stats.n_chars) {
                    continue;
                }
                if (config.max_windows_total > 0 && stats.n_windows_total >= config.max_windows_total) {
                    reached_window_cap = true;
                    break;
                }
                stats.n_windows_total += 1;

                auto index_it = indexes_.find(length);
                if (index_it == indexes_.end()) {
                    continue;
                }
                LengthIndex& index = index_it->second;
                if (index.words.empty()) {
                    continue;
                }

                std::vector<int> candidate_ids = candidate_word_ids(
                    index,
                    text,
                    start,
                    config.max_candidates_per_window,
                    &stats.n_candidates_pruned_cap
                );
                if (candidate_ids.empty()) {
                    continue;
                }

                stats.n_windows_scored += 1;
                stats.n_candidates_considered += static_cast<std::int64_t>(candidate_ids.size());

                int best_distance = max_dist;
                for (int word_id : candidate_ids) {
                    const auto& dict_word = index.words[static_cast<size_t>(word_id)];
                    const int distance_limit = std::max(0, best_distance - 1);
                    const int distance = hamming_distance_limited(text, start, dict_word, distance_limit);
                    const int clipped_distance = std::min(distance, max_dist);
                    if (clipped_distance < best_distance) {
                        best_distance = clipped_distance;
                        if (best_distance == 0) {
                            break;
                        }
                    }
                }

                const double best_quality = 1.0 - (static_cast<double>(best_distance) / static_cast<double>(max_dist));
                if (best_quality < config.min_quality_threshold) {
                    continue;
                }
                intervals_for_start.push_back(Interval{
                    start,
                    end,
                    length,
                    best_distance,
                    best_quality,
                    best_quality * static_cast<double>(length),
                });
            }

            if (static_cast<int>(intervals_for_start.size()) > config.max_intervals_considered_per_start) {
                std::sort(intervals_for_start.begin(), intervals_for_start.end(), interval_start_order);
                intervals_for_start.resize(static_cast<size_t>(config.max_intervals_considered_per_start));
            }
            intervals.insert(intervals.end(), intervals_for_start.begin(), intervals_for_start.end());

            if (reached_window_cap) {
                break;
            }
        }

        std::vector<Interval> selected = select_non_overlapping(intervals);
        const int covered_chars = sum_lengths(selected);
        const double sum_weight = sum_weights(selected);
        const double denom_n = static_cast<double>(std::max(1, stats.n_chars));

        stats.chars_covered = covered_chars;
        stats.n_intervals_selected = static_cast<int>(selected.size());
        stats.coverage = static_cast<double>(covered_chars) / denom_n;
        stats.quality = sum_weight / static_cast<double>(std::max(1, covered_chars));
        stats.span_raw = sum_weight / denom_n;

        std::vector<double> sum_weight_by_len(n_bins, 0.0);
        for (const auto& item : selected) {
            const size_t idx = static_cast<size_t>(item.length - config.len_min);
            sum_weight_by_len[idx] += item.weight;
            stats.chars_covered_by_len[idx] += item.length;
            stats.selected_intervals_by_len[idx] += 1;
        }
        for (size_t idx = 0; idx < n_bins; ++idx) {
            stats.span_raw_by_len[idx] = sum_weight_by_len[idx] / denom_n;
            stats.coverage_by_len[idx] = static_cast<double>(stats.chars_covered_by_len[idx]) / denom_n;
            stats.quality_by_len[idx] = (
                sum_weight_by_len[idx] / static_cast<double>(std::max(1, stats.chars_covered_by_len[idx]))
            );
        }

        if (return_selected_intervals) {
            stats.selected_intervals = std::move(selected);
        }
        if (return_raw_intervals) {
            stats.raw_intervals = std::move(intervals);
        }
        return stats;
    }

private:
    struct LengthIndex {
        int length = 0;
        int max_hd = 0;
        int n_parts = 0;
        std::vector<std::pair<int, int>> part_slices;
        std::vector<std::vector<int>> words;
        bool use_packed_keys = true;
        std::unordered_map<std::uint64_t, std::vector<int>> buckets64;
        std::unordered_map<std::string, std::vector<int>> buckets_string;
        std::vector<int> seen_generation;
        int generation = 1;
    };

    std::unordered_map<int, LengthIndex> indexes_;

    static void validate_config(const Config& config) {
        if (config.len_min < 1) throw std::invalid_argument("len_min must be >= 1");
        if (config.len_max < config.len_min) throw std::invalid_argument("len_max must be >= len_min");
        if (config.max_hd < 0) throw std::invalid_argument("max_hd must be >= 0");
        if (config.start_stride < 1) throw std::invalid_argument("start_stride must be >= 1");
        if (config.max_windows_total < 0) throw std::invalid_argument("max_windows_total must be >= 0");
        if (config.max_candidates_per_window < 1) {
            throw std::invalid_argument("max_candidates_per_window must be >= 1");
        }
        if (config.max_intervals_considered_per_start < 1) {
            throw std::invalid_argument("max_intervals_considered_per_start must be >= 1");
        }
        if (config.min_quality_threshold < 0.0 || config.min_quality_threshold > 1.0) {
            throw std::invalid_argument("min_quality_threshold must be in [0, 1]");
        }
    }

    static std::vector<std::pair<int, int>> partition_slices(int word_length, int n_parts) {
        if (word_length < 1) throw std::invalid_argument("word_length must be >= 1");
        if (n_parts < 1) throw std::invalid_argument("n_parts must be >= 1");
        if (n_parts > word_length) throw std::invalid_argument("n_parts cannot exceed word_length");

        std::vector<std::pair<int, int>> out;
        int base = word_length / n_parts;
        int remainder = word_length % n_parts;
        int cursor = 0;
        for (int part_id = 0; part_id < n_parts; ++part_id) {
            int width = base + (part_id < remainder ? 1 : 0);
            out.emplace_back(cursor, cursor + width);
            cursor += width;
        }
        return out;
    }

    static std::uint64_t make_packed_key(
        int part_id,
        const std::vector<int>& tokens,
        int start,
        int end
    ) {
        std::uint64_t key = static_cast<std::uint64_t>(part_id + 1);
        for (int idx = start; idx < end; ++idx) {
            key = (key << 5) | static_cast<std::uint64_t>(tokens[static_cast<size_t>(idx)] + 1);
        }
        return key;
    }

    static std::string make_string_key(
        int part_id,
        const std::vector<int>& tokens,
        int start,
        int end
    ) {
        std::string key;
        key.reserve(static_cast<size_t>(2 + (end - start)));
        key.push_back(static_cast<char>(part_id + 1));
        key.push_back('|');
        for (int idx = start; idx < end; ++idx) {
            key.push_back(static_cast<char>(tokens[static_cast<size_t>(idx)] + 1));
        }
        return key;
    }

    static std::vector<int> candidate_word_ids(
        LengthIndex& index,
        const std::vector<int>& text,
        int text_start,
        int max_candidates,
        std::int64_t* pruned_out
    ) {
        std::vector<int> ordered;
        index.generation += 1;
        if (index.generation == std::numeric_limits<int>::max()) {
            std::fill(index.seen_generation.begin(), index.seen_generation.end(), 0);
            index.generation = 1;
        }
        const int generation = index.generation;

        auto add_ids = [&](const std::vector<int>& ids) {
            for (int word_id : ids) {
                int& seen = index.seen_generation[static_cast<size_t>(word_id)];
                if (seen != generation) {
                    seen = generation;
                    ordered.push_back(word_id);
                }
            }
        };

        for (int part_id = 0; part_id < index.n_parts; ++part_id) {
            const auto& slice = index.part_slices[static_cast<size_t>(part_id)];
            if (index.use_packed_keys) {
                const std::uint64_t key = make_packed_key(
                    part_id,
                    text,
                    text_start + slice.first,
                    text_start + slice.second
                );
                auto found = index.buckets64.find(key);
                if (found != index.buckets64.end()) {
                    add_ids(found->second);
                }
            } else {
                const std::string key = make_string_key(
                    part_id,
                    text,
                    text_start + slice.first,
                    text_start + slice.second
                );
                auto found = index.buckets_string.find(key);
                if (found != index.buckets_string.end()) {
                    add_ids(found->second);
                }
            }
        }

        std::sort(ordered.begin(), ordered.end());
        const int all_count = static_cast<int>(ordered.size());
        if (all_count > max_candidates) {
            if (pruned_out != nullptr) {
                *pruned_out += static_cast<std::int64_t>(all_count - max_candidates);
            }
            ordered.resize(static_cast<size_t>(max_candidates));
        }
        return ordered;
    }

    static int hamming_distance_limited(
        const std::vector<int>& text,
        int text_start,
        const std::vector<int>& word,
        int max_value
    ) {
        int mismatch = 0;
        for (int idx = 0; idx < static_cast<int>(word.size()); ++idx) {
            if (text[static_cast<size_t>(text_start + idx)] != word[static_cast<size_t>(idx)]) {
                mismatch += 1;
                if (mismatch > max_value) {
                    return mismatch;
                }
            }
        }
        return mismatch;
    }

    static bool interval_start_order(const Interval& lhs, const Interval& rhs) {
        if (lhs.weight != rhs.weight) return lhs.weight > rhs.weight;
        if (lhs.end != rhs.end) return lhs.end < rhs.end;
        if (lhs.start != rhs.start) return lhs.start < rhs.start;
        return lhs.length > rhs.length;
    }

    struct Plan {
        double total_weight = 0.0;
        int covered_chars = 0;
        std::vector<int> selected_indices;
        std::vector<std::tuple<int, int, int>> canonical_keys;
    };

    static bool plan_a_better(const Plan& a, const Plan& b) {
        constexpr double eps = 1e-12;
        if (a.total_weight > b.total_weight + eps) return true;
        if (b.total_weight > a.total_weight + eps) return false;
        if (a.covered_chars > b.covered_chars) return true;
        if (b.covered_chars > a.covered_chars) return false;
        if (a.canonical_keys < b.canonical_keys) return true;
        if (b.canonical_keys < a.canonical_keys) return false;
        return true;
    }

    static std::vector<Interval> select_non_overlapping(const std::vector<Interval>& intervals) {
        if (intervals.empty()) {
            return {};
        }
        std::vector<Interval> ordered = intervals;
        std::sort(ordered.begin(), ordered.end(), [](const Interval& lhs, const Interval& rhs) {
            return lhs.canonical_key() < rhs.canonical_key();
        });

        std::vector<int> ends;
        ends.reserve(ordered.size());
        for (const auto& item : ordered) {
            ends.push_back(item.end);
        }

        std::vector<int> predecessors;
        predecessors.reserve(ordered.size());
        for (const auto& item : ordered) {
            auto it = std::upper_bound(ends.begin(), ends.end(), item.start);
            predecessors.push_back(static_cast<int>(it - ends.begin()) - 1);
        }

        std::vector<Plan> dp;
        dp.reserve(ordered.size() + 1);
        dp.push_back(Plan{});

        for (int idx = 0; idx < static_cast<int>(ordered.size()); ++idx) {
            const auto& item = ordered[static_cast<size_t>(idx)];
            Plan include = dp[static_cast<size_t>(predecessors[static_cast<size_t>(idx)] + 1)];
            include.total_weight += item.weight;
            include.covered_chars += item.length;
            include.selected_indices.push_back(idx);
            include.canonical_keys.push_back(item.canonical_key());

            const Plan& exclude = dp.back();
            dp.push_back(plan_a_better(include, exclude) ? std::move(include) : exclude);
        }

        std::vector<Interval> selected;
        for (int idx : dp.back().selected_indices) {
            selected.push_back(ordered[static_cast<size_t>(idx)]);
        }
        return selected;
    }

    static int sum_lengths(const std::vector<Interval>& intervals) {
        int total = 0;
        for (const auto& item : intervals) total += item.length;
        return total;
    }

    static double sum_weights(const std::vector<Interval>& intervals) {
        double total = 0.0;
        for (const auto& item : intervals) total += item.weight;
        return total;
    }
};

#endif
