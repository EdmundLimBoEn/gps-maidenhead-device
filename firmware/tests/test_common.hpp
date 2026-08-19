// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <exception>
#include <functional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace pocket_locator::test {

using TestFunction = void (*)();

struct TestCase {
    const char* name;
    TestFunction function;
};

inline std::vector<TestCase>& registry() {
    static std::vector<TestCase> tests;
    return tests;
}

class Register {
public:
    Register(const char* name, TestFunction function) { registry().push_back({name, function}); }
};

template <typename Left, typename Right>
void require_equal(const Left& left, const Right& right, const char* left_text, const char* right_text, const char* file, int line) {
    if (!(left == right)) {
        std::ostringstream message;
        message << file << ':' << line << ": expected " << left_text << " == " << right_text;
        throw std::runtime_error(message.str());
    }
}

inline void require_true(bool condition, const char* expression, const char* file, int line) {
    if (!condition) {
        throw std::runtime_error(std::string(file) + ':' + std::to_string(line) + ": expected " + expression);
    }
}

}  // namespace pocket_locator::test

#define TEST(name) \
    static void name(); \
    static ::pocket_locator::test::Register name##_registration(#name, &name); \
    static void name()

#define REQUIRE(expression) ::pocket_locator::test::require_true((expression), #expression, __FILE__, __LINE__)
#define REQUIRE_EQ(left, right) ::pocket_locator::test::require_equal((left), (right), #left, #right, __FILE__, __LINE__)
