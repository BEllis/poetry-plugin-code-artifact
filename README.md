# Poetry Plugin: (AWS) Code Artifact

[![PyPi](https://img.shields.io/pypi/v/poetry-plugin-code-artifact.svg)](https://pypi.org/project/poetry-plugin-code-artifact/)
[![Stable Version](https://img.shields.io/pypi/v/poetry-plugin-code-artifact?label=stable)](https://pypi.org/project/poetry-plugin-code-artifact/)
[![Pre-release Version](https://img.shields.io/github/v/release/bellis/poetry-plugin-code-artifact?label=pre-release&include_prereleases&sort=semver)](https://pypi.org/project/poetry-plugin-code-artifact)
[![Python Versions](https://img.shields.io/pypi/pyversions/poetry-plugin-code-artifact)](https://pypi.org/project/poetry-plugin-code-artifact)
[![Code coverage Status](https://codecov.io/gh/bellis/poetry-plugin-code-artifact/branch/main/graph/badge.svg)](https://codecov.io/gh/bellis/poetry-plugin-code-artifact)
[![PyTest](https://github.com/bellis/poetry-plugin-code-artifact/workflows/test/badge.svg)](https://github.com/bellis/poetry-plugin-code-artifact/actions?query=workflow%3Atest)
[![Download Stats](https://img.shields.io/pypi/dm/poetry-plugin-code-artifact)](https://pypistats.org/packages/poetry-plugin-code-artifact)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This package is a plugin that attempts to give improved integration of AWS CodeArtifact repositories with poetry.

## Installation

The easiest way to install the `code-artifact` plugin is via the `self add` command of Poetry.

```bash
poetry self add poetry-plugin-code-artifact
```

If you used `pipx` to install Poetry you can add the plugin via the `pipx inject` command.

```bash
pipx inject poetry poetry-plugin-code-artifact
```

Otherwise, if you used `pip` to install Poetry you can add the plugin packages via the `pip install` command.

```bash
pip install poetry-plugin-code-artifact
```

## Prerequisites

It is assumed there are one or more AWS CodeArtifact repositories set up and that you have a set of credentials that have permissions to available either, to search and download, and/or, publish packages.

### Identity policies

In order to grant access to a repository for **read** access, the following policy will need to be applied to the AWS identity for which credentials will be used to access the repository.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sts:GetServiceBearerToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "codeartifact:DescribeDomain",
                "codeartifact:GetAuthorizationToken",
                "codeartifact:ListRepositoriesInDomain"
            ],
            "Resource": "arn:aws:codeartifact:us-east-1:345125489763:domain/my-domain"
        },
        {
            "Effect": "Allow",
            "Action": [
                "codeartifact:Describe*",
                "codeartifact:List*",
                "codeartifact:GetPackageVersionReadme",
                "codeartifact:GetRepositoryEndpoint",
                "codeartifact:ReadFromRepository"
            ],
            "Resource": [
                "arn:aws:codeartifact:us-east-1:345125489763:repository/my-domain/my-repo",
                "arn:aws:codeartifact:us-east-1:345125489763:repository/my-domain/my-repo/*",
                "arn:aws:codeartifact:us-east-1:345125489763:package/my-domain/my-repo/*"
            ]
        }
    ]
}
```

In order to grant access to a repository for **write** access, the following policy will need to be applied to the AWS identity for which credentials will be used to access the repository.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "codeartifact:GetRepositoryEndpoint",
                "codeartifact:PublishPackageVersion",
                "codeartifact:PutPackageMetadata"
            ],
            "Resource": [
                "arn:aws:codeartifact:us-east-1:345125489763:repository/my-domain/my-repo",
                "arn:aws:codeartifact:us-east-1:345125489763:repository/my-domain/my-repo/*",
                "arn:aws:codeartifact:us-east-1:345125489763:package/my-domain/my-repo/*"
            ]
        }
    ]
}
```

### Cross-account policies

For cross-account access to the AWS CodeArtifact domain, the **domain** must have the resource policy,

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Principal": {
                "AWS": "arn:aws:iam::345125489763:root"
            },
            "Effect": "Allow",
            "Action": [
                "codeartifact:DescribeDomain",
                "codeartifact:GetAuthorizationToken",
                "codeartifact:ListRepositoriesInDomain"
            ],
            "Resource": "*"
        }
    ]
}
```

For cross-account **read** access to a repository, the **repository** will require the following resource policy,

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Principal": {
                "AWS": "arn:aws:iam::345125489763:root"
            },
            "Effect": "Allow",
            "Action": [
                "codeartifact:DescribePackageVersion",
                "codeartifact:DescribeRepository",
                "codeartifact:Get*",
                "codeartifact:List*",
                "codeartifact:ReadFromRepository"
            ],
            "Resource": "*"
        }
    ]
}
```

For cross-account **write** access, the **repository** will require the following resource policy,

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Principal": {
                "AWS": "arn:aws:iam::345125489763:root"
            },
            "Effect": "Allow",
            "Action": [
                "codeartifact:GetRepositoryEndpoint",
                "codeartifact:PublishPackageVersion",
                "codeartifact:PutPackageMetadata"
            ],
            "Resource": "*"
        }
    ]
}
```

## Usage

Other than configuration, usage is the same as adding any other repository to poetry.

The plugin is configured in the pyproject.toml file, below is an example of adding three AWS CodeArtifact repositories..

```toml
[[tool.poetry-plugin-code-artifact.sources]]
name="dev"  # The name of the repositroy in poetry
aws-codeartefact-domain="my-domain"   # The AWS CodeArtifact domain.
aws-codeartefact-owner="564131876131" # The AWS CodeArtifact domain owner.
aws-codeartefact-region="us-east-1"   # The AWS CodeArtifact region.
aws-codeartefact-repository="dev"     # The AWS CodeArtifact repository name.

[[tool.poetry-plugin-code-artifact.sources]]
name="qa"
aws-codeartefact-domain="my-domain"
aws-codeartefact-owner="564131876131"
aws-codeartefact-region="us-east-1"
aws-codeartefact-repository="dev"

[[tool.poetry-plugin-code-artifact.sources]]
name="prod"
aws-codeartefact-domain="my-domain"
aws-codeartefact-owner="564131876131"
aws-codeartefact-region="eus-east-1"
aws-codeartefact-repository="dev"
```

To use the above repositories via poetry, just use the normal commands,

*Note: You must first be logged into AWS with an identity that has the correct permissions as given in the prerequisites section above. For more information on configuring credentials, see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html*

```sh
# To add a dependency,
poetry add my-lib  # Searches all repositories
# or
poetry add my-lib --source dev  # Prioritizes dev repository then searches all repositories.

# To publish a dependency,
poetry publish -r dev
```

## Related Projects

* [website](https://github.com/python-poetry/website): The official Poetry website and blog
* [poetry-plugin-export](https://github.com/python-poetry/poetry-plugin-export): Export Poetry projects/lock files to
foreign formats like requirements.txt (Used some test code from this project)
* [poetry-plugin-package-info](https://github.com/bellis/poetry-plugin-package-info): Poetry Plugin for including project and git information in your distributable files. (Shameless plug to one of my other poetry plugins)
