#ifndef FLAT2DARRAY_H
#define FLAT2DARRAY_H

#include <vector>
#include <stdexcept>
#include <algorithm>

class Flat2DArray {
public:
    // Default constructor
    Flat2DArray() noexcept : rows(0), cols(0) {}

    // Constructor that takes a 2D vector of integers
    Flat2DArray(const std::vector<std::vector<int>>& vec)
        : rows(vec.size()), cols(rows ? vec[0].size() : 0), data(rows * cols) {
        if (rows > 0) {
            for (const auto& row : vec) {
                if (row.size() != cols) {
                    throw std::invalid_argument("All rows must have the same number of columns");
                }
            }
            for (size_t i = 0; i < rows; ++i) {
                std::copy(vec[i].begin(), vec[i].end(), data.begin() + i * cols);
            }
        }
    }

    // Return the number of rows
    size_t row_count() const noexcept { return rows; }

    // Return the number of columns
    size_t col_count() const noexcept { return cols; }

    // Return the total size of the flattened array
    size_t size() const noexcept { return data.size(); }

    // Accessor operator
    int& operator()(size_t row, size_t col) {
        return data[check_index(row, col)];
    }

    const int& operator()(size_t row, size_t col) const {
        return data[check_index(row, col)];
    }

    // Copy constructor
    Flat2DArray(const Flat2DArray& other) = default;

    // Copy assignment operator
    Flat2DArray& operator=(const Flat2DArray& other) = default;

    // Move constructor
    Flat2DArray(Flat2DArray&& other) noexcept
        : rows(other.rows), cols(other.cols), data(std::move(other.data)) {
        other.rows = 0;
        other.cols = 0;
    }

private:
    size_t rows, cols;
    std::vector<int> data;

    size_t check_index(size_t row, size_t col) const {
        if (row >= rows || col >= cols) {
            throw std::out_of_range("Index out of range");
        }
        return row * cols + col;
    }
};

#endif // FLAT2DARRAY_H
