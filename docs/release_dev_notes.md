# Dev notes to do after each release:

1) Make sure binaries are generated in release artifacts
2) Download and install binaries
3) Check that the app opens up
4) Check that the app shows the latest version in the menu
5) Check that all files from test/golden_sample_corpus can be opened with the application from the explorer app (or using terminal on MacOS/Linux)
6) Convert all game files on all 3 platforms, check diffs. Expect no changes expect what the new release brought

Whenever something went wrong during tests: 
1) create a hotfix branch
2) add failing tests for issues found (if possible)
3) fix ONLY found issues, do not make other changes
3) merge branch into the main, release the new version