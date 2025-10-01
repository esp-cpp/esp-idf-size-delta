# ESP IDF Size-Delta Action

Github action for computing FLASH and D/IRAM deltas between versions for
commenting on PRs and releases.

This repository provides a reusable action for computing changes between builds
(e.g. for PRs and releases) of your flash and D/IRAM usage for esp-idf projects.

It can calculate and post size delta tables on both `pull requests` as well as `releases`:

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [ESP IDF Size-Delta Action](#esp-idf-size-delta-action)
  - [About](#about)
    - [Example Output on PR](#example-output-on-pr)
    - [Example Output on Release](#example-output-on-release)
  - [Using This Action](#using-this-action)
    - [For Pull Requests](#for-pull-requests)
    - [For Releases](#for-releases)
    - [Inputs ](#inputs)

<!-- markdown-toc end -->

## About

The output of this action is a comment on the PR or release showing the changes
in flash and D/IRAM usage between the current build and the target branch (for
PRs) or previous release (for releases).

It runs `idf_size.py` to compute the sizes, outputting the reults into a simple
`.json` file, before running a Python script to compute the deltas and format
them into a markdown table.

The primary use case for this action is to be run on pull requests and releases,
so that the size changes will be automatically computed and added to the PR or
release notes for ease of use.

For an example repository which uses this action, see
[esp-cpp/template](https://github.com/esp-cpp/template):
- [esp-cpp/template build.yml](https://github.com/esp-cpp/template/blob/main/.github/workflows/build.yml) - uses this action on pull requests 
- [esp-cpp/template package_main.yml](https://github.com/esp-cpp/template/blob/main/.github/workflows/package_main.yml) - uses this action on releases

### Example Output on PR

<img width="1023" height="542" alt="CleanShot 2025-10-01 at 09 29 57" src="https://github.com/user-attachments/assets/8f39f662-c801-4e73-bed0-a09698b2f39f" />

### Example Output on Release

<img width="1317" height="608" alt="CleanShot 2025-10-01 at 10 00 06" src="https://github.com/user-attachments/assets/a2e63fa2-75d1-40e6-a733-54bfae51c2a1" />

## Using This Action

You can use this action in your GitHub workflows. Below are example workflows
for pull requests and releases.

### For Pull Requests

This action can be used to compute the flash and D/IRAM size changes for pull
requests. It will compare the current branch (the PR branch) against the target
branch (e.g. `main` or `develop`).

You will need to ensure that the build artifacts are available in the `build`
directory (or whatever directory you specify in the `build-path` input). This
typically means you will need to run the build step before this action.

Here is an example workflow for pull requests:

```yaml
name: Build and Compute Size Delta (PR)
on: [pull_request]

jobs:
  build:
    name: Build the project
    permissions:
      issues: write # to post PR comments
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v5

    - name: Build the code
      uses: espressif/esp-idf-ci-action@v1
      with:
        esp_idf_version: v5.5
        target: esp32s3
        path: '.'

    - name: Determine Size Delta
      uses: esp-cpp/esp-idf-size-delta@v1
      with:
        app_name: "My ESP-IDF App"
        app_path: "."
        idf_target: esp32s3
        idf_version: v5.5
        idf_component_manager: "1" # enable component manager
        base_ref: ${{ github.event.pull_request.base.sha }}
        flash_total_override: 1500000 # optional, number of bytes for app partition in flash for percentage calculation
```

### For Size-Only Reports (No Base Comparison)

You can also use this action to generate a size report without comparing against a base reference. This is useful for standalone builds or when you only want to see the current size state without deltas.

Simply omit the `base_ref` input or set it to an empty string:

```yaml
name: Build and Show Size Report
on: [push]

jobs:
  build:
    name: Build and report size
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v5

    - name: Build the code
      uses: espressif/esp-idf-ci-action@v1
      with:
        esp_idf_version: v5.5
        target: esp32s3
        path: '.'

    - name: Show Size Report
      uses: esp-cpp/esp-idf-size-delta@v1
      with:
        app_name: "My ESP-IDF App"
        app_path: "."
        idf_target: esp32s3
        idf_version: v5.5
        # base_ref is omitted - will show only current size without delta comparison
        post_comment: 'false' # typically for push events, not PRs
```

This will generate a simpler table showing only the current size metrics without base/delta columns.

### For Releases

This action can also be used to compute the flash and D/IRAM size changes for
releases. It will compare the current build against the latest release on the
target branch (e.g. `main` or `develop`).

You will need to ensure that the build artifacts are available in the `build`
directory (or whatever directory you specify in the `build-path` input). This
typically means you will need to run the build step before this action.

```yaml
name: Build and Compute Size Delta (Release)
on:
  release:
    types: [published]
jobs:
  build:
    name: Compute Size Delta for Release
    runs-on: ubuntu-latest
    permissions:
      contents: write # to allow updating release notes
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0 # to fetch all tags

    - name: Determine base ref
      id: base
      shell: bash
      run: |
        set -euo pipefail
        # use the previous tag chronologically
        prev=$(git tag --sort=-creatordate | sed -n '2p')
        if [ -z "$prev" ]; then prev=$(git tag --sort=-v:refname | sed -n '2p'); fi
        echo "ref=$prev" >> "$GITHUB_OUTPUT"

    - name: Determine Size Delta
      uses: esp-cpp/esp-idf-size-delta@v1
      with:
        app_name: "My ESP-IDF App"
        app_path: "."
        head_name: "${{ github.event.release.tag_name }}"
        base_name: "${{ steps.base.outputs.ref }}"
        idf_target: esp32s3
        idf_version: v5.5
        idf_component_manager: "1" # enable component manager
        base_ref: ${{ steps.base.outputs.ref }}
        flash_total_override: 1500000 # optional, number of bytes for app partition in flash for percentage calculation
        post_comment: 'false' # set to false since this is not a PR with comments
```

### Inputs 

```yaml
inputs:
  app_name:
    description: 'Name of the ESP-IDF app (for reporting)'
    required: true
  app_path:
    description: 'Relative path to the ESP-IDF app (contains CMakeLists.txt)'
    required: true
  idf_version:
    description: 'ESP-IDF version to setup'
    required: false
    default: 'v5.5'
  idf_target:
    description: 'ESP-IDF target (defaults to IDF_TARGET env var or "esp32")'
    required: false
  idf_component_manager:
    description: 'Set IDF_COMPONENT_MANAGER ("0" to disable)'
    required: false
    default: '0'
  head_name:
    description: 'Name of the head app (for reporting, defaults to "PR")'
    required: false
    default: 'PR'
  base_name:
    description: 'Name of the base app (for reporting, defaults to "Base")'
    required: false
    default: 'Base'
  base_ref:
    description: 'Git ref/sha to use as base for delta (optional - if omitted, shows only current size without comparison)'
    required: false
  post_comment:
    description: 'Whether to post a PR comment (true/false)'
    required: false
    default: 'true'
  flash_total_override:
    description: 'Override total FLASH bytes for percentage (optional)'
    required: false
    default: ''
  github_token:
    description: 'GitHub token'
    required: false
    default: ${{ github.token }}
  checkout_token:
    description: 'Token to use for checkout actions (defaults to GITHUB_TOKEN)'
    required: false
    default: ''

outputs:
  markdown:
    description: 'Markdown report for this app'
    value: ${{ steps.mkdown.outputs.markdown }}
```
