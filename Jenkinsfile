#!/usr/bin/env groovy

pipeline {

  options {
    ansiColor('xterm')
  }

  environment {
    PYTHON_MODULES = 'ingit test *.py'
  }

  agent none

  stages { stage("Matrix") { matrix {

    axes {
      axis {
        name 'PYTHON_VERSION'
        values '3.7', '3.8', '3.9', '3.10'
      }
    }

    agent { dockerfile {
      filename 'Dockerfile'
      additionalBuildArgs '--build-arg USER_ID=${USER_ID} --build-arg GROUP_ID=${GROUP_ID} --build-arg AUX_GROUP_IDS="${AUX_GROUP_IDS}" --build-arg TIMEZONE=${TIMEZONE} --build-arg PYTHON_VERSION=${PYTHON_VERSION}'
    } }

    stages {

      stage('Lint') {
        steps {
          sh """#!/usr/bin/env bash
            set -Eeux pipefail
            python -m pylint ${PYTHON_MODULES} | tee pylint.log
            echo "\${PIPESTATUS[0]}" | tee pylint_status.log
            python -m mypy ${PYTHON_MODULES} | tee mypy.log
            echo "\${PIPESTATUS[0]}" | tee mypy_status.log
            python -m pycodestyle ${PYTHON_MODULES} | tee pycodestyle.log
            echo "\${PIPESTATUS[0]}" | tee pycodestyle_status.log
            python -m pydocstyle ${PYTHON_MODULES} | tee pydocstyle.log
            echo "\${PIPESTATUS[0]}" | tee pydocstyle_status.log
          """
        }
      }

      stage('Coverage') {
        environment {
          CODECOV_TOKEN = credentials("codecov-token-mbdevpl-ingit")
        }
        steps {
          sh """#!/usr/bin/env bash
            set -Eeuxo pipefail
            TEST_PACKAGING=1 python -m coverage run --branch --source . -m unittest -v
            python -m coverage report --show-missing
            python -m codecov --token ${CODECOV_TOKEN}
          """
        }
      }

    }

  } } }

}
