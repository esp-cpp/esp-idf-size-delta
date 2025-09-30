# ESP IDF Size-Delta Action

Github action for computing FLASH and D/IRAM deltas between versions for
commenting on PRs and releases.

This repository provides a reusable action for computing changes between builds
(e.g. for PRs and releases) of your flash and D/IRAM usage for esp-idf projects.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [ESP IDF Size-Delta Action](#esp-idf-size-delta-action)
  - [About](#about)
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

```yaml
  size-delta:
    name: Compute the flash and D/IRAM size delta for esp-idf projects
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: esp-cpp/esp-idf-size-delta-action@v1.0.0
        with:
          build-path: 'build'
          target-branch: 'main'
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Using This Action

### For Pull Requests

This action can be used to compute the flash and D/IRAM size changes for pull
requests. It will compare the current branch (the PR branch) against the target
branch (e.g. `main` or `develop`).

You will need to ensure that the build artifacts are available in the `build`
directory (or whatever directory you specify in the `build-path` input). This
typically means you will need to run the build step before this action.

Here is an example workflow for pull requests:

```yaml
name: CI
on:
  pull_request:
    branches:
      - main
      - develop
jobs:
  build:
    name: Build the project
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build the code
        uses: espressif/esp-idf-ci-action@v1
          with:
          esp_idf_version: v5.4.1
          target: esp32s3
          path: '.'
          command: idf.py build
      - name: Compute Size Delta
        uses: esp-cpp/esp-idf-size-delta-action@v1.0.0
        with:
          build-path: 'build'
          target-branch: 'main'
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### For Releases

This action can also be used to compute the flash and D/IRAM size changes for
releases. It will compare the current build against the latest release on the
target branch (e.g. `main` or `develop`).

You will need to ensure that the build artifacts are available in the `build`
directory (or whatever directory you specify in the `build-path` input). This
typically means you will need to run the build step before this action.

```yaml
name: Release
on:
  release:
    types: [published]
jobs:
  build:
    name: Build the project
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build the code
        uses: espressif/esp-idf-ci-action@v1
          with:
          esp_idf_version: v5.4.1
          target: esp32s3
      - name: Compute Size Delta
        uses: esp-cpp/esp-idf-size-delta-action@v1.0.0
        with:
          build-path: 'build'
          target-branch: 'main'
          github-token: ${{ secrets.GITHUB_TOKEN }}
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
  idf_component_manager:
    description: 'Set IDF_COMPONENT_MANAGER ("0" to disable)'
    required: false
    default: '0'
  base_ref:
    description: 'Git ref/sha to use as base for delta (defaults to PR base sha)'
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

outputs:
  markdown:
    description: 'Markdown report for this app'
    value: ${{ steps.mkdown.outputs.markdown }}
  head_json:
    description: 'JSON metrics for PR/head'
    value: ${{ steps.collect-head.outputs.json }}
  base_json:
    description: 'JSON metrics for base'
    value: ${{ steps.collect-base.outputs.json }}
```
