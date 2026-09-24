// Nuclear Data Adjustment Tool
// Copyright (C) 2026 Aurora Jahan
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 3 as
// published by the Free Software Foundation.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#include "input_parser.hpp"

#include <highfive/highfive.hpp>

#include <array>
#include <cstdint>
#include <fstream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {
struct Token {
  std::string value;
  std::size_t line;
};

enum class Card : std::uint8_t { Prmean, Prcov, Obsdelta, Obscov, Sens };

constexpr std::size_t card_count = 5;

struct ParsedCard {
  Card type;
  Token name_token;
  std::string filepath;
  std::string dataset;
  bool has_filepath;
  bool has_dataset;
};

constexpr auto card_index(Card card) -> std::size_t {
  return static_cast<std::size_t>(card);
}

auto card_type(std::string_view name) -> std::optional<Card> {
  if (name == "prmean") {
    return Card::Prmean;
  }
  if (name == "prcov") {
    return Card::Prcov;
  }
  if (name == "obsdelta") {
    return Card::Obsdelta;
  }
  if (name == "obscov") {
    return Card::Obscov;
  }
  if (name == "sens") {
    return Card::Sens;
  }
  return std::nullopt;
}

auto card_name(Card card) -> const char * {
  switch (card) {
  case Card::Prmean:
    return "prmean";
  case Card::Prcov:
    return "prcov";
  case Card::Obsdelta:
    return "obsdelta";
  case Card::Obscov:
    return "obscov";
  case Card::Sens:
    return "sens";
  }
  return "unknown";
}

[[noreturn]] auto parse_error(const Token &token, std::string_view message)
    -> void {
  throw std::runtime_error(std::string{"parse_input: line "} +
                           std::to_string(token.line) + ": " +
                           std::string(message));
}

[[noreturn]] auto parse_error_at_end(std::string_view message) -> void {
  throw std::runtime_error(std::string{"parse_input: end of file: "} +
                           std::string(message));
}

auto read_tokens(std::ifstream &input) -> std::vector<Token> {
  std::vector<Token> tokens;
  std::string line{};
  std::size_t line_number{0};

  while (std::getline(input, line)) {
    ++line_number;

    const auto comment_start = line.find('#');
    if (comment_start != std::string::npos) {
      line.erase(comment_start);
    }

    const auto first_non_whitespace = line.find_first_not_of(" \t\v\f\r");
    if (first_non_whitespace == std::string::npos) {
      continue;
    }

    std::istringstream line_stream(line);
    for (std::string value{}; static_cast<bool>(line_stream >> value);) {
      tokens.push_back(Token{.value = std::move(value), .line = line_number});
    }
  }

  if (input.bad()) {
    throw std::runtime_error("parse_input: failed while reading input file");
  }

  return tokens;
}

auto read_field_value(const std::vector<Token> &tokens, std::size_t &position,
                      const Token &keyword_token,
                      std::string_view card_name_value) -> std::string {
  if (position == tokens.size()) {
    parse_error_at_end(std::string{"expected a path after "} +
                       keyword_token.value + " in CARD " +
                       std::string(card_name_value));
  }
  return tokens.at(position++).value;
}

auto parse_card_fields(const std::vector<Token> &tokens, std::size_t &position,
                       ParsedCard &card) -> void {
  while (position < tokens.size() && tokens.at(position).value != "END") {
    const Token &keyword_token = tokens.at(position++);
    if (keyword_token.value == "filepath") {
      if (card.has_filepath) {
        parse_error(keyword_token,
                    std::string{"duplicate filepath keyword in CARD "} +
                        card.name_token.value);
      }
      card.has_filepath = true;
      card.filepath = read_field_value(tokens, position, keyword_token,
                                       card.name_token.value);
    } else if (keyword_token.value == "dataset") {
      if (card.has_dataset) {
        parse_error(keyword_token,
                    std::string{"duplicate dataset keyword in CARD "} +
                        card.name_token.value);
      }
      card.has_dataset = true;
      card.dataset = read_field_value(tokens, position, keyword_token,
                                      card.name_token.value);
    } else {
      parse_error(keyword_token,
                  std::string{"expected filepath or dataset keyword in CARD "} +
                      card.name_token.value);
    }
  }

  if (position == tokens.size()) {
    parse_error_at_end(std::string{"expected END for CARD "} +
                       card.name_token.value);
  }
  ++position;

  if (!card.has_filepath) {
    parse_error(card.name_token, std::string{"CARD "} + card.name_token.value +
                                     " is missing the filepath keyword");
  }
  if (!card.has_dataset) {
    parse_error(card.name_token, std::string{"CARD "} + card.name_token.value +
                                     " is missing the dataset keyword");
  }
}

