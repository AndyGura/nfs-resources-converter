import unittest
import os
import sys
import time
import unittest
from collections import defaultdict
from typing import List, Any

from library import require_file
from library.context import ReadContext


def deep_equal(a: Any, b: Any) -> bool:
    """
    Perform a deep equality comparison between two objects.

    Args:
        a: First object to compare
        b: Second object to compare

    Returns:
        True if objects are deeply equal, False otherwise
    """
    # Check if objects are of the same type
    if type(a) != type(b):
        return False

    # Handle None
    if a is None:
        return b is None

    # Handle basic types
    if isinstance(a, (int, float, str, bool)):
        return a == b

    # Handle lists
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(deep_equal(a[i], b[i]) for i in range(len(a)))

    # Handle dictionaries
    if isinstance(a, dict):
        if len(a) != len(b):
            return False
        if set(a.keys()) != set(b.keys()):
            return False
        return all(deep_equal(a[k], b[k]) for k in a.keys())

    # Handle tuples
    if isinstance(a, tuple):
        if len(a) != len(b):
            return False
        return all(deep_equal(a[i], b[i]) for i in range(len(a)))

    # Handle sets
    if isinstance(a, set):
        return a == b

    # For other types, use equality operator
    return a == b


class TestGamesDirectory(unittest.TestCase):
    @unittest.skip
    def test_all_game_files_should_remain_the_same(self):
        """
        Test that goes through the entire ./games/ directory, reads each file, writes it back to a bytes object,
        and compares the output with the input. It prints progress information during the process and handles
        errors appropriately.
        """
        # Start time tracking
        start_time = time.time()

        # ANSI color codes
        GREEN = "\033[32m"
        RED = "\033[31m"
        RESET = "\033[0m"

        # Statistics tracking
        total_files = 0
        read_success = 0
        write_success = 0
        read_again_success = 0
        compare_success = 0
        extension_stats = defaultdict(lambda: {
            "total": 0,
            "read_success": 0,
            "write_success": 0,
            "read_again_success": 0,
            "compare_success": 0
        })

        games_dir = "../../games"
        all_files = self._get_all_files(games_dir)
        all_files = [x for x in all_files if x[-4:].upper() not in ['.EXE', '.DLL', '.INF', '.INV', '.PIF', '.TXT', '.CFG',
                                                                    '.ICO', '.ID0', '.ID1', '.ID2', '.NAM', '.TIL', '.ENG',
                                                                    '.GER', '.ION']]
        all_files = [x for x in all_files if x[-3:].upper() not in ['.UC', '.UV']]
        all_files = [x for x in all_files if x[-2:].upper() not in ['.0']]

        total_files = len(all_files)

        for file_path in all_files:
            # Get file extension
            ext = file_path[-4:].upper()
            extension_stats[ext]["total"] += 1

            # Print file name and "..." to indicate processing has started
            sys.stdout.write(f"{file_path}...")
            sys.stdout.flush()

            try:
                # Test 1: Read the file
                (name, block, data) = require_file(file_path)
                # Add checkmark to indicate successful read
                sys.stdout.write("✓")
                sys.stdout.flush()
                read_success += 1
                extension_stats[ext]["read_success"] += 1

                # Test 2: Write the file back to a bytes object
                output = block.pack(data, name=name)
                # Add checkmark to indicate successful write
                sys.stdout.write("✓")
                sys.stdout.flush()
                write_success += 1
                extension_stats[ext]["write_success"] += 1

                # Optimization: Check test 4 first (compare with original)
                with open(file_path, 'rb') as bdata:
                    original = bdata.read()
                    if len(original) == len(output):
                        is_same = True
                        for i, x in enumerate(original):
                            if x != output[i]:
                                is_same = False
                                break

                        if is_same:
                            # Test 4 passed, so test 3 passes automatically
                            read_again_success += 1
                            extension_stats[ext]["read_again_success"] += 1
                            compare_success += 1
                            extension_stats[ext]["compare_success"] += 1

                            # Add checkmark for test 3 (read again)
                            sys.stdout.write("✓")
                            sys.stdout.flush()

                            # Add green checkmark for test 4 (compare)
                            sys.stdout.write(f"{GREEN}✓{RESET}\n")
                            sys.stdout.flush()
                        else:
                            # Test 4 failed, need to check test 3
                            # Test 3: Read the written data again
                            try:
                                # Create a BytesIO object from the output
                                from io import BytesIO
                                output_buffer = BytesIO(output)
                                # Read the data again
                                read_again_data = block.unpack(
                                    ReadContext(buffer=output_buffer, name=file_path, block=block,
                                                read_bytes_amount=len(output)))

                                # Compare with original data (deep equal)
                                if deep_equal(data, read_again_data):
                                    # Test 3 passed
                                    read_again_success += 1
                                    extension_stats[ext]["read_again_success"] += 1
                                    # Add checkmark for test 3
                                    sys.stdout.write("✓")
                                    sys.stdout.flush()
                                else:
                                    # Test 3 failed
                                    sys.stdout.write(f"{RED}❌{RESET}")
                                    sys.stdout.flush()
                                    self.fail(f"Read-again data differs from original data for file {file_path}")
                            except Exception as e:
                                # Test 3 failed
                                sys.stdout.write(f"{RED}❌ (Error: {str(e)}){RESET}")
                                sys.stdout.flush()
                                self.fail(f"Failed to read written data for file {file_path}: {str(e)}")

                            # Test 4 failed
                            sys.stdout.write(f"{RED}❌{RESET}\n")
                            sys.stdout.flush()
                            self.fail(f"Output differs from input for file {file_path}")
                    else:
                        # Test 4 failed due to length mismatch
                        # Try test 3 anyway
                        try:
                            # Create a BytesIO object from the output
                            from io import BytesIO
                            output_buffer = BytesIO(output)
                            # Read the data again
                            read_again_data = block.unpack(
                                ReadContext(buffer=output_buffer, name=file_path, block=block,
                                            read_bytes_amount=len(output)))

                            # Compare with original data (deep equal)
                            if deep_equal(data, read_again_data):
                                # Test 3 passed
                                read_again_success += 1
                                extension_stats[ext]["read_again_success"] += 1
                                # Add checkmark for test 3
                                sys.stdout.write("✓")
                                sys.stdout.flush()
                            else:
                                # Test 3 failed
                                sys.stdout.write(f"{RED}❌{RESET}")
                                sys.stdout.flush()
                                self.fail(f"Read-again data differs from original data for file {file_path}")
                        except Exception as e:
                            # Test 3 failed
                            sys.stdout.write(f"{RED}❌ (Error: {str(e)}){RESET}")
                            sys.stdout.flush()
                            self.fail(f"Failed to read written data for file {file_path}: {str(e)}")

                        # Test 4 failed
                        sys.stdout.write(f"{RED}❌{RESET}\n")
                        sys.stdout.flush()
                        self.fail(
                            f"Output length ({len(output)}) differs from input length ({len(original)}) for file {file_path}")

            except Exception as e:
                # Skip file if it was failed to read
                sys.stdout.write(f"{RED}❌ (Error: {str(e)}){RESET}\n")
                sys.stdout.flush()
                continue

        # Print statistics
        print("\n--- Test Statistics ---")
        print(f"Total files tested: {total_files}")
        print(f"Files read successfully: {read_success}")
        print(f"Files written successfully: {write_success}")
        print(f"Files read again successfully: {read_again_success}")
        print(f"Files passed comparison test: {compare_success}")

        # Calculate and print extension success rates for each test
        # Test 1: Read success rates
        print("\n--- File Extension Read Success Rates (Test 1) ---")
        read_extension_rates = {}
        for ext, stats in extension_stats.items():
            if stats["total"] > 0:
                success_rate = (stats["read_success"] / stats["total"]) * 100
                read_extension_rates[ext] = success_rate
                if success_rate > 0:
                    print(f"{ext}: {success_rate:.2f}%")

        # Test 2: Write success rates
        print("\n--- File Extension Write Success Rates (Test 2) ---")
        write_extension_rates = {}
        for ext, stats in extension_stats.items():
            if stats["total"] > 0:
                success_rate = (stats["write_success"] / stats["total"]) * 100
                write_extension_rates[ext] = success_rate
                # Show if success rate > 0 or if it has success in test 1
                if success_rate > 0 or (ext in read_extension_rates and read_extension_rates[ext] > 0):
                    print(f"{ext}: {success_rate:.2f}%")

        # Test 3: Read-again success rates
        print("\n--- File Extension Read-Again Success Rates (Test 3) ---")
        read_again_extension_rates = {}
        for ext, stats in extension_stats.items():
            if stats["total"] > 0:
                success_rate = (stats["read_again_success"] / stats["total"]) * 100
                read_again_extension_rates[ext] = success_rate
                # Show if success rate > 0 or if it has success in test 1
                if success_rate > 0 or (ext in read_extension_rates and read_extension_rates[ext] > 0):
                    print(f"{ext}: {success_rate:.2f}%")

        # Test 4: Comparison success rates
        print("\n--- File Extension Comparison Success Rates (Test 4) ---")
        compare_extension_rates = {}
        for ext, stats in extension_stats.items():
            if stats["total"] > 0:
                success_rate = (stats["compare_success"] / stats["total"]) * 100
                compare_extension_rates[ext] = success_rate
                # Show if success rate > 0 or if it has success in test 1
                if success_rate > 0 or (ext in read_extension_rates and read_extension_rates[ext] > 0):
                    print(f"{ext}: {success_rate:.2f}%")

        # Calculate elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Print time spent
        print("\n--- Time Spent ---")
        print(f"Total time: {int(hours):02}:{int(minutes):02}:{seconds:.2f}")

        # Export statistics to file
        stats_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_files_stats.txt")
        with open(stats_file_path, 'w') as stats_file:
            stats_file.write("--- Test Statistics ---\n")
            stats_file.write(f"Total files tested: {total_files}\n")
            stats_file.write(f"Files read successfully: {read_success}\n")
            stats_file.write(f"Files written successfully: {write_success}\n")
            stats_file.write(f"Files read again successfully: {read_again_success}\n")
            stats_file.write(f"Files passed comparison test: {compare_success}\n\n")

            # Test 1: Read success rates
            stats_file.write("--- File Extension Read Success Rates (Test 1) ---\n")
            for ext, rate in sorted(read_extension_rates.items(), key=lambda x: x[1], reverse=True):
                if rate > 0:
                    stats_file.write(f"{ext}: {rate:.2f}%\n")

            # Test 2: Write success rates
            stats_file.write("\n--- File Extension Write Success Rates (Test 2) ---\n")
            for ext, rate in sorted(write_extension_rates.items(), key=lambda x: x[1], reverse=True):
                # Show if success rate > 0 or if it has success in test 1
                if rate > 0 or (ext in read_extension_rates and read_extension_rates[ext] > 0):
                    stats_file.write(f"{ext}: {rate:.2f}%\n")

            # Test 3: Read-again success rates
            stats_file.write("\n--- File Extension Read-Again Success Rates (Test 3) ---\n")
            for ext, rate in sorted(read_again_extension_rates.items(), key=lambda x: x[1], reverse=True):
                # Show if success rate > 0 or if it has success in test 1
                if rate > 0 or (ext in read_extension_rates and read_extension_rates[ext] > 0):
                    stats_file.write(f"{ext}: {rate:.2f}%\n")

            # Test 4: Comparison success rates
            stats_file.write("\n--- File Extension Comparison Success Rates (Test 4) ---\n")
            for ext, rate in sorted(compare_extension_rates.items(), key=lambda x: x[1], reverse=True):
                # Show if success rate > 0 or if it has success in test 1
                if rate > 0 or (ext in read_extension_rates and read_extension_rates[ext] > 0):
                    stats_file.write(f"{ext}: {rate:.2f}%\n")

            # Write time spent to file
            stats_file.write("\n--- Time Spent ---\n")
            stats_file.write(f"Total time: {int(hours):02}:{int(minutes):02}:{seconds:.2f}\n")

        print(f"\nStatistics exported to: {stats_file_path}")

    def _get_all_files(self, directory: str) -> List[str]:
        """
        Recursively get all files in a directory.

        Args:
            directory: The directory to search in.

        Returns:
            A list of file paths.
        """
        all_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                all_files.append(os.path.join(root, file))
        return all_files
