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

#include <exception>
#include <iostream>
#include <span>

#include "input_parser.hpp"

auto main(int argc, char *argv[]) -> int {
  const std::span<char *const> arguments(argv, static_cast<std::size_t>(argc));
  if (arguments.size() != 2) {
    const char *executable = arguments.empty() ? "nda" : arguments.front();
    std::cerr << "Usage: " << executable << " <input-file>\n";
    return 2;
  }

  try {
    const auto [prmean_filepath, prmean_dataset, prcov_filepath, prcov_dataset,
                obsdelta_filepath, obsdelta_dataset, obscov_filepath,
                obscov_dataset, sens_filepath, sens_dataset] =
        parse_input(arguments.back());

    std::cout << "prmean.filepath: " << prmean_filepath << '\n'
              << "prmean.dataset: " << prmean_dataset << '\n'
              << "prcov.filepath: " << prcov_filepath << '\n'
              << "prcov.dataset: " << prcov_dataset << '\n'
              << "obsdelta.filepath: " << obsdelta_filepath << '\n'
              << "obsdelta.dataset: " << obsdelta_dataset << '\n'
              << "obscov.filepath: " << obscov_filepath << '\n'
              << "obscov.dataset: " << obscov_dataset << '\n'
              << "sens.filepath: " << sens_filepath << '\n'
              << "sens.dataset: " << sens_dataset << '\n';
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }

  return 0;
}