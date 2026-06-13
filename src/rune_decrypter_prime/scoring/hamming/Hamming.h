#ifndef HAMMING_H
#define HAMMING_H

#include <map>
#include <iostream>
#include <limits>
#include "Flat2DArray.h"
#include "Types.h"

class Hamming {
public:
    Hamming() = default;

    int get_min_hamming_distance(const CommonTypes::IntVec& runes_index, const CommonTypes::IntVec2D& word_indices) const {
        int word_length = word_indices[0][1];
        const auto& dict_words = __all_words_index.at(word_length);
        int min_hd = std::numeric_limits<int>::max();

        for (size_t row = 0; row < dict_words.row_count(); ++row) {
            int hd = 0;
            for (size_t i = 0; i < word_indices.size(); ++i) {
                if (dict_words(row, word_indices[i][0]) != runes_index[i]) {
                    ++hd;
                }
            }
            if (hd == 0) {
                return 0;
            }
            if (hd < min_hd) {
                min_hd = hd;
            }
        }
        return min_hd;
    }

    int find_min_HD(const CommonTypes::IntVec& runes_index, const CommonTypes::IntVec2D& wli_data, int max_hd) const {
        auto word_data = create_word_data(runes_index, wli_data);
        const auto& runesword = word_data.first;
        const auto& wliwords = word_data.second;
        int total_hd = 0;

        for (size_t i = 0; i < runesword.size(); ++i) {
            total_hd += get_min_hamming_distance(runesword[i], wliwords[i]);
            if (total_hd > max_hd) {
                break;
            }
        }
        return total_hd;
    }

    int get_min_hamming_distance_verbose(const CommonTypes::IntVec& runes_index, const CommonTypes::IntVec2D& word_indices) const {
        std::cout << "get_min_hamming_distance_verbose" << std::endl;
        int word_length = word_indices[0][1];
        std::cout << "word_length: " << word_length << std::endl;

        const auto& dict_words = __all_words_index.at(word_length);
        int min_hd = std::numeric_limits<int>::max();
        std::cout << "total_words = " << dict_words.row_count() << std::endl;

        for (size_t row = 0; row < dict_words.row_count(); ++row) {
            int hd = 0;
            for (size_t i = 0; i < word_indices.size(); ++i) {
                if (dict_words(row, word_indices[i][0]) != runes_index[i]) {
                    ++hd;
                }
            }
            if (hd == 0) {
                std::cout << "Found exact match at row: " << row << std::endl;
                return 0;
            }
            if (hd < min_hd) {
                min_hd = hd;
            }
        }
        std::cout << "Searched all words, min_hd: " << min_hd << std::endl;
        return min_hd;
    }

    int find_min_HD_verbose(const CommonTypes::IntVec& runes_index, const CommonTypes::IntVec2D& wli_data, int max_hd) const {
        std::cout << "find_min_HD_verbose" << std::endl;
        auto word_data = create_word_data(runes_index, wli_data);
        const auto& runesword = word_data.first;
        const auto& wliwords = word_data.second;
        int total_hd = 0;

        for (size_t i = 0; i < runesword.size(); ++i) {
            std::cout << "runes:" << std::endl;
            print1DVector(runesword[i]);
            std::cout << "wli:" << std::endl;
            print2DVector(wliwords[i]);

            total_hd += get_min_hamming_distance_verbose(runesword[i], wliwords[i]);
            if (total_hd > max_hd) {
                std::cout << "word:" << i << " total_hd: " << total_hd << " > max_hd " << max_hd << ", FAIL" << std::endl;
                break;
            } else {
                std::cout << "word:" << i << " total_hd: " << total_hd << std::endl;
            }
        }
        return total_hd;
    }

    std::pair<CommonTypes::IntVec2D, CommonTypes::IntVec3D> create_word_data(const CommonTypes::IntVec& runes_index, const CommonTypes::IntVec2D& wli_data) const {
        CommonTypes::IntVec2D return_runes;
        CommonTypes::IntVec3D return_wli;
        CommonTypes::IntVec nextrunes;
        CommonTypes::IntVec2D nextwli;

        for (size_t i = 0; i < runes_index.size(); ++i) {
            int rune = runes_index[i];
            const CommonTypes::IntVec& wli = wli_data[i];

            if (wli[0] == 0) {
                if (!nextrunes.empty()) {
                    return_runes.push_back(nextrunes);
                    return_wli.push_back(nextwli);
                }
                nextwli = {wli};
                nextrunes = {rune};
            } else {
                nextwli.push_back(wli);
                nextrunes.push_back(rune);
            }
        }

        if (!nextrunes.empty()) {
            return_runes.push_back(nextrunes);
            return_wli.push_back(nextwli);
        }

        return {return_runes, return_wli};
    }

    size_t update_all_words_index(int wordlength, const CommonTypes::IntVec2D& input_list) {
        __all_words_index[wordlength] = Flat2DArray(input_list);
        return __all_words_index.at(wordlength).size();
    }

    void status() const {
        std::cout << "Hamming words " << std::endl;
        for (const auto& pair : __all_words_index) {
            std::cout << "Key: " << pair.first << ", Value.rows: " << pair.second.row_count()
                      << ", Value.cols: " << pair.second.col_count() << std::endl;
        }
    }

private:
    std::map<int, Flat2DArray> __all_words_index;

    void print1DVector(const CommonTypes::IntVec& vec) const {
        std::cout << "{";
        for (size_t i = 0; i < vec.size(); ++i) {
            std::cout << vec[i];
            if (i < vec.size() - 1) {
                std::cout << ", ";
            }
        }
        std::cout << "}" << std::endl;
    }

    void print2DVector(const CommonTypes::IntVec2D& vec) const {
        std::cout << "{" << std::endl;
        for (size_t i = 0; i < vec.size(); ++i) {
            std::cout << "    {";
            for (size_t j = 0; j < vec[i].size(); ++j) {
                std::cout << vec[i][j];
                if (j < vec[i].size() - 1) {
                    std::cout << ", ";
                }
            }
            std::cout << "}";
            if (i < vec.size() - 1) {
                std::cout << ",";
            }
            std::cout << std::endl;
        }
        std::cout << "}" << std::endl;
    }
};

#endif // HAMMING_H
