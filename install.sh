#! /bin/bash

# To store the path of the executing script's directory in var `__DIR__`:
DIR="$(cd "$(dirname "${0}")"; echo "$(pwd)")"

ln -s ${DIR}/AnalysisCharts.py ${DIR}/../AnalysisCharts.py
ln -s ${DIR}/www/analysischarts ${DIR}/../../www/analysischarts
ln -s ${DIR}/www/analysischarts.html ${DIR}/../../www/analysischarts.html