auto parse_card(const std::vector<Token> &tokens, std::size_t &position)
    -> ParsedCard {
  const Token &card_token = tokens.at(position);
  if (card_token.value != "CARD") {
    parse_error(card_token, "expected CARD");
  }
  ++position;

  if (position == tokens.size()) {
    parse_error_at_end("expected card name after CARD");
  }
  const Token &name_token = tokens.at(position++);
  const auto type = card_type(name_token.value);
  if (!type) {
    parse_error(name_token,
                std::string{"unknown card '"} + name_token.value + "'");
  }

  ParsedCard card{.type = *type,
                  .name_token = name_token,
                  .filepath = {},
                  .dataset = {},
                  .has_filepath = false,
                  .has_dataset = false};
  parse_card_fields(tokens, position, card);
  return card;
}

auto store_card(InputPaths &paths, ParsedCard card) -> void {
  switch (card.type) {
  case Card::Prmean:
    paths.prmean_filepath = std::move(card.filepath);
    paths.prmean_dataset = std::move(card.dataset);
    break;
  case Card::Prcov:
    paths.prcov_filepath = std::move(card.filepath);
    paths.prcov_dataset = std::move(card.dataset);
    break;
  case Card::Obsdelta:
    paths.obsdelta_filepath = std::move(card.filepath);
    paths.obsdelta_dataset = std::move(card.dataset);
    break;
  case Card::Obscov:
    paths.obscov_filepath = std::move(card.filepath);
    paths.obscov_dataset = std::move(card.dataset);
    break;
  case Card::Sens:
    paths.sens_filepath = std::move(card.filepath);
    paths.sens_dataset = std::move(card.dataset);
    break;
  }
}
} // namespace

auto parse_input(const std::filesystem::path &input_file) -> InputPaths {
  std::ifstream input(input_file);
  if (!input.is_open()) {
    throw std::runtime_error(
        std::string{"parse_input: unable to open input file '"} +
        input_file.string() + "'");
  }

  const std::vector<Token> tokens = read_tokens(input);
  InputPaths paths{};
  std::array<bool, card_count> seen{};
  std::size_t position{0};

  while (position < tokens.size()) {
    ParsedCard card = parse_card(tokens, position);
    const std::size_t index = card_index(card.type);
    if (seen.at(index)) {
      parse_error(card.name_token,
                  std::string{"duplicate CARD "} + card.name_token.value);
    }
    seen.at(index) = true;
    store_card(paths, std::move(card));
  }

  for (std::size_t index{0}; index < seen.size(); ++index) {
    if (!seen.at(index)) {
      const auto card = static_cast<Card>(index);
      throw std::runtime_error(std::string{"parse_input: missing CARD "} +
                               card_name(card));
    }
  }

  return paths;
}

auto read_dataset(const std::filesystem::path &file_path,
                  const std::string &dataset_path) -> Dataset {
  HighFive::File file(file_path.string(), HighFive::File::ReadOnly);
  const HighFive::DataSet dataset = file.getDataSet(dataset_path);

  if (dataset.getDataType() != HighFive::AtomicType<double>()) {
    throw std::runtime_error(std::string{"read_dataset: dataset '"} +
                             dataset_path + "' in file '" + file_path.string() +
                             "' must have float64/double datatype");
  }

  const std::vector<std::size_t> dimensions = dataset.getDimensions();
  if (dimensions.empty()) {
    throw std::runtime_error(std::string{"read_dataset: dataset '"} +
                             dataset_path +
                             "' is scalar; expected a vector or matrix");
  }

  if (dimensions.size() > 2) {
    throw std::runtime_error(
        std::string{"read_dataset: dataset '"} + dataset_path +
        "' has more than two dimensions; only vectors and matrices "
        "are supported");
  }

  const std::size_t element_count = dataset.getElementCount();
  const auto max_eigen_index =
      static_cast<std::size_t>(std::numeric_limits<Eigen::Index>::max());
  if (element_count > max_eigen_index || dimensions.front() > max_eigen_index) {
    throw std::runtime_error(std::string{"read_dataset: dataset '"} +
                             dataset_path + "' is too large for Eigen");
  }

  std::vector<double> values(element_count);
  if (element_count > 0) {
    dataset.read_raw(values.data(), HighFive::AtomicType<double>());
  }

  if (dimensions.size() == 1) {
    Eigen::VectorXd result(static_cast<Eigen::Index>(element_count));
    for (std::size_t index{0}; index < element_count; ++index) {
      result(static_cast<Eigen::Index>(index)) = values.at(index);
    }
    return result;
  }

  const std::size_t rows = dimensions.front();
  if (rows == 0 || element_count % rows != 0) {
    throw std::runtime_error(std::string{"read_dataset: dataset '"} +
                             dataset_path + "' has invalid matrix dimensions");
  }
  const std::size_t columns = element_count / rows;
  if (columns > max_eigen_index) {
    throw std::runtime_error(std::string{"read_dataset: dataset '"} +
                             dataset_path + "' is too large for Eigen");
  }

  Eigen::MatrixXd result(static_cast<Eigen::Index>(rows),
                         static_cast<Eigen::Index>(columns));
  for (std::size_t row{0}; row < rows; ++row) {
    for (std::size_t column{0}; column < columns; ++column) {
      result(static_cast<Eigen::Index>(row),
             static_cast<Eigen::Index>(column)) =
          values.at((row * columns) + column);
    }
  }
  return result;
}
